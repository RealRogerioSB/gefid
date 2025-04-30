from datetime import date

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection

st.cache_data.clear()

engine = st.connection(name="DB2", type=SQLConnection)

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)

st.subheader(":material/account_balance: Base de Investidores")


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
def load_report(_mci: int, _year: int, _month: int, _data: date) -> pd.DataFrame:
    base = engine.query(
        sql="""
            SELECT
                t5.CD_CLI_ACNT AS MCI,
                STRIP(CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 THEN t6.NOM
                    ELSE t8.NM_INVR
                END) AS INVESTIDOR,
                CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 THEN CAST(t6.COD_CPF_CGC AS BIGINT)
                    ELSE CAST(t8.NR_CPF_CNPJ_INVR AS BIGINT)
                END AS CPF_CNPJ,
                CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 AND t6.COD_TIPO = 1 THEN 'PF'
                    WHEN t5.CD_CLI_ACNT < 1000000000 AND t6.COD_TIPO = 2 THEN 'PJ'
                    WHEN  t5.CD_CLI_ACNT >= 999999999 AND t8.CD_TIP_PSS = 1 THEN 'PF'
                    ELSE 'PJ'
                END AS TIPO,
                t5.DATA,
                t5.CD_TIP_TIT AS COD_TITULO,
                CONCAT(t7.SG_TIP_TIT, t7.CD_CLS_TIP_TIT) AS SIGLA,
                CAST(t5.QUANTIDADE AS BIGINT) AS QUANTIDADE,
                CASE 
                    WHEN t5.CD_CLI_CSTD = 903485186 THEN 'ESCRITURAL'
                    ELSE 'CUSTÓDIA'
                END AS CUSTODIANTE
            FROM (
                SELECT
                    CD_CLI_EMT,
                    CD_TIP_TIT,
                    CD_CLI_ACNT,
                    CD_CLI_CSTD,
                    DATA,
                    QUANTIDADE
                FROM (
                    SELECT
                        t1.CD_CLI_EMT,
                        t1.CD_TIP_TIT,
                        t1.CD_CLI_ACNT,
                        t1.CD_CLI_CSTD,
                        t1.DT_MVTC AS DATA,
                        t1.QT_TIT_ATU AS QUANTIDADE
                    FROM
                        DB2AEB.MVTC_DIAR_PSC t1
                    WHERE
                        t1.CD_CLI_EMT = :mci
                    UNION ALL
                    SELECT
                        t1.CD_CLI_EMT,
                        t1.CD_TIP_TIT,
                        t1.CD_CLI_ACNT,
                        t1.CD_CLI_CSTD,
                        t1.DT_PSC - 1 DAY AS DATA,
                        t1.QT_TIT_INC_MM AS QUANTIDADE
                    FROM
                        DB2AEB.PSC_TIT_MVTD t1
                    WHERE
                        t1.CD_CLI_EMT = :mci
                ) t10
            ) t5
                LEFT JOIN DB2MCI.CLIENTE t6
                    ON t5.CD_CLI_ACNT = t6.COD
                LEFT JOIN DB2AEB.TIP_TIT t7
                    ON t5.CD_TIP_TIT = t7.CD_TIP_TIT
                LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                    ON t5.CD_CLI_ACNT = t8.CD_CLI_ACNT
            WHERE
                DATA BETWEEN :anterior AND :data
            ORDER BY
                CAST(t5.CD_CLI_ACNT AS INTEGER),
                DATA DESC
        """,
        show_spinner=False,
        ttl=60,
        params=dict(
            mci=_mci,
            anterior=date(_year, _month, 28).strftime("%Y-%m-%d"),
            data=_data.strftime("%Y-%m-%d")
        ),
    )
    base.columns = [str(columns).upper() for columns in base.columns]
    base["PK"] = f"{base['MCI']}-{base['COD_TITULO']}-{base['CUSTODIANTE']}"
    base = base.groupby("PK").first()
    base = base[~base["MCI"].isin([205007939, 211684707]) & base["QUANTIDADE"].ne(0)]
    base["COD_TITULO"] = base["COD_TITULO"].astype(str)
    base.reset_index(drop=True, inplace=True)

    dfixo = base[["MCI", "INVESTIDOR", "CPF_CNPJ", "TIPO"]].copy()
    dfixo.drop_duplicates(subset=["MCI"], inplace=True)

    lista_tit = []

    for x in (base["COD_TITULO"] + base["SIGLA"]).unique():
        dfx = base[(base["COD_TITULO"] + base["SIGLA"]).eq(x)].copy()
        dfx.reset_index(drop=True, inplace=True)

        tipo = dfx["SIGLA"][0] + dfx["COD_TITULO"].astype(str)[0]

        dfbb = dfx[dfx["CUSTODIANTE"].eq("ESCRITURAL")].copy()[["MCI", "QUANTIDADE"]]
        dfbb.rename(columns={"QUANTIDADE": "BB_" + tipo}, inplace=True)

        dfb3 = dfx[dfx["CUSTODIANTE"].eq("CUSTÓDIA")].copy()[["MCI", "QUANTIDADE"]]
        dfb3.rename(columns={"QUANTIDADE": "B3_" + tipo}, inplace=True)

        dfx = pd.merge(dfbb, dfb3, how="outer", on=["MCI"])

        dfixo = pd.merge(dfixo, dfx, how="left", on=["MCI"])

        lista_tit.append(tipo)

    dfixo.fillna(0, inplace=True)

    cols = ["MCI", "INVESTIDOR", "CPF_CNPJ"]

    for x in lista_tit:
        dfixo["TOTAL_" + x] = dfixo["BB_" + x] + dfixo["B3_" + x]
        cols.extend(["BB_" + x, "B3_" + x, "TOTAL_" + x])

    dfixo = dfixo[cols]

    return dfixo


