from datetime import date

import polars as pl
import streamlit as st
from sqlalchemy import create_engine

engine = create_engine(st.secrets["connections"]["DB2"]["url"])

st.cache_data.clear()

st.subheader(":material/send_money: Rendimentos Distribuídos")


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_active(active: str) -> dict[int, str]:
    df = pl.read_database(
        query=f"""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                t2.NOM
            FROM
                DB2AEB.PRM_EMP AS t1
                INNER JOIN DB2MCI.CLIENTE AS t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.DT_ECR_CTR IS {active}
        """,
        connection=engine,
        infer_schema_length=None
    )
    return {k: v for k, v in zip(df["MCI"].to_list(), df["NOM"].to_list())}


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_report(_mci: int, _ano: int, _mes: int) -> pl.DataFrame:
    return pl.read_database(
        query=f"""
            SELECT
                t1.CD_CLI_TITR as MCI,
                STRIP(t2.NOM) AS INVESTIDOR,
                CAST(t2.COD_CPF_CGC AS BIGINT) AS CPF_CNPJ,
                CASE WHEN t2.COD_TIPO = 1 THEN 'PF' ELSE 'PJ' END AS TIPO_PESSOA,
                t1.DT_MVT_DRT AS DATA,
                t4.NM_TIP_DRT AS DIREITO,
                STRIP(t3.SG_TIP_TIT) || STRIP(t3.CD_CLS_TIP_TIT) AS SIGLA,
                t1.VL_MVT_REN AS VALOR,
                t1.VL_IR_CLCD_MVT_REN AS VALOR_IR,
                t1.VL_MVT_REN - t1.VL_IR_CLCD_MVT_REN AS VALOR_LIQUIDO
            FROM
                DB2AEB.MVT_REN t1
                FULL JOIN DB2MCI.CLIENTE t2
                    ON t2.COD = t1.CD_CLI_TITR
                INNER JOIN DB2AEB.TIP_TIT t3
                    ON t3.CD_TIP_TIT = t1.CD_TIP_TIT
                INNER JOIN DB2AEB.TIP_DRT t4
                    ON t4.CD_TIP_DRT = t1.CD_TIP_DRT
            WHERE
                t1.CD_CLI_DLBC = {_mci} AND
                t1.CD_EST_DRT IN (1) AND
                YEAR(t1.DT_MVT_DRT) = {_ano} AND
                MONTH(t1.DT_MVT_DRT) = {_mes}
            ORDER BY
                STRIP(t2.NOM),
                t1.DT_MVT_DRT
        """,
        connection=engine,
        infer_schema_length=None
    )


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_data(_mci: int) -> pl.DataFrame:
    return pl.read_database(
        query=f"""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                t1.SG_EMP AS SIGLA,
                t2.NOM AS EMPRESA,
                t2.COD_CPF_CGC AS CNPJ
            FROM
                DB2AEB.PRM_EMP t1
                INNER JOIN DB2MCI.CLIENTE t2
                    ON t1.CD_CLI_EMT = t2.COD
            WHERE
                t1.CD_CLI_EMT = {_mci}
        """,
        connection=engine,
        infer_schema_length=None
    )


option_active = st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"])

kv = load_active("NULL") if option_active == "ativos" else load_active("NOT NULL")

empresa = st.selectbox(label="**Clientes ativos:**" if option_active == "ativos" else "**Clientes inativos:**",
                       options=sorted(kv.values()))

mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

col = st.columns([1.5, 0.5, 1, 1])
mes = col[0].slider(label="**Mês:**", min_value=1, max_value=12, value=date.today().month)
ano = col[1].selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1))

params = dict(type="primary", use_container_width=True)

st.divider()

col = st.columns(3)

if col[0].button(label="**Visualizar na tela**", key="btn_view", icon=":material/preview:", **params):
    get_view = load_report(mci, ano, mes)
    if not get_view.is_empty():
        get_data = load_data(mci)
        st.write(f"**MCI:** {get_data['MCI'][0]}")
        st.write(f"**EMPRESA:** {get_data['EMPRESA'][0]}")
        st.write(f"**CNPJ:** {get_data['CNPJ'][0]}")
        st.write(f"**MÊS/ANO:** {mes:02d}/{ano}")
        st.write(f"**TOTAL BRUTO:** R$ {float(get_view['VALOR'].sum()):_.2f}"
                 .replace(".", ",").replace("_", "."))
        st.write(f"**TOTAL IR:** R$ {float(get_view['VALOR_IR'].sum()):_.2f}"
                 .replace(".", ",").replace("_", "."))
        st.write(f"**TOTAL LÍQUIDO:** R$ {float(get_view['VALOR_LIQUIDO'].sum()):_.2f}"
                 .replace(".", ",").replace("_", "."))
        st.dataframe(get_view)
    else:
        st.toast(body="**Sem dados para exibir.**", icon="⚠️")

if col[1].button(label="**Arquivo CSV**", key="btn_csv", icon=":material/csv:", **params):
    get_csv = load_report(mci, ano, mes)
    if not get_csv.is_empty():
        sigla = load_data(mci)["SIGLA"][0]
        get_csv.write_csv(file=f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Distribuídos.csv")
    else:
        st.toast(body="**Sem dados para exibir.**", icon="⚠️")

if col[2].button(label="**Arquivo Excel**", key="btn_excel", icon=":material/format_list_numbered_rtl:", **params):
    get_xlsx = load_report(mci, ano, mes)
    if not get_xlsx.is_empty():
        sigla = load_data(mci)["SIGLA"][0]
        if len(get_xlsx) <= int(1e6):
            caminho_saida = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Distribuídos.xlsx"
            get_xlsx.write_excel(workbook=caminho_saida)

            st.toast(body="**Arquivo XLSX enviado para a pasta específica**", icon="✔️")
        else:
            caminho_saida_1 = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Distribuidos-parte1.xlsx"
            get_xlsx[:int(1e6)].write_excel(workbook=caminho_saida_1)

            caminho_saida_2 = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Distribuidos-parte2.xlsx"
            get_xlsx[int(1e6):int(2e6)].write_excel(workbook=caminho_saida_2)

            caminho_saida_3 = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Distribuidos-parte3.xlsx"
            get_xlsx[int(2e6):].write_excel(workbook=caminho_saida_3)

            st.toast(body="**Mais partes de arquivos XLSX enviados para a pasta específica**", icon="✔️")
    else:
        st.toast(body="**Sem dados para exibir**", icon="⚠️")

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)
