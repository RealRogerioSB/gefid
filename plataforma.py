import streamlit as st

st.markdown(
    body="""<style>
        [data-testid='stHeader'] {display: none;}
        #MainMenu {visibility: hidden} footer {visibility: hidden}
    </style>""",
    unsafe_allow_html=True
)

st.set_page_config(
    page_title="Intranet DIOPE GEFID",
    page_icon="img/bbfav.svg",
    layout="wide",
)

st.logo(image="img/bb_png.png", size="large", link="https://gefid-aplic-1.intranet.bb.com.br/")

st.markdown(
    body="""<style>
        [data-testid='stHeader'] {display: none;}
        #MainMenu {visibility: hidden} footer {visibility: hidden}
    </style>""",
    unsafe_allow_html=True
)

st.navigation(
    pages={
        "Home": [
            st.Page(page="apps/home.py", title="BB Escrituração", icon=":material/home:", default=True),
        ],
        "Atendimento aos Clientes": [
            st.Page(page="apps/base-investidores.py", title="Base de Investidores", icon=":material/account_balance:"),
            st.Page(page="apps/rendimentos-distribuidos.py", title="Rendimentos Distribuídos",
                    icon=":material/send_money:"),
            st.Page(page="apps/rendimentos-pagos.py", title="Rendimentos Pagos", icon=":material/paid:"),
            st.Page(page="apps/rendimentos-pendentes.py", title="Rendimentos Pendentes", icon=":material/savings:"),
            st.Page(page="apps/dipj.py", title="DIPJ", icon=":material/dynamic_form:"),
            st.Page(page="apps/calculo-rendimentos.py", title="Cálculo de Rendimentos", icon=":material/calculate:"),
            st.Page(page="apps/ediv.py", title="EDIV", icon=":material/diversity_3:"),
            st.Page(page="apps/autorregulacao-bb.py", title="Autorregulação BB",
                    icon=":material/published_with_changes:"),
        ],
        "Atendimento aos Investidores": [
            st.Page(page="apps/informe-rendimentos.py", title="Informe de Rendimentos", icon=":material/ad:"),
            st.Page(page="apps/extrato-movimentacao.py", title="Extrato de Movimentação", icon=":material/wysiwyg:"),
            st.Page(page="apps/extrato-rendimentos.py", title="Extrato de Rendimentos", icon=":material/local_atm:"),
            st.Page(page="apps/consulta-cautelar.py", title="Consulta Cautelas (ABB/BBA)", icon=":material/autorenew:"),
        ],
        "Obrigações / Rotinas": [
            st.Page(page="apps/circular-3945.py", title="Circular BACEN 3945", icon=":material/cycle:"),
            st.Page(page="apps/circular-3624.py", title="Circular BACEN 3624", icon=":material/cycle:"),
            st.Page(page="apps/cvm-160.py", title="Resolução CVM 160", icon=":material/siren:"),
        ],
        "Declarações Diversas": [
            st.Page(page="apps/acoes-tesouraria.py", title="Ações em Tesouraria", icon=":material/bar_chart_4_bars:"),
            st.Page(page="apps/cancela-cepac.py", title="Cancelamento de CEPAC", icon=":material/hide_source:"),
            st.Page(page="apps/maiores-investidores.py", title="Maiores Investidores", icon=":material/editor_choice:"),
            st.Page(page="apps/maiores-investidores-percentual.py", title="Maiores Investidores Percentual",
                    icon=":material/workspace_premium:"),
        ]
    },
    expanded=True
).run()
