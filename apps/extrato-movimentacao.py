import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/wysiwyg: Extrato de Movimentação")

st.markdown("##### Extrato de Movimentação de Ativos dos últimos 12 meses")

stmt_load_nome: str = """
    SELECT
        t1.CD_TIP_TIT AS TIPO,
        CAST(t1.DT_MVTC AS DATE) AS DATA,
        CAST(t1.QT_TIT_MVTD AS INT) AS MOVIMENTO,
        CAST(t1.QT_TIT_ATU AS INT) AS SALDO,
        t1.CD_CLI_CSTD AS MCI_CUSTODIANTE
    FROM
        DB2AEB.MVTC_DIAR_PSC t1
        LEFT JOIN DB2MCI.CLIENTE AS t2
            ON t2.COD = t1.CD_CLI_EMT
    WHERE
        t1.CD_CLI_EMT = :mci AND
        t2.NOM = :value
    ORDER BY
        t1.DT_MVTC
"""

stmt_load_mci: str = """
    SELECT t1.CD_TIP_TIT AS TIPO,
        CAST(t1.DT_MVTC AS DATE) AS DATA,
        CAST(t1.QT_TIT_MVTD AS INT) AS MOVIMENTO,
        CAST(t1.QT_TIT_ATU AS INT) AS SALDO,
        t1.CD_CLI_CSTD AS MCI_CUSTODIANTE
    FROM
        DB2AEB.MVTC_DIAR_PSC t1
    WHERE
        t1.CD_CLI_EMT = :mci AND
        t1.CD_CLI_ACNT = :value
    ORDER BY
        t1.DT_MVTC
"""

stmt_load_cpf_cgc: str = """
    SELECT
        t1.CD_TIP_TIT AS TIPO,
        CAST(t1.DT_MVTC AS DATE) AS DATA,
        CAST(t1.QT_TIT_MVTD AS INT) AS MOVIMENTO,
        CAST(t1.QT_TIT_ATU AS INT) AS SALDO,
        t1.CD_CLI_CSTD AS MCI_CUSTODIANTE
    FROM
        DB2AEB.MVTC_DIAR_PSC t1
        INNER JOIN DB2MCI.CLIENTE AS t2
            ON t2.COD = t1.CD_CLI_EMT
    WHERE
        t1.CD_CLI_EMT = :mci AND
        t2.COD_CPF_CGC = :value
    ORDER BY
        t1.DT_MVTC
"""


@st.cache_data(show_spinner="**:material/hourglass: Preparando a listagem da empresa, aguarde...**")
def load_client() -> dict[int, str]:
    load: pd.DataFrame = engine.query(
        sql="""SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
               FROM DB2AEB.PRM_EMP t1 INNER JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_EMT
               WHERE t1.DT_ECR_CTR IS NULL
               ORDER BY STRIP(t2.NOM)""",
        show_spinner=False,
        ttl=0
    )
    return {k: v for k, v in zip(load["mci"].to_list(), load["nom"].to_list())}


