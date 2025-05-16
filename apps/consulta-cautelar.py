import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

message = st.empty()


def load_acionista(key: str, value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"SELECT * FROM DB2I13E5.SISTEMA_ANTIGO_ACIONISTAS WHERE {key.upper()} = :value",
        show_spinner=False,
        ttl=0,
        params=dict(value=value)
    )


def load_certificado(value: tuple) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT DISTINCT INSCRICAO, NUMERO_CERT, NR_PRIM_ACAO, DATA_EMIS, QT_ACOES
            FROM DB2I13E5.SISTEMA_ANTIGO_CERTIFICADOS
            WHERE INSCRICAO IN {value}
        """,
        show_spinner=False,
        ttl=0,
    )


st.subheader(":material/autorenew: Consulta Cautelar (ABB/BBA)")

st.markdown("**Consulta aos Sistemas Antigos ABB e BBA**")

st.columns(5)[0].text_input("**Inscrição:**", key="inscrição", max_chars=10)
st.columns(2)[0].text_input("**Nome do Investidor:**", key="nome_on", max_chars=60)

col1, col2, _ = st.columns([1, 1.2, 4])
col1.text_input("**MCI:**", key="bdc", max_chars=10)
col2.text_input("**CPF/CNPJ:**", key="cpf_cnpj", max_chars=14)

st.button("**Pesquisar**", key="search", type="primary", icon=":material/search:")

if st.session_state["search"]:
    if all([st.session_state["inscrição"], st.session_state["nome_on"],
            st.session_state["bdc"], st.session_state["cpf_cnpj"]]):
        message.warning("**Só pode preencher um dos campos abaixo**", icon=":material/warning:", width=600)
        st.stop()

    if not any([st.session_state["inscrição"], st.session_state["nome_on"],
                st.session_state["bdc"], st.session_state["cpf_cnpj"]]):
        message.warning("**É necessário preencher um campo abaixo**", icon=":material/warning:", width=600)
        st.stop()

    if not st.session_state["inscrição"].isdigit() and st.session_state["inscrição"]:
        message.warning("**O campo 'Inscrição' tem de ser numérico**", icon=":material/warning:", width=600)
        st.stop()

    elif not st.session_state["bdc"].isdigit() and st.session_state["bdc"]:
        message.warning("**O campo 'MCI' tem de ser numérico**", icon=":material/warning:", width=600)
        st.stop()

    elif not st.session_state["cpf_cnpj"].isdigit() and st.session_state["cpf_cnpj"]:
        message.warning("**O campo 'CPF/CNPJ' tem de ser numérico**", icon=":material/warning:", width=600)
        st.stop()

    with st.spinner("**:material/hourglass: Preparando para exportar os dados, aguarde...**", show_time=True):
        acionistas: pd.DataFrame = load_acionista(
            key="inscricao" if st.session_state["inscrição"]
            else "nome_on" if st.session_state["nome_on"]
            else "bdc" if st.session_state["bdc"]
            else "cpf_cnpj",
            value=st.session_state["inscrição"] if st.session_state["inscrição"]
            else unidecode(st.session_state["nome_on"]).upper() if st.session_state["nome_on"]
            else st.session_state["bdc"] if st.session_state["bdc"]
            else st.session_state["cpf_cnpj"],
        )

        if acionistas.empty:
            message.info("**Não foram encontrados dados para a pesquisa...**", icon=":material/error:", width=600)
            st.stop()

        inscricoes: tuple = tuple(acionistas["inscricao"].astype("int64").drop_duplicates().to_list())

        certificados: pd.DataFrame = load_certificado(value=inscricoes)

        if not certificados.empty:
            message.warning("**Não foram encontrados dados para a pesquisa...**", icon=":material/error:", width=600)
            st.stop()

        st.divider()

        st.columns([3, 1])[0].data_editor(
            data=acionistas,
            hide_index=True,
            use_container_width=True,
            column_config={
                "cpf_cnpj": st.column_config.NumberColumn("CPF / CNPJ"),
                "data_de_nascimento": st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"),
                "bdc": st.column_config.NumberColumn("MCI"),
                "inscricao": st.column_config.NumberColumn("Inscrição"),
                "ag": st.column_config.NumberColumn("Agência"),
                "cta": st.column_config.NumberColumn("Contestação"),
                "dt_cadastr": st.column_config.DateColumn("Data de Cadastro", format="DD/MM/YYYY"),
                "cep": st.column_config.NumberColumn("CEP"),
                "nome_on": st.column_config.TextColumn("Nome ON", width="large"),
                "nome_pn": st.column_config.TextColumn("Nome PN", width="large"),
                "endereco": st.column_config.TextColumn("Endereço", width="large"),
                "cidade": st.column_config.TextColumn("Cidade"),
                "uf": st.column_config.TextColumn("Estado"),
            },
        )

        st.columns(2)[0].data_editor(
            data=certificados,
            hide_index=True,
            use_container_width=True,
            column_config={
                "inscricao": st.column_config.NumberColumn("INSCRIÇÃO"),
                "numero_cert": st.column_config.NumberColumn("NUMERO CERT"),
                "nr_prim_acao": st.column_config.NumberColumn("NR PRIM AÇÃO"),
                "data_emis": st.column_config.NumberColumn("DATA EMIS"),
                "qt_acoes": st.column_config.NumberColumn("QT AÇÕES"),
            },
        )

        st.download_button(
            label="**Baixar CSV**",
            data=certificados.to_csv(sep=";", index=False).encode("utf-8"),
            file_name=f"sistemas_antigos_{st.session_state['inscrição']}.csv",
            mime="text/csv",
            type="primary",
            icon=":material/download:",
        )

        certificados.to_csv(
            path_or_buf=f"static/escriturais/@deletar/sistemas_antigos_{st.session_state['inscrição']}.csv",
            sep=";",
            index=False,
        )

        message.info("**Gerada com sucesso a planilha para a pasta específica**",
                     icon=":material/check_circle:", width=600)
