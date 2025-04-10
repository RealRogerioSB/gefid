import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection
from unidecode import unidecode

engine = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/wysiwyg: Extrato de Movimentação")

st.markdown("##### Extrato de Movimentação de Ativos dos últimos 12 meses")


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_client() -> dict[int, str]:
    load = engine.query(
        sql=f"""
            SELECT
                t1.CD_CLI_EMT AS mci,
                t2.NOM AS nom
            FROM
                DB2AEB.PRM_EMP AS t1
                INNER JOIN DB2MCI.CLIENTE AS t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.DT_ECR_CTR IS NOT NULL
            ORDER BY
                t2.NOM
        """,
        show_spinner=False,
        ttl=60,
    )
    return {k: v for k, v in zip(load["mci"].to_list(), load["nom"].to_list())}


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_extrato(field: str, _mci: int, _cpf_cnpj: int) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT
                t1.CD_TIP_TIT AS tipo,
                CAST(t1.DT_MVTC AS DATE) AS data,
                CAST(t1.QT_TIT_MVTD AS INT) AS movimento,
                CAST(t1.QT_TIT_ATU AS INT) AS saldo,
                t1.CD_CLI_CSTD AS mci_custodiante
            FROM
                DB2AEB.MVTC_DIAR_PSC t1
                INNER JOIN DB2MCI.CLIENTE t2
                ON t2.COD = t1.CD_CLI_ACNT
            WHERE
                t1.CD_CLI_EMT = :mci AND
                t2.{field.upper()} = :cpf_cnpj
            ORDER BY
                t1.DT_MVTC
        """,
        show_spinner=False,
        ttl=60,
        params=dict(mci=_mci, cpf_cnpj=_cpf_cnpj)
    )


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_empresa(field: str, _value: int | str) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT
                t1.COD AS mci_empresa,
                t1.NOM AS nm_empresa,
                t1.COD_CPF_CGC AS cnpj_empresa
            FROM
                DB2MCI.CLIENTE t1
            WHERE
                t1.{field.upper()} = :value
        """,
        show_spinner=False,
        ttl=60,
        params=dict(value=_value)
    )


@st.cache_data(show_spinner="Obtendo os dados, aguarde...")
def load_tipo(_tipo: int) -> pd.DataFrame:
    return engine.query(
        sql="SELECT t1.SG_TIP_TIT FROM DB2AEB.TIP_TIT t1 WHERE t1.CD_TIP_TIT = :tipo",
        show_spinner=False,
        ttl=60,
        params=dict(tipo=_tipo)
    )


kv = load_client()

col1, _ = st.columns(2)

with col1:
    empresa = st.selectbox(label="**Empresa:**", options=sorted(kv.values()))
    nome_investidor = st.text_input(label="**Nome Investidor:**", max_chars=100)

    col2, _ = st.columns(2)

    mci_investidor = col2.text_input(label="**MCI:**", max_chars=10)
    cpf_cnpj_investidor = col2.text_input(label="**CPF/CNPJ:**", max_chars=14)
    custodiante = col2.selectbox(label="**Custodiante:**", options=["Ambas", "Banco do Brasil", "B3"])

if st.button("**Pesquisar**", icon=":material/search:", type="primary"):
    mci = next((chave for chave, valor in kv.items() if valor == empresa), 0)

    match custodiante:
        case "Ambas": idx_custodia = 0
        case "Banco do Brasil": idx_custodia = 903485186
        case "B3": idx_custodia = 205007939

    if not any([nome_investidor, mci_investidor, cpf_cnpj_investidor]):
        st.toast("**Deve preencher só ao menos um dos campos abaixo**", icon=":material/warning:")
        st.stop()

    if nome_investidor:
        df_investidor = load_empresa("cod", mci)
        mci_empresa = df_investidor["mci_empresa"][0]
        nm_empresa = df_investidor["nm_empresa"][0]
        cnpj_empresa = df_investidor["cnpj_empresa"][0].astype(str).str.zfill(14)

        nome_investidor = unidecode(nome_investidor).upper()
        df = load_extrato("cd_cli_acnt", mci, mci_investidor)
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d.%m.%Y")

    col1, col2, col3 = st.columns(3, border=True)
    with col1:
        st.text_input(label="**Nome da Empresa:**", value=nm_empresa)
        st.text_input(label="**MCI da Empresa:**", value=mci_empresa)
        st.text_input(label="**CNPJ da Empresa:**", value=cnpj_empresa)

    with col2:
        st.text_input(label="**Nome do Investidor:**", value="nm_investidor")
        st.text_input(label="**MCI do Investidor:**", value="mci_investidor")
        st.text_input(label="**CPF/CNPJ do Investidor:**", value="cpf_cnpj_investidor")

    st.button("**Voltar**", type="primary")

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)