@st.cache_data(show_spinner=":material/hourglass: Obtendo os dados, aguarde...")
def load_data(_mci: int) -> tuple[int, str, int, str]:
    cadastro = engine.query(
        sql="""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                t1.SG_EMP AS SIGLA,
                STRIP(t2.NOM) AS EMPRESA,
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
    cadastro.columns = [str(columns).upper() for columns in cadastro.columns]

    mci_empresa = cadastro["MCI"][0]
    nome = cadastro["EMPRESA"][0]
    cnpj = cadastro["CNPJ"][0]
    sigla = cadastro["SIGLA"][0]

    return mci_empresa, nome, cnpj, sigla


option_active = st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"])

kv = load_active("NULL" if option_active == "ativos" else "NOT NULL")

with st.columns(2)[0]:
    empresa = st.selectbox(
        label="**Clientes ativos:**" if option_active == "ativos" else "**Clientes inativos:**",
        options=sorted(kv.values()),
    )

    with st.columns(3)[0]:
        hoje = st.date_input(label="**Data:**", value=date.today(), format="DD/MM/YYYY")

mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

year = hoje.year - 1 if hoje.month == 1 else hoje.year
month = 12 if hoje.month == 1 else hoje.month - 1

with st.columns(2)[0]:
    st.divider()

    params = dict(type="primary", use_container_width=True)

    col = st.columns(3)

    btn_view = col[0].button(label="**Visualizar na tela**", icon=":material/preview:", **params)
    btn_csv = col[1].button(label="**Arquivo CSV**", icon=":material/csv:", **params)
    btn_excel = col[2].button(label="**Arquivo Excel**", icon=":material/format_list_numbered_rtl:", **params)

    if btn_view:
        get_report = load_report(mci, year, month, hoje)
        if not get_report.empty:
            get_title = load_data(mci)
            st.write(f"**MCI:** {get_title[0]}")
            st.write(f"**Empresa:** {get_title[1]}")
            st.write(f"**CNPJ:** {int(get_title[2])}")
            st.write(f"**Data:** {hoje:%d/%m/%Y}")

            st.dataframe(get_report, hide_index=True)

            st.button(label="**Voltar**", key="btn_back", type="primary")
        else:
            st.toast(body="**Sem dados para exibir**", icon=":material/warning:")

    if btn_csv:
        get_report = load_report(mci, year, month, hoje)
        if not get_report.empty:
            get_title = load_data(mci)
            get_report.to_csv(f"static/escriturais/@deletar/{get_title[3]}-{hoje}.csv", index=False)

            st.toast(body="**Arquivo CSV enviado para a pasta específica**", icon=":material/check_circle:")
        else:
            st.toast(body="**Sem dados para exibir**", icon=":material/warning:")

    if btn_excel:
        pass
