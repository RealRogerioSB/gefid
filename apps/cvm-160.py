from datetime import date, timedelta

import streamlit as st
from streamlit.connections import SQLConnection

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)


@st.cache_data(show_spinner="**Preparando a listagem da empresa, aguarde...**")
def load_active(active: str) -> dict[str, int]:
    df = engine.query(
        sql=f"""
            SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
            FROM DB2AEB.PRM_EMP AS t1 INNER JOIN DB2MCI.CLIENTE AS t2 ON t2.COD = t1.CD_CLI_EMT
            WHERE t1.DT_ECR_CTR IS {active.upper()}
            ORDER BY STRIP(t2.NOM)
        """,
        show_spinner=False,
        ttl=0,
    )
    return {k: v for k, v in zip(df["nom"].to_list(), df["mci"].to_list())}


with st.columns(2)[0]:
    st.subheader(":material/siren: Resolução CVM 160")

    st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"], key="option")

    kv: dict[str, int] = load_active("null") if st.session_state["option"] == "ativos" else load_active("not null")

    st.selectbox(
        label="**Clientes ativos:**" if st.session_state["option"] == "ativos" else "**Clientes inativos:**",
        options=kv.keys(),
        key="empresa"
    )

    mci: int = kv.get(st.session_state["empresa"])

    st.columns(3)[0].date_input(label="**Data:**", key="data", value=date.today().replace(day=1) - timedelta(days=1),
                                format="DD/MM/YYYY")

    data_ant: date = (st.session_state["data"].replace(day=1) - timedelta(days=1)).replace(day=28)

st.button(label="**Enviar TXT**", key="enviar", type="primary", icon=":material/upload:")

if st.session_state["enviar"]:
    with st.spinner(text="**:material/hourglass: Preparando os dados para enviar, aguarde...**", show_time=True):
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
                    DATA BETWEEN :data_ant AND :data
                ORDER BY
                    CPF_CNPJ,
                    DATA DESC
            """,
            show_spinner=False,
            ttl=0,
            params=dict(mci=mci, data_ant=data_ant, data=st.session_state["data"]),
        )

        if base.empty:
            st.toast("###### Não há dados para enviar...", icon=":material/error:")

        else:
            base["pk"] = base.apply(lambda x: f"{x['cpf_cnpj']}-{x['cod_titulo']}", axis=1)
            base = base.groupby("pk").first()
            base = base[base["cpf_cnpj"].ne(60777661000150) & base["cpf_cnpj"].gt(0) & base["quantidade"].ne(0)]

            if base.empty:
                st.toast("###### Não há dados para enviar...", icon=":material/error:")

            else:
                base.reset_index(drop=True, inplace=True)
                base["reserva"] = "            "
                base.drop(["mci", "DATA"], axis=1, inplace=True)
                pega = base.copy()

                for row in base["cod_titulo"].unique():
                    pega = base[base["cod_titulo"].eq(row)].copy()

                    pega["listar"] = pega.apply(lambda x: f"{x['tipo']}{x['pss']}{x['cpf_cnpj']:0>19}"
                                                          f"{x['quantidade']:0>17}{x['reserva']}", axis=1)

                    trailer: str = (f"static/escriturais/@deletar/resolucao160-"
                                    f"{st.session_state['empresa'].replace('/', '.')}-tipo{row}.txt")

                    pega["listar"].to_csv(trailer, header=False, index=False)

                    with open(trailer, "a") as f:
                        f.write(f"9 {len(pega) + 1:0>19}{pega['quantidade'].sum():0>17}            ")

                st.toast("###### Criação de TXT gerada com sucesso, está na pasta específica.",
                         icon=":material/check_circle:")