def load_empresa(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""SELECT t1.COD AS mci_empresa,
                       t1.NOM AS nm_empresa,
                       CASE
                           WHEN t1.COD_TIPO = 2 THEN LPAD(t1.COD_CPF_CGC, 14, '0')
                           ELSE LPAD(t1.COD_CPF_CGC, 11, '0')
                       END AS cnpj_empresa
                FROM DB2MCI.CLIENTE t1
                WHERE t1.{key.upper()} = :value""",
        show_spinner=False,
        ttl=0,
        params=dict(value=value)
    )


def load_extrato(n_load: int, _mci: int, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=stmt_load_nome if n_load == 0 else stmt_load_mci if n_load == 1 else stmt_load_cpf_cgc,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, value=value)
    )


def load_tipo(_tipo: int) -> pd.DataFrame:
    return engine.query(
        sql="SELECT t1.SG_TIP_TIT FROM DB2AEB.TIP_TIT t1 WHERE t1.CD_TIP_TIT = :tipo",
        show_spinner=False,
        ttl=0,
        params=dict(tipo=_tipo)
    )


with st.columns(2)[0]:
    kv: dict[int, str] = load_client()

    st.selectbox(label="**Empresa:**", options=kv.values(), key="empresa")
    st.text_input(label="**Nome Investidor:**", max_chars=100, key="nome_investidor")

    col = st.columns([1.3, 1.6, 1.4])

    col[0].number_input(label="**MCI:**", min_value=0, max_value=9999999999, key="mci_investidor")
    col[1].number_input(label="**CPF/CNPJ:**", min_value=0, max_value=99999999999999, key="cpf_cnpj_investidor")
    col[2].selectbox(label="**Custodiante:**", options=["Ambas", "Banco do Brasil", "B3"], key="custodiante")

    st.button(label="**Pesquisar**", key="search", type="primary", icon=":material/search:")

if st.session_state["search"]:
    mci: int = next((chave for chave, valor in kv.items() if valor == st.session_state["empresa"]), 0)

    idx_custodia: int = 0 if st.session_state["custodiante"] == "Ambas" \
        else 903485186 if st.session_state["custodiante"] == "Banco do Brasil" else 205007939

    if not any([st.session_state["nome_investidor"], st.session_state["mci_investidor"],
                st.session_state["cpf_cnpj_investidor"]]):
        st.toast("**Deve preencher ao menos um dos campos abaixo**", icon=":material/warning:")
        st.stop()

    with st.spinner("**:material/hourglass: Preparando os dados para exibir, aguarde...**", show_time=True):
        cliente: pd.DataFrame = load_empresa("cod", mci)

        investidor: pd.DataFrame = load_empresa(
            key="nom" if st.session_state["nome_investidor"]
            else "cod" if st.session_state["mci_investidor"]
            else "cod_cpf_cgc",
            value=unidecode(st.session_state["nome_investidor"]).upper() if st.session_state["nome_investidor"]
            else st.session_state["mci_investidor"] if st.session_state["mci_investidor"]
            else st.session_state["cpf_cnpj_investidor"],
        )

        extrato: pd.DataFrame = load_extrato(
            n_load=0 if st.session_state["nome_investidor"] else 1 if st.session_state["mci_investidor"] else 2,
            _mci=mci,
            value=unidecode(st.session_state["nome_investidor"]).upper() if st.session_state["nome_investidor"]
            else st.session_state["mci_investidor"] if st.session_state["mci_investidor"]
            else st.session_state["cpf_cnpj_investidor"],
        )

        if idx_custodia != 0:
            extrato = extrato[extrato["mci_custodiante"].eq(idx_custodia)]

        extrato["pk"] = extrato["tipo"] + extrato["mci_custodiante"]
        extratos = extrato["pk"].drop_duplicates().to_list()

        saldo_anteriores: list[int] = []
        custodiantes: list[str] = []
        tipos: list[str] = []

        if extrato.empty:
            st.toast("**Não ocorreram movimentações nos últimos 12 meses**", icon=":material/error:")
            st.stop()

        for _extrato in extratos:
            consulta: pd.DataFrame = extrato[extrato["pk"].eq(_extrato)].copy()
            consulta.reset_index(inplace=True)

            saldo_anteriores.append(consulta["saldo"][0] - consulta["movimento"][0])

            if consulta["mci_custodiante"][0] == 903485186:
                custodiantes.append("Banco do Brasil")
            elif consulta["mci_custodiante"][0] == 205007939:
                custodiantes.append("B3")

            tipo = consulta["tipo"].iloc[0]
            tipo = engine.query(
                sql="SELECT t1.SG_TIP_TIT FROM DB2AEB.TIP_TIT t1 WHERE t1.CD_TIP_TIT = :tipo",
                show_spinner="**:material/hourglass: Obtendo os dados, aguarde...**",
                ttl=0,
                params=dict(tipo=tipo)
            )
            tipos.append(tipo["sg_tip_tit"][0])

            consulta.drop(["tipo", "mci_custodiante", "pk"], axis=1, inplace=True)

        with st.columns(2)[0]:
            st.dataframe(
                data=cliente,
                hide_index=True,
                column_config={
                    "mci_empresa": st.column_config.NumberColumn(label="MCI Empresa"),
                    "nm_empresa": st.column_config.TextColumn(label="Empresa"),
                    "cnpj_empresa": st.column_config.TextColumn(label="CNPJ"),
                },
            )

            st.dataframe(
                data=investidor,
                hide_index=True,
                column_config={
                    "mci_empresa": st.column_config.NumberColumn(label="MCI Investidor"),
                    "nm_empresa": st.column_config.TextColumn(label="Investidor"),
                    "cnpj_empresa": st.column_config.TextColumn(label="CPF/CNPJ"),
                },
            )

            st.dataframe(
                data=extrato,
                hide_index=True,
                column_config={
                    "tipo": st.column_config.NumberColumn(label="Tipo"),
                    "DATA": st.column_config.DateColumn(label="Data", format="DD/MM/YYYY"),
                    "movimento": st.column_config.NumberColumn(label="Movimento"),
                    "saldo": st.column_config.NumberColumn(label="Saldo"),
                    "mci_custodiante": st.column_config.NumberColumn(label="MCI de Custodiante"),
                },
            )

        st.button("**Voltar**", type="primary", icon=":material/reply:")
