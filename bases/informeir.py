import re
import streamlit as st
from unidecode import unidecode
from conn import conn

st.logo("img/bb_png.png", size="large", link="https://gefid-aplic-1.intranet.bb.com.br/")

st.header("DIOPE GEFID")
st.subheader("Plataforma de Serviços de Escrituração")

params = dict(type="primary", use_container_width=True)


@st.cache_data(show_spinner=False)
def get_join_email(field, value):
    stmt = f"""
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
            t2.{field.upper()} = {value if value.isdigit() else repr(value)} OR
            t3.{field.upper()} = {value if value.isdigit() else repr(value)}
    """
    return conn(stmt)


@st.cache_data(show_spinner=False)
def get_email(field, value):
    stmt = f"""
        SELECT DISTINCT
            CD_CLI_ACNT AS MCI_INVESTIDOR,
            CASE WHEN CD_EST_PRCT = 13 THEN 'EMAIL ENVIADO' ELSE 'NÃO ENVIADO' END AS STATUS,
            TS_INC_PRCT_EMAI AS LOG,
            TX_END_EMAI AS EMAIL
        FROM
            DB2I13E5.IR2025_ENVIO_EMAILS
        WHERE
            {field.upper()} = {value if value.isdigit() else repr(value)}
    """
    return conn(stmt)


@st.cache_data(show_spinner=False)
def get_bb(field, value):
    return conn(f"SELECT * FROM DB2I13E5.IR2025_CADASTRO_BB "
                f"WHERE {field.upper()} = {value if value.isdigit() else repr(value)}")


@st.cache_data(show_spinner=False)
def get_b3(field, value):
    return conn(f"SELECT * FROM DB2I13E5.IR2025_CADASTRO_B3 "
                f"WHERE {field.upper()} = {value if value.isdigit() else repr(value)}")


row, cont = st.columns([3.2, 0.8]), 0

with row[0]:
    with st.container(border=True):
        st.markdown("###### Informe de Rendimentos de Ativos Escriturais (somente preencha um campo abaixo)")

        tx_nome = st.text_input(label="Nome do Investidor:", placeholder="Digite o nome do Investidor")
        tx_mci = st.text_input(label="MCI:", placeholder="Digite o número do Investidor")
        tx_cpf_cnpj = st.text_input(label="CPF / CNPJ:", placeholder="Digite o número do CPF / CNPJ")
        tx_email = st.text_input(label="E-mail:", placeholder="Digite o e-mail do Investidor")

        if st.button("Pesquisar", key="btn_search", type="primary"):
            with st.spinner("Obtendo os dados, aguarde..."):
                if (tx_nome.strip() == "" and tx_mci.strip() == "" and tx_cpf_cnpj.strip() == ""
                        and tx_email.strip() == ""):
                    st.toast("Precisa digitar qualquer um campo para pesquisar, pelo menos...", icon="⚠️")

                elif tx_nome != "":
                    envio_email = get_join_email("investidor", unidecode(tx_nome).upper())
                    envio_bb = get_bb("investidor", unidecode(tx_nome).upper())
                    envio_b3 = get_b3("investidor", unidecode(tx_nome).upper())

                    with st.container(border=True):
                        st.markdown("##### Resultado da Pesquisa")

                        st.markdown("###### Dados do envio:")
                        if len(envio_email) > 0:
                            st.dataframe(envio_email)
                        else:
                            st.write("Não localizamos email enviados.")

                        st.markdown("###### Dados do MCI:")
                        if len(envio_bb) > 0:
                            st.dataframe(envio_bb)
                        else:
                            st.write("Não localizamos dados no recorte da tabela MCI.")

                        st.markdown("###### Dados do B3:")
                        if len(envio_b3) > 0:
                            st.dataframe(envio_b3)
                        else:
                            st.write("Não localizamos dados na tabela de cadastro da B3.")

                        st.button("Voltar", key="btn_back", type="primary")

                elif tx_mci != "":
                    envio_email = get_email("cd_cli_acnt", re.sub(r"\D", "", tx_mci))
                    envio_bb = get_bb("mci_investidor", re.sub(r"\D", "", tx_mci))
                    envio_b3 = get_b3("mci_investidor", re.sub(r"\D", "", tx_mci))

                    with st.container(border=True):
                        st.markdown("##### Resultado da Pesquisa")

                        st.markdown("###### Dados do envio:")
                        if len(envio_email) > 0:
                            st.dataframe(envio_email)
                        else:
                            st.write("Não localizamos email enviados.")

                        st.markdown("###### Dados do MCI:")
                        if len(envio_bb) > 0:
                            st.dataframe(envio_bb)
                        else:
                            st.write("Não localizamos dados no recorte da tabela MCI.")

                        st.markdown("###### Dados do B3:")
                        if len(envio_b3) > 0:
                            st.dataframe(envio_b3)
                        else:
                            st.write("Não localizamos dados na tabela de cadastro da B3.")

                        st.button("Voltar", key="btn_back", type="primary")

                elif tx_cpf_cnpj != "":
                    envio_email = get_join_email("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj))
                    envio_bb = get_bb("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj))
                    envio_b3 = get_b3("cpf_cnpj", re.sub("\D", "", tx_cpf_cnpj))

                    with st.container(border=True):
                        st.markdown("##### Resultado da Pesquisa")

                        st.markdown("###### Dados do envio:")
                        if len(envio_email) > 0:
                            st.dataframe(envio_email)
                        else:
                            st.write("Não localizamos email enviados.")

                        st.markdown("###### Dados do MCI:")
                        if len(envio_bb) > 0:
                            st.dataframe(envio_bb)
                        else:
                            st.write("Não localizamos dados no recorte da tabela MCI.")

                        st.markdown("###### Dados do B3:")
                        if len(envio_b3) > 0:
                            st.dataframe(envio_b3)
                        else:
                            st.write("Não localizamos dados na tabela de cadastro da B3.")

                        st.button("Voltar", key="btn_back", type="primary")

                elif tx_email != "":
                    envio_email = get_email("tx_end_emai", tx_email.lower())
                    envio_bb = get_bb("email", tx_email.lower())
                    envio_b3 = get_b3("email", tx_email.lower())

                    with st.container(border=True):
                        st.markdown("##### Resultado da Pesquisa")

                        st.markdown("###### Dados do envio:")
                        if len(envio_email) > 0:
                            st.dataframe(envio_email)
                        else:
                            st.write("Não localizamos e-mail enviado.")

                        st.markdown("###### Dados do MCI:")
                        if len(envio_bb) > 0:
                            st.dataframe(envio_bb)
                        else:
                            st.write("Não localizamos dados no recorte da tabela MCI.")

                        st.markdown("###### Dados do B3:")
                        if len(envio_b3) > 0:
                            st.dataframe(envio_b3)
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
