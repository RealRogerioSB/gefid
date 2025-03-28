import os
from datetime import date

import polars as pl
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

conn = create_engine(os.getenv("DB2"))

st.cache_data.clear()

st.subheader(":material/send_money: Rendimentos Distribuídos")


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
                t1.DT_ECR_CTR IS {0}
        """.format(active),
        connection=conn,
        infer_schema_length=None
    )
    return {k: v for k, v in zip(df["MCI"].to_list(), df["NOM"].to_list())}


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_report(_mci: int, _ano: int, _mes: int) -> pl.DataFrame:
    df = pl.read_database(
        query="""
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
                t1.CD_CLI_DLBC = {} AND
                t1.CD_EST_DRT IN (1) AND
                YEAR(t1.DT_MVT_DRT) = {} AND
                MONTH(t1.DT_MVT_DRT) = {}
            ORDER BY
                STRIP(t2.NOM),
                t1.DT_MVT_DRT
        """.format(_mci, _ano, _mes),
        connection=conn,
        infer_schema_length=None
    )
    return df


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_data(_mci):
    df = pl.read_database(
        query="""
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
                t1.CD_CLI_EMT = {}
        """.format(_mci),
        connection=conn,
        infer_schema_length=None
    )
    return df


option_active = st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"])

kv = load_active("NULL") if option_active == "ativos" else load_active("NOT NULL")

empresa = st.selectbox(label="**Clientes ativos:**" if option_active == "ativos" else "**Clientes inativos:**",
                       options=sorted(kv.values()))

mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

col = st.columns([1.5, 0.5, 1, 1])
mes = col[0].slider(label="**Mês:**", min_value=1, max_value=12, value=date.today().month - 1)
ano = col[1].selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1))

params = dict(type="primary", use_container_width=True)

with st.container(border=True):
    col = st.columns(3)

    if col[0].button(label="**Visualizar na tela**", key="btn_view", icon=":material/preview:", **params):
        get_report = load_report(mci, ano, mes)
        if not get_report.is_empty():
            get_data = load_data(mci)
            st.write(f"**MCI:** {get_data['MCI'][0]}")
            st.write(f"**EMPRESA:** {get_data['EMPRESA'][0]}")
            st.write(f"**CNPJ:** {get_data['CNPJ'][0]}")
            st.write(f"**MÊS/ANO:** {mes:02d}/{ano}")
            st.write(f"**TOTAL BRUTO:** R$ {float(get_report['VALOR'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.write(f"**TOTAL IR:** R$ {float(get_report['VALOR_IR'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.write(f"**TOTAL LÍQUIDO:** R$ {float(get_report['VALOR_LIQUIDO'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.dataframe(get_report)
        else:
            st.toast(body="**Sem dados para exibir.**", icon=":material/warning:")

    if col[1].button(label="**Arquivo CSV**", key="btn_csv", icon=":material/unarchive:", **params):
        pass

    if col[2].button(label="**Arquivo Excel**", key="btn_excel", icon=":material/unarchive:", **params):
        pass
