from datetime import date, timedelta

import streamlit as st
from streamlit.connections import SQLConnection

st.cache_data.clear()

engine = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/siren: Resolução CVM 160")


@st.cache_data(show_spinner=False)
def load_active(active: str) -> dict[int, str]:
    df = engine.query(
        sql=f"""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                STRIP(t2.NOM) AS NOM
            FROM
                DB2AEB.PRM_EMP AS t1
                INNER JOIN DB2MCI.CLIENTE AS t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.DT_ECR_CTR IS {active.upper()}
            ORDER BY
                STRIP(t2.NOM)
        """,
        show_spinner=False,
        ttl=0,
    )
    return {k: v for k, v in zip(df["mci"].to_list(), df["nom"].to_list())}


@st.cache_data(show_spinner=False)
def report(_mci: int, _data_ant: date, _data: date) -> None:
    base = engine.query(
        sql="""
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
                t5.CD_TIP_TIT AS COD_TITULO,
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
                        t1.CD_CLI_EMT = :mci AND
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
                        t1.CD_CLI_EMT = :mci AND
                        t1.CD_CLI_CSTD = 903485186
                ) 
            ) t5
            LEFT JOIN DB2MCI.CLIENTE t6
                ON t5.CD_CLI_ACNT = t6.COD
            LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                ON t5.CD_CLI_ACNT = t8.CD_CLI_ACNT
            WHERE
                DATA BETWEEN :anterior AND :data
            ORDER BY
                CPF_CNPJ,
                DATA DESC
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, anterior=_data_ant, data=_data),
    )

    if base.empty:
        st.toast(body="**Não há dados para exibir...**", icon=":material/error:")

    else:
        base["reserva"] = "            "
        base["pk"] = f"{base['cpf_cnpj']}-{base['cod_titulo']}"
        base = base.groupby(["pk"]).first()
        base = base[~base["cpf_cnpj"].isin([60777661000150]) & base["cpf_cnpj"].gt(0) & base["quantidade"].ne(0)]
        base = base.drop(["mci", "DATA"], axis=1)
        base = base.reset_index(drop=True)

        for z in base["cod_titulo"].unique():
            globals()["base" + str(z)] = base[base["cod_titulo"].eq(z)]

            y = globals()["base" + str(z)].apply(lambda x: "%s%s%s%s%s" % (
                x["tipo"], x["pss"], str(x["cpf_cnpj"]).zfill(19), str(x["quantidade"]).zfill(17), x["reserva"]),
                                                   axis=1)

            y.to_csv(f"static/escriturais/@deletar/resolucao160-{st.session_state['empresa']}-tipo{z}.txt",
                     sep='.', header=False, index=False)

            trailer = f"9 {str(len(y.index) + 1).zfill(19)}{str(base['quantidade'].sum()).zfill(17)}            "

            with open(f"static/escriturais/@deletar/resolucao160-{st.session_state['empresa']}-tipo{z}.txt", "a") as f:
                f.write(trailer)

        st.toast(body="**Criação de TXT feita com sucesso**", icon=":material/check_circle:")


with st.columns(2)[0]:
    st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"], key="option_active")

    kv = load_active("null") if st.session_state["option_active"] == "ativos" else load_active("not null")

    st.selectbox(
        label="**Clientes ativos:**" if st.session_state["option_active"] == "ativos" else "**Clientes inativos:**",
        options=sorted(kv.values()),
        key="empresa"
    )

    mci = next((chave for chave, valor in kv.items() if valor == st.session_state["empresa"]), 0)

    st.columns(3)[0].date_input(label="**Data:**", key="data", value=date.today().replace(day=1) - timedelta(days=1),
                                format="DD/MM/YYYY")

    data_ant: date = (st.session_state["data"].replace(day=1) - timedelta(days=1)).replace(day=28)

    if st.button(label="**Enviar TXT**", key="btn_send_csv", icon=":material/edit_note:", type="primary"):
        with st.spinner(text="**:material/hourglass: Obtendo os dados, aguarde...**", show_time=True):
            report(mci, data_ant, st.session_state["data"])
