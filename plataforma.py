import streamlit as st

st.set_page_config(
    page_title="Intranet DIOPE GEFID",
    page_icon="img/bbfav.svg",
    layout="wide",
)

st.logo(image="img/bb_png.png", size="large", link="https://gefid-aplic-1.intranet.bb.com.br/")

pages: dict[str, list[st.Page]] = {
    "Atendimento aos Clientes": [
        st.Page("bases/page1.py", title="Base de Investidores", icon=":material/bug_report:"),
        st.Page("bases/page2.py", title="Rendimentos Distribuídos", icon=":material/bug_report:"),
        st.Page("bases/page3.py", title="Rendimentos Pagos", icon=":material/bug_report:"),
        st.Page("bases/page4.py", title="Rendimentos Pendentes", icon=":material/bug_report:"),
        st.Page("bases/page5.py", title="DIPJ", icon=":material/bug_report:"),
        st.Page("bases/page6.py", title="Cálculo de Rendimentos", icon=":material/bug_report:"),
        st.Page("bases/page7.py", title="EDIV", icon=":material/bug_report:"),
        st.Page("bases/page8.py", title="Autorregulação BB", icon=":material/bug_report:"),
    ],
    "Atendimento aos Investidores": [
        st.Page("bases/informeir.py", title="Informe de Rendimentos", icon=":material/bug_report:", default=True),
        st.Page("bases/page10.py", title="Extrato de Movimentação", icon=":material/bug_report:"),
        st.Page("bases/page11.py", title="Extrato de Rendimentos", icon=":material/bug_report:"),
        st.Page("bases/page12.py", title="Consulta Cautelas (ABB/BBA)", icon=":material/bug_report:"),
    ],
    "Obrigações / Rotinas": [
        st.Page("bases/page13.py", title="Circular BACEN 3945", icon=":material/bug_report:"),
        st.Page("bases/page14.py", title="Circular BACEN 3624", icon=":material/bug_report:"),
        st.Page("bases/page15.py", title="Resolução CVM 160", icon=":material/bug_report:"),
    ],
    "Declarações Diversas": [
        st.Page("bases/page16.py", title="Ações em Tesouraria", icon=":material/bug_report:"),
        st.Page("bases/page17.py", title="Cancelamento de CEPAC", icon=":material/bug_report:"),
        st.Page("bases/page18.py", title="Maiores Investidores", icon=":material/bug_report:"),
        st.Page("bases/page19.py", title="Maiores Investidores Percentual", icon=":material/bug_report:"),
    ]
}

pg = st.navigation(pages, expanded=True)

pg.run()
