import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

st.cache_data.clear()

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/autorenew: Consulta Cautelar (ABB/BBA)")

st.markdown("**Consulta aos Sistemas Antigos ABB e BBA**")


@st.cache_data(show_spinner=False)
def load_acionista(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"SELECT * FROM DB2I13E5.SISTEMA_ANTIGO_ACIONISTAS WHERE {key.upper()} = :value",
        show_spinner=False,
        ttl=0,
        params=dict(value=value)
    )


@st.cache_data(show_spinner=False)
def load_certificado(value: tuple) -> pd.DataFrame:
    return engine.query(
        sql=f"""SELECT DISTINCT INSCRICAO, NUMERO_CERT, NR_PRIM_ACAO, DATA_EMIS, QT_ACOES
                FROM DB2I13E5.SISTEMA_ANTIGO_CERTIFICADOS
                WHERE INSCRICAO IN {value}""",
        show_spinner=False,
        ttl=0,
    )


st.columns(5)[0].number_input("**Inscrição:**", key="inscricao", min_value=0, max_value=9999999999)
st.columns(2)[0].text_input("**Nome do Investidor:**", key="nome_investidor")

col1, col2, _ = st.columns([1, 1.2, 4])
col1.number_input("**MCI:**", key="mci_investidor", min_value=0, max_value=9999999999)
col2.number_input("**CPF/CNPJ:**", key="cpf_cnpj_investidor", min_value=0, max_value=99999999999999)

st.button("**Pesquisar**", key="search", type="primary", icon=":material/search:")

if st.session_state["search"]:
    if not any([st.session_state["inscricao"], st.session_state["nome_investidor"],
                st.session_state["mci_investidor"], st.session_state["cpf_cnpj_investidor"]]):

        st.toast("###### É necessário preencher um campo abaixo", icon=":material/warning:")
        st.stop()

    if all([st.session_state["inscricao"], st.session_state["nome_investidor"],
            st.session_state["mci_investidor"], st.session_state["cpf_cnpj_investidor"]]):

        st.toast("###### Só pode preencher um dos campos abaixo", icon=":material/warning:")
        st.stop()

    with st.spinner("**:material/hourglass: Preparando para exportar os dados, aguarde...**", show_time=True):
        acionistas: pd.DataFrame = load_acionista(
            key="inscricao" if st.session_state["inscricao"]
            else "nome_on" if st.session_state["nome_investidor"]
            else "bdc" if st.session_state["mci_investidor"]
            else "cpf_cnpj",
            value=st.session_state["inscricao"] if st.session_state["inscricao"]
            else unidecode(st.session_state["nome_investidor"]).upper() if st.session_state["nome_investidor"]
            else st.session_state["mci_investidor"] if st.session_state["mci_investidor"]
            else st.session_state["cpf_cnpj_investidor"],
        )

        if not acionistas.empty:
            inscricoes: tuple = tuple(acionistas["inscricao"].astype("int64").drop_duplicates().to_list())

            certificados: pd.DataFrame = load_certificado(value=inscricoes)

            if not certificados.empty:
                certificados.to_excel(
                    excel_writer=f"static/escriturais/@deletar/sistemas_antigos_{st.session_state['inscricao']}.xlsx",
                    index=False
                )
                st.toast("###### Gerada com sucesso a planilha para a pasta específica", icon=":material/check_circle:")

            else:
                st.toast("###### Não foram encontrados dados para a pesquisa realizada", icon=":material/error:")

        else:
            st.toast("###### Não foram encontrados dados para a pesquisa realizada", icon=":material/error:")
