from datetime import date, timedelta

import polars as pl
import streamlit as st
from sqlalchemy import create_engine

st.cache_data.clear()

engine = create_engine(st.secrets["connections"]["DB2"]["url"])

st.subheader(":material/siren: Resolução CVM 160")


@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
def report(_mci, _ano, _mes, _data) -> None:
    base = pl.read_database(
        query=f"""
            SELECT
                1 as TIPO,
                t5.CD_CLI_ACNT AS MCI,
                CASE
                    WHEN t6.COD_PAIS_ORIG <= 1 AND t5.CD_CLI_ACNT < 1000000000 AND t6.COD_TIPO = 1 THEN 'F'
                    WHEN t6.COD_PAIS_ORIG <= 1 AND t5.CD_CLI_ACNT < 1000000000 AND t6.COD_TIPO = 2 THEN 'J'
                    WHEN t6.COD_PAIS_ORIG <= 1 AND t5.CD_CLI_ACNT > 999999999 AND t8.CD_TIP_PSS = 1 THEN 'F'
                    WHEN t6.COD_PAIS_ORIG > 1 THEN 'E'
                    ELSE 'J'
                END AS PSS,
                CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 THEN CAST(t6.COD_CPF_CGC AS BIGINT)
                    ELSE CAST(t8.NR_CPF_CNPJ_INVR AS BIGINT)
                END AS CPF_CNPJ,
                t5.DATA,
                t5.CD_TIP_TIT as COD_TITULO,
                CAST(t5.QUANTIDADE AS BIGINT) AS QUANTIDADE
            FROM (
                SELECT
                    CD_TIP_TIT,
                    CD_CLI_ACNT,
                    DATA,
                    QUANTIDADE
                FROM (
                    SELECT
                        t1.CD_TIP_TIT,
                        t1.CD_CLI_ACNT,
                        t1.DT_MVTC AS DATA,
                        t1.QT_TIT_ATU AS QUANTIDADE
                    FROM
                        DB2AEB.MVTC_DIAR_PSC t1
                    WHERE
                        t1.CD_CLI_EMT = {_mci} AND
                        t1.CD_CLI_CSTD = 903485186
                    UNION ALL
                    SELECT
                        t1.CD_TIP_TIT,
                        t1.CD_CLI_ACNT,
                        t1.DT_PSC - 1 DAY AS DATA,
                        t1.QT_TIT_INC_MM AS QUANTIDADE
                    FROM
                        DB2AEB.PSC_TIT_MVTD t1
                    WHERE
                        t1.CD_CLI_EMT = {_mci} AND
                        t1.CD_CLI_CSTD = 903485186
                ) 
            ) t5
            LEFT JOIN DB2MCI.CLIENTE t6
                ON t5.CD_CLI_ACNT = t6.COD
            LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                ON t5.CD_CLI_ACNT = t8.CD_CLI_ACNT
            WHERE
                DATA BETWEEN {date(_ano, _mes, 28).strftime('%Y-%m-%d')!r} AND {_data.strftime('%Y-%m-%d')!r}
            ORDER BY
                CPF_CNPJ,
                DATA DESC
        """,
        connection=engine,
        infer_schema_length=None
    )
    if base.is_empty():
        st.toast(body="**Sem dados para exibir**", icon="⚠️")
    else:
        base = base.with_columns(pl.lit("            ").alias("RESERVA"))
        base = base.with_columns((base["CPF_CNPJ"].cast(pl.Utf8) + "-" + base["COD_TITULO"].cast(pl.Utf8)).alias("PK"))
        base = base.group_by(["PK"]).agg(pl.col("*").first())
        base = base.filter(~pl.col("CPF_CNPJ").is_in([60777661000150]) & (pl.col("CPF_CNPJ") > 0) &
                           (pl.col("QUANTIDADE") != 0))
        base = base.drop(["MCI", "DATA"])
        base = base.with_row_index("index", offset=0)

        for z in base["COD_TITULO"].unique():
            globals()["base" + str(z)] = base.filter(pl.col("COD_TITULO") == z)

            y = base.select([
                pl.concat_str([
                    pl.col("TIPO"),
                    pl.col("PSS"),
                    pl.col("CPF_CNPJ").cast(pl.Utf8).str.zfill(19),
                    pl.col("QUANTIDADE").cast(pl.Utf8).str.zfill(17),
                    pl.col("RESERVA")
                ]).alias("y")
            ])

            filename = f"static/escriturais/@deletar/resolucao160-{_mci}-tipo{z}.txt"

            y.write_csv(filename, separator=".", include_header=False)

            trailer = f"9 {str((len(y) + 1)).zfill(19)}{str(base['QUANTIDADE'].sum()).zfill(17)}            "

            with open(filename, "a") as f:
                f.write(trailer)

        st.toast(body="**Criação de TXT feita com sucesso**", icon="ℹ️")


option_active = st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"])

kv = load_active("NULL") if option_active == "ativos" else load_active("NOT NULL")

empresa = st.selectbox(
    label="**Clientes ativos:**" if option_active == "ativos" else "**Clientes inativos:**",
    options=sorted(kv.values()),
)

mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

col = st.columns(3)
data = col[0].date_input(label="**Data:**", value=date.today().replace(day=1) - timedelta(days=1), format="DD/MM/YYYY")

ano = data.year - 1 if data.month == 1 else data.year
mes = 12 if data.month == 1 else data.month - 1

if st.button(label="**Enviar TXT**", key="btn_send_csv", icon=":material/edit_note:", type="primary"):
    with st.spinner(text="Obtendo os dados, aguarde...", show_time=True):
        report(mci, ano, mes, data)

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)
