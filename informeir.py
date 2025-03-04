import re

import streamlit as st
from unidecode import unidecode
from conn import conn

st.set_page_config(
    page_title="Intranet DIOPE GEFID",
    page_icon="img/bb_ico.ico",
    layout="wide",
)

st.logo("img/bb_logo.jpg", size="large", link="https://gefid-aplic-1.intranet.bb.com.br/")
st.header("DIOPE GEFID")
st.subheader("Plataforma de Serviços de Escrituração")

params = dict(type="primary", use_container_width=True)


def get_tables():
    pass


row, cont = st.columns([3.2, 0.8]), 0

with (row[0]):
    with st.container(border=True):
        st.write("###### Informe de Rendimentos de Ativos Escriturais (somente preencha um campo abaixo)")
        tx_nome = st.text_input(label="Nome do Investidor:", placeholder="Digite o nome do Investidor")
        tx_mci = st.text_input(label="MCI:", placeholder="Digite o número do Investidor")
        tx_cpf_cnpj = st.text_input(label="CPF / CNPJ:", placeholder="Digite o número do CPF / CNPJ")
        tx_email = st.text_input(label="E-mail:", placeholder="Digite o e-mail do Investidor")
        btn_search = st.button("Pesquisar", key="btn_search", type="primary")
        if btn_search:
            if tx_nome.strip() == "" and tx_mci.strip() == "" and tx_cpf_cnpj.strip() == "" and tx_email.strip() == "":
                st.toast("Precisa digitar qualquer campo para pesquisar...", icon="⚠️")

            elif tx_nome != "":
                tx_nome = unidecode(tx_nome).upper()

                stmt_envio = conn(f"""
                    SELECT DISTINCT
                        t1.CD_CLI_ACNT AS MCI_INVESTIDOR,
                        CASE WHEN t1.CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO ' ELSE 'NÃO ENVIADO' END AS STATUS,
                        t1.TS_INC_PRCT_EMAI AS LOG,
                        t1.TX_END_EMAI AS EMAIL
                    FROM
                        DB2I13E5.IR2024_ENVIO_EMAILS t1
                        LEFT JOIN DB2I13E5.IR2024_CADASTRO_BB t2
                            ON t2.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                        LEFT JOIN DB2I13E5.IR2024_CADASTRO_B3 t3
                            ON t3.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                    WHERE
                        t2.INVESTIDOR = {tx_nome!r} OR
                        t3.INVESTIDOR = {tx_nome!r}
                """)

                stmt_b3 = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_B3 WHERE INVESTIDOR = {tx_nome!r}")

                stmt_bb = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_BB WHERE INVESTIDOR = {tx_nome!r}")

                with st.container(border=True):
                    st.write("##### Resultado da Pesquisa")

                    st.write("###### Dados do envio:")
                    if len(stmt_envio) > 0:
                        st.dataframe(stmt_envio)
                    else:
                        st.write("Não localizamos email enviados.")

                    st.write("###### Dados do MCI:")
                    if len(stmt_bb) > 0:
                        st.dataframe(stmt_bb)
                    else:
                        st.write("Não localizamos dados no recorte da tabela MCI.")

                    st.write("###### Dados do B3:")
                    if len(stmt_b3) > 0:
                        st.dataframe(stmt_b3)
                    else:
                        st.write("Não localizamos dados na tabela de cadastro da B3.")

                    st.button("Voltar", key="btn_back", type="primary")

            elif tx_mci != "":
                tx_mci = re.sub("\D", "", tx_mci)

                stmt_envio = conn(f"""
                    SELECT DISTINCT
                        CD_CLI_ACNT AS MCI_INVESTIDOR,
                        CASE WHEN CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO ' ELSE 'NÃO ENVIADO' END AS STATUS,
                        TS_INC_PRCT_EMAI AS LOG,
                        TX_END_EMAI AS EMAIL
                    FROM
                        DB2I13E5.IR2024_ENVIO_EMAILS
                    WHERE
                        CD_CLI_ACNT = {tx_mci}
                """)

                stmt_b3 = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_B3 WHERE MCI_INVESTIDOR = {tx_mci}")

                stmt_bb = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_BB WHERE MCI_INVESTIDOR = {tx_mci}")

                with st.container(border=True):
                    st.write("##### Resultado da Pesquisa")

                    st.write("###### Dados do envio:")
                    if len(stmt_envio) > 0:
                        st.dataframe(stmt_envio)
                    else:
                        st.write("Não localizamos email enviados.")

                    st.write("###### Dados do MCI:")
                    if len(stmt_bb) > 0:
                        st.dataframe(stmt_bb)
                    else:
                        st.write("Não localizamos dados no recorte da tabela MCI.")

                    st.write("###### Dados do B3:")
                    if len(stmt_b3) > 0:
                        st.dataframe(stmt_b3)
                    else:
                        st.write("Não localizamos dados na tabela de cadastro da B3.")

                    st.button("Voltar", key="btn_back", type="primary")

            elif tx_cpf_cnpj != "":
                tx_cpf_cnpj = re.sub("\D", "", tx_cpf_cnpj)

                stmt_envio = conn(f"""
                    SELECT DISTINCT
                        t1.CD_CLI_ACNT AS MCI_INVESTIDOR,
                        CASE WHEN t1.CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO ' ELSE 'NÃO ENVIADO' END AS STATUS,
                        t1.TS_INC_PRCT_EMAI AS LOG,
                        t1.TX_END_EMAI AS EMAIL
                    FROM
                        DB2I13E5.IR2024_ENVIO_EMAILS t1
                        LEFT JOIN DB2I13E5.IR2024_CADASTRO_BB t2
                            ON t2.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                        LEFT JOIN DB2I13E5.IR2024_CADASTRO_B3 t3
                            ON t3.MCI_INVESTIDOR = t1.CD_CLI_ACNT
                    WHERE
                        t2.CPF_CNPJ = {tx_cpf_cnpj} OR
                        t3.CPF_CNPJ = {tx_cpf_cnpj}
                """)

                stmt_b3 = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_B3 WHERE CPF_CNPJ = {tx_cpf_cnpj}")

                stmt_bb = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_BB WHERE CPF_CNPJ = {tx_cpf_cnpj}")

                with st.container(border=True):
                    st.write("##### Resultado da Pesquisa")

                    st.write("###### Dados do envio:")
                    if len(stmt_envio) > 0:
                        st.dataframe(stmt_envio)
                    else:
                        st.write("Não localizamos email enviados.")

                    st.write("###### Dados do MCI:")
                    if len(stmt_bb) > 0:
                        st.dataframe(stmt_bb)
                    else:
                        st.write("Não localizamos dados no recorte da tabela MCI.")

                    st.write("###### Dados do B3:")
                    if len(stmt_b3) > 0:
                        st.dataframe(stmt_b3)
                    else:
                        st.write("Não localizamos dados na tabela de cadastro da B3.")

                    st.button("Voltar", key="btn_back", type="primary")

            elif tx_email != "":
                stmt_envio = conn(f"""
                    SELECT DISTINCT
                        CD_CLI_ACNT AS MCI_INVESTIDOR,
                        CASE WHEN CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO ' ELSE 'NÃO ENVIADO' END AS STATUS,
                        TS_INC_PRCT_EMAI AS LOG,
                        TX_END_EMAI AS EMAIL
                    FROM
                        DB2I13E5.IR2024_ENVIO_EMAILS
                    WHERE
                        TX_END_EMAI = {tx_email.lower()!r}
                """)

                stmt_b3 = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_B3 WHERE EMAIL = {tx_email.lower()!r}")

                stmt_bb = conn(f"SELECT * FROM DB2I13E5.IR2024_CADASTRO_BB WHERE EMAIL = {tx_email.lower()!r}")

                with st.container(border=True):
                    st.write("##### Resultado da Pesquisa")

                    st.write("###### Dados do envio:")
                    if len(stmt_envio) > 0:
                        st.dataframe(stmt_envio)
                    else:
                        st.write("Não localizamos email enviados.")

                    st.write("###### Dados do MCI:")
                    if len(stmt_bb) > 0:
                        st.dataframe(stmt_bb)
                    else:
                        st.write("Não localizamos dados no recorte da tabela MCI.")

                    st.write("###### Dados do B3:")
                    if len(stmt_b3) > 0:
                        st.dataframe(stmt_b3)
                    else:
                        st.write("Não localizamos dados na tabela de cadastro da B3.")

                    st.button("Voltar", key="btn_back", type="primary")

            else:
                st.write("nada")

with row[1]:
    with st.container(border=True):
        st.write("**Navegação**")
        st.link_button("**Intranet BB**", url="https://intranet.bb.com.br/", **params)
        st.link_button("**Portal Diope**", url="https://portal.diope.bb.com.br/", **params)
        st.link_button("**Portal GEFID**", url="https://gefid-aplic-1.intranet.bb.com.br/", **params)
        st.link_button("**Menu Escrituração**", url="http://localhost:8501", **params)
