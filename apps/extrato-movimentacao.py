import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)


@st.cache_data(show_spinner="**:material/hourglass: Preparando a listagem da empresa, aguarde...**")
def load_client() -> dict[str, int]:
    load: pd.DataFrame = engine.query(
        sql="""
            SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
            FROM DB2AEB.PRM_EMP t1 INNER JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_EMT
            WHERE t1.DT_ECR_CTR IS NULL
            ORDER BY STRIP(t2.NOM)
        """,
        show_spinner=False,
        ttl=0
    )
    return {k: v for k, v in zip(load["nom"].to_list(), load["mci"].to_list())}


def load_empresa(field: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT
                COD AS MCI_EMPRESA,
                STRIP(NOM) AS NOME_EMPRESA,
                CASE
                    WHEN COD_TIPO = 2 THEN LPAD(COD_CPF_CGC, 14, '0')
                    ELSE LPAD(COD_CPF_CGC, 11, '0')
                END AS CNPJ_EMPRESA
            FROM
                DB2MCI.CLIENTE
            WHERE
                {field.upper()} = :value
        """,
        show_spinner=False,
        ttl=0,
        params=dict(value=value)
    )


def load_extrato(join: str, field: str, _mci: int, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT
                t0.SG_TIP_TIT AS SIGLA,
                t1.CD_TIP_TIT AS TIPO,
                t1.DT_MVTC AS DATA_MVTC,
                SUM(CAST(t1.QT_TIT_MVTD AS BIGINT)) AS MOVIMENTO,
                SUM(CAST(t1.QT_TIT_ATU AS BIGINT)) AS SALDO,
                CAST(SUM(t1.QT_TIT_ATU - t1.QT_TIT_MVTD) AS BIGINT) AS SALDO_ANTERIOR,
                t1.CD_CLI_CSTD AS MCI_CUSTODIANTE
            FROM
                DB2AEB.TIP_TIT t0
                RIGHT JOIN DB2AEB.MVTC_DIAR_PSC t1
                    ON t1.CD_TIP_TIT = t0.CD_TIP_TIT{join}
            WHERE
                t1.CD_CLI_EMT = :mci AND
                {field} = :value
            GROUP BY
                t0.SG_TIP_TIT,
                t1.CD_TIP_TIT,
                t1.DT_MVTC,
                t1.CD_CLI_CSTD
            ORDER BY
                t1.DT_MVTC
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, value=value)
    )


with st.columns(2)[0]:
    st.subheader(":material/wysiwyg: Extrato de Movimentação")

    st.markdown("##### Extrato de Movimentação de Ativos dos últimos 12 meses")

    kv: dict[str, int] = load_client()

    st.selectbox(label="**Empresa:**", options=kv.keys(), key="empresa")
    st.text_input(label="**Nome Investidor:**", max_chars=100, key="nome_inv")

    col = st.columns([1.3, 1.6, 1.4])

    col[0].number_input(label="**MCI:**", min_value=0, max_value=9999999999, key="mci_inv")
    col[1].number_input(label="**CPF/CNPJ:**", min_value=0, max_value=99999999999999, key="cpf_cnpj_inv")
    col[2].selectbox(label="**Custodiante:**", options=["Ambas", "Banco do Brasil", "B3"], key="custodiante")

    st.button(label="**Pesquisar**", key="search", type="primary", icon=":material/search:")

    st.markdown("")

if st.session_state["search"]:
    mci: int = kv.get(st.session_state["empresa"])

    idx_custodia: int = 0 if st.session_state["custodiante"] == "Ambas" \
        else 903485186 if st.session_state["custodiante"] == "Banco do Brasil" else 205007939

    if all([st.session_state["nome_inv"], st.session_state["mci_inv"], st.session_state["cpf_cnpj_inv"]]):
        st.toast("###### Só deve preencher um dos campos abaixo", icon=":material/warning:")
        st.stop()

    if not any([st.session_state["nome_inv"], st.session_state["mci_inv"], st.session_state["cpf_cnpj_inv"]]):
        st.toast("###### Deve preencher ao menos um dos campos abaixo", icon=":material/warning:")
        st.stop()

    with st.spinner("**:material/hourglass: Preparando os dados para exibir, aguarde...**", show_time=True):
        cliente: pd.DataFrame = load_empresa("cod", mci)

        investidor: pd.DataFrame = load_empresa(
            field="nom" if st.session_state["nome_inv"] else "cod" if st.session_state["mci_inv"]
            else "cod_cpf_cgc",
            value=unidecode(st.session_state["nome_inv"]).upper() if st.session_state["nome_inv"]
            else st.session_state["mci_inv"] if st.session_state["mci_inv"]
            else st.session_state["cpf_cnpj_inv"],
        )

        extrato: pd.DataFrame = load_extrato(
            join=" LEFT JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_EMT" if st.session_state["nome_inv"]
            else "" if st.session_state["mci_inv"] else " INNER JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_EMT",
            field="t2.NOM" if st.session_state["nome_inv"] else "t1.CD_CLI_ACNT" if st.session_state["mci_inv"]
            else "t2.COD_CPF_CGC",
            _mci=mci,
            value=unidecode(st.session_state["nome_inv"]).upper() if st.session_state["nome_inv"]
            else st.session_state["mci_inv"] if st.session_state["mci_inv"]
            else st.session_state["cpf_cnpj_inv"],
        )

        extrato = extrato[extrato["mci_custodiante"].eq(idx_custodia)] if idx_custodia != 0 else extrato

        if extrato.empty:
            st.toast("###### Não ocorreram movimentações nos últimos 12 meses.", icon=":material/error:")

        else:
            with st.columns(2)[0]:
                col1, col2 = st.columns(2, border=True)

                with col1:
                    st.markdown(f"**Empresa:**: {cliente['nome_empresa'].iloc[0]}")
                    st.markdown(f"**MCI:**: {cliente['mci_empresa'].iloc[0]}")
                    st.markdown(f"**CNPJ:**: {cliente['cnpj_empresa'].iloc[0]}")

                with col2:
                    st.markdown(f"**Investidor:**: {investidor['nome_empresa'].iloc[0]}")
                    st.markdown(f"**MCI:**: {investidor['mci_empresa'].iloc[0]}")
                    st.markdown(f"**CPF/CNPJ:**: {investidor['cnpj_empresa'].iloc[0]}")

                st.markdown("")

                st.dataframe(
                    data=extrato,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "sigla": st.column_config.TextColumn(label="Sigla"),
                        "data_mvtc": st.column_config.DateColumn(label="Data", format="DD/MM/YYYY"),
                        "movimento": st.column_config.NumberColumn(label="Movimento"),
                        "saldo": st.column_config.NumberColumn(label="Saldo"),
                        "saldo_anterior": st.column_config.NumberColumn(label="Saldo Anterior"),
                        "mci_custodiante": st.column_config.NumberColumn(label="MCI de Custodiante"),
                    },
                )

            st.button("**Voltar**", type="primary", icon=":material/reply:")
