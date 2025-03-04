import streamlit as st

st.set_page_config(
    page_title="Intranet DIOPE GEFID",
    page_icon="img/bb_ico.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.logo("img/bb_logo.jpg", size="large", link="https://gefid-aplic-1.intranet.bb.com.br/")

cards = [
    "Aplicações e Resgates", "BB Escrituração", "Captura CRA - Valores",
    "Conciliador - Conta Corrente\nControladoria de Fundos", "Conciliador Internacional (2024)",
    "Conversor EGT", "Grandes Números - Precificação", "Módulo CBIO", "Módulo CBIO - Custódia",
    "Módulo CBIO - Negociação", "Módulo de Carteiras", "Módulo de Clientes",
    "Módulo de Cobrança de Tarifas GEFID", "Módulo de Conciliação CETIP-B3 x Drive",
    "Módulo de Conciliação de Conta\nCaixa de Fundos", "Módulo de Conciliação Drive x GFI",
    "Módulo de Conciliação em Moeda Estrangeira", "Módulo de Conciliação GFI x CETIP",
    "Módulo de Conciliação Internacional", "Módulo de Conciliação IPN",
    "Módulo de Conciliação Selic x SAC", "Módulo de Demonstrações Contábeis de Fundos",
    "Módulo de Dias Utéis", "Módulo de Integração de Tarifas", "Módulo de Lançamentos a Estornar - Contabilidade",
    "Módulo de Lançamentos EGT", "Módulo de Precificação", "Módulo de Precificação de CRIs",
    "Módulo de Usuários", "Módulo DEB-EGT Selic", "Módulo Fundos - Brasilprev",
    "Módulo Gerador de Relatório Rendimento Cotista", "Módulo Importador de Fundos",
    "Módulo Impressão GFI", "Módulo Inventário", "Módulo Liquidação Financeira EGT BI-B3",
    "Módulo Papel Zero", "Módulo Papel Zero - Boletas CETIP", "Módulo Papel Zero - Boletas Selic",
    "Papel Zero - Liquidação BBDTVM", "Partidas", "Taxa de Administração"
]

cont, params = 0, dict(type="primary", use_container_width=True)

with st.sidebar:
    with st.container(border=True):
        st.write("**Navegação**")
        st.link_button("**Intranet BB**", url="https://intranet.bb.com.br/", **params)
        st.link_button("**Demandas Externas**", url="https://www.bb.com.br/", **params)

    with st.expander("**Escolha o aplicativo abaixo:**"):
        for _ in range(len(cards)):
            if cont < len(cards):
                with st.container(border=True):
                    st.button(f"**{cards[cont]}**", key=f"btn_{cont:02d}", **params)
                    cont += 1
            else:
                break

st.header("DIOPE GEFID")
st.subheader("Diretoria Operações - Gerência de Serviços Fiduciários")

st.json(st.session_state)
