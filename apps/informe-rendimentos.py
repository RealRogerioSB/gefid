import re
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

st.cache_data.clear()

engine = st.connection(name="DB2", type=SQLConnection)

st.subheader(f":material/ad: Informe de Rendimentos - {date.today().year}")

params_columns = dict(
    mci_investidor=st.column_config.Column(label="MCI", disabled=True),
    investidor=st.column_config.Column(label="Investidor", disabled=True),
    status=st.column_config.Column(label="Status", disabled=True),
    log=st.column_config.DatetimeColumn(label="Log", disabled=True, format="DD/MM/YYYY HH:MM:SS"),
    cpf_cnpj=st.column_config.Column(label="CPF / CNPJ", disabled=True),
    email=st.column_config.Column(label="E-mail", disabled=True),
)


@st.cache_data(show_spinner=False)
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
                DB2I13E5.IR2025_ENVIO_EMAILS t1
                LEFT JOIN DB2I13E5.IR2025_CADASTRO_BB t2
                    ON t2.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                LEFT JOIN DB2I13E5.IR2025_CADASTRO_B3 t3
                    ON t3.MCI_INVESTIDOR = t1.CD_CLI_ACNT
            WHERE
                t2.{key.upper()} = :value OR
                t3.{key.upper()} = :value
        """,
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


@st.cache_data(show_spinner=False)
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
                DB2I13E5.IR2025_ENVIO_EMAILS
            WHERE
                {key.upper()} = :value
        """,
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


@st.cache_data(show_spinner=False)
def get_bb(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"SELECT * FROM DB2I13E5.IR2025_CADASTRO_BB WHERE {key.upper()} = :value",
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


@st.cache_data(show_spinner=False)
def get_b3(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"SELECT * FROM DB2I13E5.IR2025_CADASTRO_B3 WHERE {key.upper()} = :value",
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


def report(mail: pd.DataFrame, bb: pd.DataFrame, b3: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown("##### Resultado da Pesquisa")
        st.markdown("###### Dados do envio:")

        if len(mail) > 0:
            st.dataframe(data=mail, hide_index=True, column_config=params_columns)
        else:
            st.write("Não localizamos email enviados.")

        st.markdown("###### Dados do MCI:")
        if len(bb) > 0:
            st.dataframe(data=bb, hide_index=True, column_config=params_columns)
        else:
            st.write("Não localizamos dados no recorte da tabela MCI.")

        st.markdown("###### Dados do B3:")
        if len(b3) > 0:
            st.dataframe(data=b3, hide_index=True, column_config=params_columns)
        else:
            st.write("Não localizamos dados na tabela de cadastro da B3.")

        st.button("**Voltar**", key="btn_back", type="primary")


with st.container():
    with st.columns(2)[0]:
        st.markdown("###### Informe de Rendimentos de Ativos Escriturais (somente preencha um campo abaixo)")

        tx_nome = st.text_input(label="**Nome do Investidor:**", placeholder="Digite o nome do Investidor")
        tx_mci = st.text_input(label="**MCI:**", placeholder="Digite o número do MCI")
        tx_cpf_cnpj = st.text_input(label="**CPF / CNPJ:**", placeholder="Digite o número do CPF ou CNPJ")
        tx_email = st.text_input(label="**E-mail:**", placeholder="Digite o e-mail do Investidor")

        if st.button(label="**Pesquisar**", key="btn_search", type="primary"):
            with st.spinner(text=":material/hourglass: Obtendo os dados, aguarde...", show_time=True):
                if not any([tx_nome, tx_mci, tx_cpf_cnpj, tx_email]):
                    st.toast("**Precisa digitar qualquer um campo para pesquisar, pelo menos...**",
                             icon=":material/warning:")

                elif tx_nome != "":
                    report(
                        get_join_email("investidor", unidecode(tx_nome).upper()),
                        get_bb("investidor", unidecode(tx_nome).upper()),
                        get_b3("investidor", unidecode(tx_nome).upper())
                    )

                elif tx_mci != "":
                    if re.sub(r"\D", "", tx_mci):
                        report(
                            get_email("cd_cli_acnt", re.sub(r"\D", "", tx_mci)),
                            get_bb("mci_investidor", re.sub(r"\D", "", tx_mci)),
                            get_b3("mci_investidor", re.sub(r"\D", "", tx_mci))
                        )
                    else:
                        st.toast("**O campo MCI está inválido...**", icon=":material/warning:")

                elif tx_cpf_cnpj != "":
                    if re.sub(r"\D", "", tx_cpf_cnpj):
                        report(
                            get_join_email("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj)),
                            get_bb("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj)),
                            get_b3("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj))
                        )
                    else:
                        st.toast("**O Campo CPF / CNPJ está inválido...**", icon=":material/warning:")

                elif tx_email != "":
                    report(
                        get_email("tx_end_emai", tx_email.lower()),
                        get_bb("email", tx_email.lower()),
                        get_b3("email", tx_email.lower())
                    )
