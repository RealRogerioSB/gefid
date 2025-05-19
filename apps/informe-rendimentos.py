import re
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from streamlit.elements.lib.column_types import ColumnConfig
from unidecode import unidecode

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)


def get_join_email(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT DISTINCT
                t1.CD_CLI_ACNT AS MCI_INVESTIDOR,
                CASE
                    WHEN t1.CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO'
                    ELSE 'NÃO ENVIADO'
                END AS STATUS,
                t1.TS_INC_PRCT_EMAI AS LOG,
                t1.TX_END_EMAI AS EMAIL
            FROM
                DB2I13E5.IR{date.today().year}_ENVIO_EMAILS t1
                LEFT JOIN DB2I13E5.IR{date.today().year}_CADASTRO_BB t2
                    ON t2.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                LEFT JOIN DB2I13E5.IR{date.today().year}_CADASTRO_B3 t3
                    ON t3.MCI_INVESTIDOR = t1.CD_CLI_ACNT
            WHERE
                t2.{key.upper()} = :value OR
                t3.{key.upper()} = :value
        """,
        show_spinner=False,
        ttl=0,
        params=dict(value=value),
    )


def get_email(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT DISTINCT
                CD_CLI_ACNT AS MCI_INVESTIDOR,
                CASE
                    WHEN CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO'
                    ELSE 'NÃO ENVIADO'
                END AS STATUS,
                TS_INC_PRCT_EMAI AS LOG,
                TX_END_EMAI AS EMAIL
            FROM
                DB2I13E5.IR{date.today().year}_ENVIO_EMAILS
            WHERE
                {key.upper()} = :value
        """,
        show_spinner=False,
        ttl=0,
        params=dict(value=value),
    )


def get_bb(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"SELECT * FROM DB2I13E5.IR2025_CADASTRO_BB WHERE {key.upper()} = :value",
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


def get_b3(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"SELECT * FROM DB2I13E5.IR2025_CADASTRO_B3 WHERE {key.upper()} = :value",
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


st.subheader(f":material/ad: Informe de Rendimentos - {date.today().year}")

params: dict[str, bool | ColumnConfig] = dict(
    hide_index=True,
    use_container_width=True,
    column_config=dict(
        mci_investidor=st.column_config.NumberColumn(label="MCI"),
        investidor=st.column_config.TextColumn(label="Investidor"),
        status=st.column_config.TextColumn(label="Status", disabled=True),
        log=st.column_config.DatetimeColumn(label="Log", disabled=True, format="DD/MM/YYYY HH:MM:SS"),
        cpf_cnpj=st.column_config.TextColumn(label="CPF/CNPJ", disabled=True),
        email=st.column_config.TextColumn(label="E-mail", disabled=True),
    )
)


def report(mail: pd.DataFrame, bb: pd.DataFrame, b3: pd.DataFrame) -> None:
    st.markdown("")

    with st.columns(2)[0].container(border=True):
        st.markdown("##### Resultado da Pesquisa")

        st.markdown("###### Dados do envio:")
        if mail.empty:
            st.write("Não localizamos email enviados.")
        else:
            st.dataframe(data=mail, **params)

        st.markdown("###### Dados do MCI:")
        if bb.empty:
            st.write("Não localizamos dados no recorte da MCI.")
        else:
            st.dataframe(data=bb, **params)

        st.markdown("###### Dados do B3:")
        if b3.empty:
            st.write("Não localizamos dados na B3.")
        else:
            st.dataframe(data=b3, **params)

        st.button("**Voltar**", key="btn_back", type="primary", icon=":material/reply:")


with st.container():
    with st.columns(2)[0]:
        st.markdown("##### Informe de Rendimentos de Ativos Escriturais")

        st.text_input(label="**Investidor:**", key="nome_inv", placeholder="Digite o nome do Investidor")

        col1, col2 = st.columns(2)
        col1.text_input(label="**MCI:**", key="mci_inv", placeholder="Digite o número do MCI")
        col2.text_input(label="**CPF / CNPJ:**", key="cpf_cnpj", placeholder="Digite o número do CPF ou CNPJ")

        st.text_input(label="**E-mail:**", key="mail_inv", placeholder="Digite o e-mail do Investidor")
        st.button(label="**Pesquisar**", key="search", type="primary", icon=":material/search:")

if st.session_state["search"]:
    if all([st.session_state["nome_inv"], st.session_state["mci_inv"], st.session_state["cpf_cnpj"],
            st.session_state["mail_inv"]]):
        st.toast("###### Deve preencher somente um campo para pesquisar.", icon=":material/warning:")
        st.stop()

    if not any([st.session_state["nome_inv"], st.session_state["mci_inv"], st.session_state["cpf_cnpj"],
                st.session_state["mail_inv"]]):
        st.toast("###### Precisa digitar um campo qualquer para pesquisar.", icon=":material/warning:")
        st.stop()

    with st.spinner(text=":material/hourglass: Obtendo os dados, aguarde...", show_time=True):
        if st.session_state["nome_inv"] != "":
            report(
                get_join_email("investidor", unidecode(st.session_state["nome_inv"]).upper()),
                get_bb("investidor", unidecode(st.session_state["nome_inv"]).upper()),
                get_b3("investidor", unidecode(st.session_state["nome_inv"]).upper())
            )

        elif st.session_state["mci_inv"] != "":
            if re.sub(r"\D", "", st.session_state["mci_inv"]):
                report(
                    get_email("cd_cli_acnt", re.sub(r"\D", "", st.session_state["mci_inv"])),
                    get_bb("mci_investidor", re.sub(r"\D", "", st.session_state["mci_inv"])),
                    get_b3("mci_investidor", re.sub(r"\D", "", st.session_state["mci_inv"]))
                )
            else:
                st.toast("###### O campo MCI está inválido...", icon=":material/warning:")

        elif st.session_state["cpf_cnpj"] != "":
            if re.sub(r"\D", "", st.session_state["cpf_cnpj"]):
                report(
                    get_join_email("cpf_cnpj", re.sub("\D", "", st.session_state["cpf_cnpj"])),
                    get_bb("cpf_cnpj", re.sub("\D", "", st.session_state["cpf_cnpj"])),
                    get_b3("cpf_cnpj", re.sub("\D", "", st.session_state["cpf_cnpj"]))
                )
            else:
                st.toast("###### O Campo CPF / CNPJ está inválido...", icon=":material/warning:")

        elif st.session_state["mail_inv"] != "":
            report(
                get_email("tx_end_emai", st.session_state["mail_inv"].lower()),
                get_bb("email", st.session_state["mail_inv"].lower()),
                get_b3("email", st.session_state["mail_inv"].lower())
            )
