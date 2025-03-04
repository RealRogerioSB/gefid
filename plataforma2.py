import math
import streamlit as st

st.set_page_config(
    page_title="Intranet DIOPE GEFID",
    page_icon="img/bb_ico.ico",
    layout="wide",
)

st.logo("img/bb_logo.jpg", size="large", link="https://gefid-aplic-1.intranet.bb.com.br/")

header = st.columns([1.3, 12], vertical_alignment="center")
header[0].image("img/bb.png", width=100)
header[1].header("DIOPE GEFID")
header[1].subheader("Plataforma de Serviços de Escrituração")

titles = ["Atendimento aos Clientes", "Atendimento aos Investidores", "Obrigações / Rotinas", "Declarações Diversas"]
cards = [
    ["Base de Investidores", "Rendimentos Distribuídos", "Rendimentos Pagos", "Rendimentos Pendentes",
     "DIPJ", "Cálculo de Rendimentos", "EDIV", "Autorregulação BB"],
    ["Informe de Rendimentos", "Extrato de Movimentação", "Extrato de Rendimentos", "Consulta Cautelas (ABB/BBA)"],
    ["Circular BACEN 3945", "Circular BACEN 3624", "Resolução CVM 160"],
    ["Ações em Tesouraria", "Cancelamento de CEPAC", "Maiores Investidores", "Maiores Investidores Percentual"]
]

params = dict(type="primary", use_container_width=True)

acumula = 0

for card in range(len(cards)):
    row, cont = st.columns([3.2, 0.8]), 0
    with row[0]:
        with st.container(border=True):
            st.write(f"**{titles[card]}**")
            for _ in range(math.ceil(len(cards[card]) / 4)):
                for col in st.columns(4):
                    if cont < len(cards[card]):
                        with col:
                            with st.container(height=140, border=True):
                                st.write(f"**{cards[card][cont]}**")
                                st.button("**Acessar**", key=f"btn_{acumula}", **params)
                                cont += 1
                                acumula += 1
                    else:
                        break

    with row[1]:
        if card < 1:
            with st.container(border=True):
                st.write("**Navegação**")
                st.link_button("**Intranet BB**", url="https://intranet.bb.com.br/", **params)
                st.link_button("**Portal Diope**", url="https://portal.diope.bb.com.br/", **params)
                st.link_button("**Portal GEFID**", url="https://gefid-aplic-1.intranet.bb.com.br/", **params)
                st.link_button("**Menu Escrituração**", url="http://localhost:8501", **params)
