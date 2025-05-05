from datetime import date

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection

st.cache_data.clear()

engine = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/paid: Rendimentos Pagos")


@st.cache_data(show_spinner=":material/hourglass: Obtendo os dados, aguarde...")
def load_active(active: str) -> dict[int, str]:
    df = engine.query(
        sql=f"""
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
        show_spinner=False,
        ttl=60,
    )
    return {k: v for k, v in zip(df["mci"].to_list(), df["nom"].to_list())}


@st.cache_data(show_spinner=":material/hourglass: Obtendo os dados, aguarde...")
def load_report(_mci: int, _ano: int, _mes: int) -> pd.DataFrame:
    return engine.query(
        sql="""
            SELECT
                t1.CD_CLI_TITR AS MCI,
                STRIP(t2.NOM) AS INVESTIDOR,
                CAST(t2.COD_CPF_CGC AS BIGINT) AS CPF_CNPJ,
                CASE WHEN t2.COD_TIPO = 1 THEN 'PF' ELSE 'PJ' END AS TIPO_PESSOA,
                t1.DT_MVT_DRT AS DATA,
                t4.NM_TIP_DRT AS DIREITO,
                CONCAT(t3.SG_TIP_TIT, t3.CD_CLS_TIP_TIT) AS SIGLA,
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
                t1.CD_CLI_DLBC = :mci AND
                t1.CD_EST_DRT IN (8, 9) AND
                YEAR(t1.DT_MVT_DRT) = :ano AND
                MONTH(t1.DT_MVT_DRT) = :mes
            ORDER BY
                STRIP(t2.NOM),
                t1.DT_MVT_DRT
        """,
        show_spinner=False,
        ttl=60,
        params=dict(mci=_mci, ano=_ano, mes=_mes),
    )


@st.cache_data(show_spinner=":material/hourglass: Obtendo os dados, aguarde...")
def load_data(_mci: int) -> pd.DataFrame:
    return engine.query(
        sql="""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                t1.SG_EMP AS SIGLA,
                t2.NOM AS EMPRESA,
                t2.COD_CPF_CGC AS CNPJ
            FROM
                DB2AEB.PRM_EMP t1
                INNER JOIN DB2MCI.CLIENTE t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.CD_CLI_EMT = :mci
        """,
        show_spinner=False,
        ttl=60,
        params=dict(mci=_mci),
    )


option_active = st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"])

kv = load_active("NULL") if option_active == "ativos" else load_active("NOT NULL")

with st.columns(2)[0]:
    empresa = st.selectbox(label="**Clientes ativos:**" if option_active == "ativos" else "**Clientes inativos:**",
                           options=sorted(kv.values()))

    mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

    col = st.columns([2, 1, 1])
    mes = col[0].slider(label="**Mês:**", min_value=1, max_value=12, value=date.today().month)
    ano = col[1].selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1))

    params = dict(type="primary", use_container_width=True)

    st.divider()

    col = st.columns(3)

    btn_view = col[0].button(label="**Visualizar na tela**", icon=":material/preview:", **params)
    btn_csv = col[1].button(label="**Arquivo CSV**", icon=":material/csv:", **params)
    btn_excel = col[2].button(label="**Arquivo Excel**", icon=":material/format_list_numbered_rtl:", **params)

if btn_view:
    get_view = load_report(mci, ano, mes)
    if not get_view.empty:
        get_data = load_data(mci)
        st.write(f"**MCI:** {get_data['mci'][0]}")
        st.write(f"**EMPRESA:** {get_data['empresa'][0]}")
        st.write(f"**CNPJ:** {get_data['cnpj'][0]}")
        st.write(f"**MÊS/ANO:** {mes:02d}/{ano}")
        st.write(f"**TOTAL BRUTO:** R$ {float(get_view['valor'].sum()):_.2f}"
                 .replace(".", ",").replace("_", "."))
        st.write(f"**TOTAL IR:** R$ {float(get_view['valor_ir'].sum()):_.2f}"
                 .replace(".", ",").replace("_", "."))
        st.write(f"**TOTAL LÍQUIDO:** R$ {float(get_view['valor_liquido'].sum()):_.2f}"
                 .replace(".", ",").replace("_", "."))
        st.dataframe(get_view)
    else:
        st.toast(body="**Sem dados para exibir**", icon=":material/warning:")

if btn_csv:
    get_csv = load_report(mci, ano, mes)
    if not get_csv.empty:
        sigla = load_data(mci)["SIGLA"][0]
        get_csv.write_csv(file=f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Pagos.csv")
    else:
        st.toast(body="**Sem dados para exibir**", icon=":material/warning:")

if btn_excel:
    get_xlsx = load_report(mci, ano, mes)
    if not get_xlsx.empty:
        sigla = load_data(mci)["SIGLA"][0]
        if len(get_xlsx) <= int(1e6):
            caminho_saida = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Pagos.xlsx"
            get_xlsx.to_excel(excel_writer=caminho_saida, index=False, engine="xlsxwriter")

            st.toast(body="**Arquivo XLSX enviado para a pasta específica**", icon=":material/check_circle:")
        else:
            caminho_saida_1 = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Pagos-parte1.xlsx"
            get_xlsx[:int(1e6)].to_excel(excel_writer=caminho_saida_1, index=False, engine="xlsxwriter")

            caminho_saida_2 = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Pagos-parte2.xlsx"
            get_xlsx[int(1e6):int(2e6)].to_excel(excel_writer=caminho_saida_2, index=False, engine="xlsxwriter")

            caminho_saida_3 = f"static/escriturais/@deletar/{sigla}-{mes}-{ano}-Rendimentos Pagos-parte3.xlsx"
            get_xlsx[int(2e6):].to_excel(excel_writer=caminho_saida_3, index=False, engine="xlsxwriter")

            st.toast(body="**Mais partes de arquivos XLSX enviados para a pasta específica**",
                     icon=":material/check_circle:")
    else:
        st.toast(body="**Sem dados para exibir**", icon=":material/warning:")
