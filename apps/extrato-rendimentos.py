import locale

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")

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


def load_cadastro(field: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT t1.COD AS MCI_EMPRESA, STRIP(t1.NOM) AS EMPRESA, LPAD(t1.COD_CPF_CGC, 14, '0') AS CNPJ
            FROM DB2MCI.CLIENTE t1
            WHERE t1.{field.upper()} = :value
        """,
        show_spinner=False,
        ttl=0,
        params=dict(value=value),
    )


def load_extrato(field: str, _mci: int, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT
                t1.CD_TIP_TIT AS TIPO,
                t1.DT_MVT_DRT AS DATA_MVT,
                CAST(t1.QT_MVT_REN AS INT) AS QUANTIDADE,
                CAST(t1.VL_MVT_REN AS FLOAT) AS VALOR,
                CAST(t1.VL_IR_CLCD_MVT_REN AS FLOAT) AS VALOR_IR,
                CAST(t1.VL_MVT_REN - t1.VL_IR_CLCD_MVT_REN AS FLOAT) AS VALOR_LIQUIDO,
                t3.NM_TIP_DRT AS TIPO_DIREITO,
                t4.NM_EST_DRT AS ESTADO,
                CASE
                    WHEN t1.CD_FMA_PGTO_REN = 1 THEN 'CAIXA'
                    WHEN t1.CD_FMA_PGTO_REN = 2 THEN 'CONTA'
                    ELSE '-'
                END AS FORMA_PAGAMENTO
            FROM
                DB2AEB.MVT_REN t1
                    INNER JOIN DB2MCI.CLIENTE t2
                        ON t2.COD = t1.CD_CLI_TITR
                    INNER JOIN DB2AEB.TIP_DRT t3
                        ON t3.CD_TIP_DRT = t1.CD_TIP_DRT
                    INNER JOIN DB2AEB.EST_DRT t4
                        ON t4.CD_EST_DRT = t1.CD_EST_DRT
            WHERE
                t1.CD_CLI_EMT = :mci AND
                {field} = :value
            ORDER BY
                t1.DT_MVT_DRT,
                t1.CD_EST_DRT,
                t1.CD_TIP_DRT
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, value=value),
    )


st.subheader(":material/local_atm: Extrato de Rendimentos")

kv: dict[str, int] = load_client()

with st.columns(2)[0]:
    st.selectbox("**Empresa:**", options=kv.keys(), key="empresa")
    st.text_input("**Nome do Investidor:**", key="nome_investidor", max_chars=100)

    col1, col2 = st.columns(2)
    col1.number_input("**MCI:**", min_value=0, max_value=9999999999, key="mci_investidor")
    col2.number_input("**CPF / CNPJ:**", min_value=0, max_value=99999999999999, key="cpf_cnpj_investidor")

    st.button("**Pesquisar**", key="pesquisar", type="primary", icon=":material/search:")

if st.session_state["pesquisar"]:
    mci: int = kv.get(st.session_state["empresa"])

    df_office: pd.DataFrame = load_cadastro("cod", mci)
    nome_office: str = df_office["empresa"]
    cnpj_office: str = df_office["cnpj"]

    if not any([st.session_state["nome_investidor"], st.session_state["mci_investidor"],
                st.session_state["cpf_cnpj_investidor"]]):
        st.toast("###### Deve preencher ao menos 1 campo abaixo.", icon=":material/warning:")
        st.stop()

    if all([st.session_state["nome_investidor"], st.session_state["mci_investidor"],
            st.session_state["cpf_cnpj_investidor"]]):
        st.toast("###### Só deve preencher 1 campo abaixo.", icon=":material/warning:")
        st.stop()

    with st.spinner("**:material/hourglass: Pesquisando os dados, aguarde...**", show_time=True):
        df_cadastro: pd.DataFrame = load_cadastro(
            field="nom" if st.session_state["nome_investidor"] else
            "cod" if st.session_state["mci_investidor"] else "cod_cpf_cgc",
            value=unidecode(st.session_state["nome_investidor"]).upper() if st.session_state["nome_investidor"] else
            st.session_state["mci_investidor"] if st.session_state["mci_investidor"] else
            st.session_state["cpf_cnpj_investidor"]
        )

        df_extrato: pd.DataFrame = load_extrato(
            field="t2.NOM" if st.session_state["nome_investidor"] else
            "t1.CD_CLI_TITR" if st.session_state["mci_investidor"] else
            "t2.COD_CPF_CGC",
            _mci=mci,
            value=unidecode(st.session_state["nome_investidor"]).upper() if st.session_state["nome_investidor"] else
            st.session_state["mci_investidor"] if st.session_state["mci_investidor"] else
            st.session_state["cpf_cnpj_investidor"]
        )

        if not df_extrato.empty:
            st.data_editor(
                data=df_extrato,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "tipo": st.column_config.NumberColumn("Tipo"),
                    "data_mvt": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "quantidade": st.column_config.NumberColumn("Quantidade"),
                    "valor": st.column_config.NumberColumn("Valor", format="dollar"),
                    "valor_ir": st.column_config.NumberColumn("Valor IR", format="dollar"),
                    "valor_liquido": st.column_config.NumberColumn("Valor Líquido", format="dollar"),
                    "tipo_direito": st.column_config.TextColumn("Tipo de Direito"),
                    "estado": st.column_config.TextColumn("Estado"),
                    "forma_pagamento": st.column_config.TextColumn("Forma de Pagamento"),
                },
            )

            st.button("**Voltar**", key="back", type="primary", icon=":material/reply:")

        else:
            st.toast("###### Não foram encontrados rendimentos para a pesquisa realizada.", icon=":material/error:")
