import os
import re
from datetime import date

import polars as pl
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from unidecode import unidecode

load_dotenv()

conn = create_engine(os.getenv("DB2"))

st.subheader(f":material/ad: Informe de Rendimentos - {date.today().year}")

params_columns = dict(
    MCI_INVESTIDOR=st.column_config.Column(label="MCI", disabled=True),
    INVESTIDOR=st.column_config.Column(label="INVESTIDOR", disabled=True),
    STATUS=st.column_config.Column(label="STATUS", disabled=True),
    LOG=st.column_config.DatetimeColumn(label="LOG", disabled=True, format="DD/MM/YYYY HH:MM:SS"),
    CPF_CNPJ=st.column_config.Column(label="CPF / CNPJ", disabled=True),
    EMAIL=st.column_config.Column(label="E-MAIL", disabled=True),
)


@st.cache_data(show_spinner=False)
def get_join_email(field, value):
    return pl.read_database(
        query="""
            SELECT DISTINCT
                t1.CD_CLI_ACNT AS MCI_INVESTIDOR,
                CASE WHEN t1.CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO' ELSE 'NÃO ENVIADO' END AS STATUS,
                t1.TS_INC_PRCT_EMAI AS LOG,
                t1.TX_END_EMAI AS EMAIL
            FROM
                DB2I13E5.IR2025_ENVIO_EMAILS t1
                LEFT JOIN DB2I13E5.IR2025_CADASTRO_BB t2
                    ON t2.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                LEFT JOIN DB2I13E5.IR2025_CADASTRO_B3 t3
                    ON t3.MCI_INVESTIDOR = t1.CD_CLI_ACNT
            WHERE
                t2.{0} = {1} OR
                t3.{0} = {1}
        """.format(field.upper(), value if value.isdigit() else repr(value)),
        connection=conn,
        infer_schema_length=None
    )


@st.cache_data(show_spinner=False)
def get_email(field, value):
    return pl.read_database(
        query="""
            SELECT DISTINCT
                CD_CLI_ACNT AS MCI_INVESTIDOR,
                CASE WHEN CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO' ELSE 'NÃO ENVIADO' END AS STATUS,
                TS_INC_PRCT_EMAI AS LOG,
                TX_END_EMAI AS EMAIL
            FROM
                DB2I13E5.IR2025_ENVIO_EMAILS
            WHERE
                {0} = {1}
        """.format(field.upper(), value if value.isdigit() else repr(value)),
        connection=conn,
        infer_schema_length=None
    )


@st.cache_data(show_spinner=False)
def get_bb(field, value):
    return pl.read_database(
        query=("SELECT * FROM DB2I13E5.IR2025_CADASTRO_BB WHERE {0} = {1}"
               .format(field.upper(), value if value.isdigit() else repr(value))),
        connection=conn,
        infer_schema_length=None
    )


@st.cache_data(show_spinner=False)
def get_b3(field, value):
    return pl.read_database(
        query=("SELECT * FROM DB2I13E5.IR2025_CADASTRO_B3 WHERE {0} = {1}"
               .format(field.upper(), value if value.isdigit() else repr(value))),
        connection=conn,
        infer_schema_length=None
    )


def report(mail: pl.DataFrame, bb: pl.DataFrame, b3: pl.DataFrame) -> None:
    with st.container(border=True):
        st.markdown("##### Resultado da Pesquisa")
        st.markdown("###### Dados do envio:")

        if len(mail) > 0:
            st.dataframe(data=mail, column_config=params_columns)
        else:
            st.write("Não localizamos email enviados.")

        st.markdown("###### Dados do MCI:")
        if len(bb) > 0:
            st.dataframe(data=bb, column_config=params_columns)
        else:
            st.write("Não localizamos dados no recorte da tabela MCI.")

        st.markdown("###### Dados do B3:")
        if len(b3) > 0:
            st.dataframe(data=b3, column_config=params_columns)
        else:
            st.write("Não localizamos dados na tabela de cadastro da B3.")

        st.button("**Voltar**", key="btn_back", type="primary")


with st.container(border=True):
    st.markdown("###### Informe de Rendimentos de Ativos Escriturais (somente preencha um campo abaixo)")

    tx_nome = st.text_input(label="**Nome do Investidor:**", placeholder="Digite o nome do Investidor")
    tx_mci = st.text_input(label="**MCI:**", placeholder="Digite o número do MCI")
    tx_cpf_cnpj = st.text_input(label="**CPF / CNPJ:**", placeholder="Digite o número do CPF ou CNPJ")
    tx_email = st.text_input(label="**E-mail:**", placeholder="Digite o e-mail do Investidor")

    if st.button(label="**Pesquisar**", key="btn_search", type="primary"):
        with st.spinner(text="Obtendo os dados, aguarde...", show_time=True):
            if not any([tx_nome, tx_mci, tx_cpf_cnpj, tx_email]):
                st.toast("**Precisa digitar qualquer um campo para pesquisar, pelo menos...**", icon="⚠️")

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
                    st.toast("**O campo MCI está inválido...**", icon="⚠️")

            elif tx_cpf_cnpj != "":
                if re.sub(r"\D", "", tx_cpf_cnpj):
                    report(
                        get_join_email("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj)),
                        get_bb("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj)),
                        get_b3("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj))
                    )
                else:
                    st.toast("**O Campo CPF / CNPJ está inválido...**", icon="⚠️")

            elif tx_email != "":
                report(
                    get_email("tx_end_emai", tx_email.lower()),
                    get_bb("email", tx_email.lower()),
                    get_b3("email", tx_email.lower())
                )

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)
