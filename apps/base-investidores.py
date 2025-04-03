import os
from datetime import date, timedelta

import polars as pl
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

st.cache_data.clear()

conn = create_engine(os.getenv("DB2"))

st.subheader(":material/account_balance: Base de Investidores")


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_active(active: str) -> dict[int, str]:
    df = pl.read_database(
        query="""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                t2.NOM
            FROM
                DB2AEB.PRM_EMP AS t1
                INNER JOIN DB2MCI.CLIENTE AS t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.DT_ECR_CTR IS {}
        """.format(active),
        connection=conn,
        infer_schema_length=None
    )
    return {k: v for k, v in zip(df["MCI"].to_list(), df["NOM"].to_list())}


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def report(_mci, _nome):
    base = pl.read_database(
        query=f"""
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
                STRIP(CONCAT(t7.SG_TIP_TIT, t7.CD_CLS_TIP_TIT)) AS SIGLA,
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
                        t1.CD_CLI_EMT = {_mci}
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
                        t1.CD_CLI_EMT = {_mci}
                ) t10
            ) t5
                LEFT JOIN DB2MCI.CLIENTE t6
                    ON t5.CD_CLI_ACNT = t6.COD
                LEFT JOIN DB2AEB.TIP_TIT t7
                    ON t5.CD_TIP_TIT = t7.CD_TIP_TIT
                LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                    ON t5.CD_CLI_ACNT = t8.CD_CLI_ACNT
            WHERE
                DATA BETWEEN {date(year, month, 28).strftime("%Y-%m-%d")!r} AND {hoje.strftime("%Y-%m-%d")!r}
            ORDER BY
                CAST(t5.CD_CLI_ACNT AS INTEGER),
                DATA DESC
        """,
        connection=conn,
        infer_schema_length=None
    )
    base = base.with_columns((base["MCI"].cast(pl.Utf8) + "-" + base["COD_TITULO"].cast(pl.Utf8) + "-" +
                              base["CUSTODIANTE"].cast(pl.Utf8)).alias("PK"))
    base = base.group_by(["PK"]).agg(pl.col("*").first())
    base = base.filter(~pl.col("MCI").is_in([205007939, 211684707]) & (pl.col("QUANTIDADE") != 0))
    # base = base.with_row_count(name="index")
    base = base.with_columns(base["COD_TITULO"].cast(pl.Utf8))

    cadastro = pl.read_database(
        query=f"""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                STRIP(t1.SG_EMP) AS SIGLA,
                STRIP(t2.NOM) AS EMPRESA,
                t2.COD_CPF_CGC AS CNPJ
            FROM
                DB2AEB.PRM_EMP t1
                INNER JOIN DB2MCI.CLIENTE t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.CD_CLI_EMT = {_mci}
        """,
        connection=conn,
        infer_schema_length=None
    )

    mci = cadastro["MCI"][0]
    nome = cadastro["EMPRESA"][0]
    cnpj = cadastro["CNPJ"][0]
    sigla = cadastro["SIGLA"][0]

    fixo = base.select(["MCI"]).unique()
    # fixo = fixo.unique(["MCI"])

    list_title = []

    for x in (base["COD_TITULO"] + base["SIGLA"]).unique():
        dfx = base.filter((base["COD_TITULO"] + base["SIGLA"]) == x)

        tipo = dfx["SIGLA"][0] + str(dfx["COD_TITULO"][0])

        dfbb = dfx.filter(dfx["CUSTODIANTE"] == "ESCRITURAL")
        dfbb = dfbb.rename({"QUANTIDADE": "BB_" + tipo})
        dfbb = dfbb.drop(["INVESTIDOR", "CPF_CNPJ", "TIPO", "DATA", "COD_TITULO", "SIGLA", "CUSTODIANTE"])

        dfb3 = dfx.filter(dfx["CUSTODIANTE"] == "CUSTÓDIA")
        dfb3 = dfb3.rename({"QUANTIDADE": "B3_" + tipo})
        dfb3 = dfb3.drop(["INVESTIDOR", "CPF_CNPJ", "TIPO", "DATA", "COD_TITULO", "SIGLA", "CUSTODIANTE"])

        dfx = dfbb.join(dfb3, on=["MCI"], how="full", coalesce=True)

        fixo = fixo.join(dfx, on=["MCI"], how="left", coalesce=True)

        list_title.append(tipo)

    fixo = fixo.fill_null(0)

    cols = ["MCI", "INVESTIDOR", "CPF_CNPJ"]

    for x in list_title:
        fixo = fixo.with_columns((fixo["BB_" + x] + fixo["B3_" + x]).alias("TOTAL_" + x))
        cols.extend(["BB_" + x, "B3_" + x, "TOTAL_" + x])

    fixo = fixo.select(cols)

    return fixo


option_active = st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"])

kv = load_active("NULL") if option_active == "ativos" else load_active("NOT NULL")

empresa = st.selectbox(
    label="**Clientes ativos:**" if option_active == "ativos" else "**Clientes inativos:**",
    options=sorted(kv.values()),
)

mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

col = st.columns(3)
hoje = col[0].date_input(label="**Data:**", value=date.today().replace(day=1) - timedelta(days=1), format="DD/MM/YYYY")

year = hoje.year - 1 if hoje.month == 1 else hoje.year
month = 12 if hoje.month == 1 else hoje.month - 1

params = dict(type="primary", use_container_width=True)

with st.container(border=True):
    col = st.columns(3)

    if col[0].button(label="Visualizar na tela", key="btn_view", icon=":material/preview:", **params):
        get_report = report(mci, empresa)
        if not get_report.is_empty():
            st.dataframe(get_report)
        else:
            st.toast(body="Sem dados para exibir.", icon="⚠️")

    if col[1].button(label="Arquivo CSV", key="btn_csv", icon=":material/unarchive:", **params):
        pass

    if col[2].button(label="Arquivo Excel", key="btn_excel", icon=":material/unarchive:", **params):
        pass

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)
