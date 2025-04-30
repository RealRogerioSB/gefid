from datetime import date

import pandas as pd
import streamlit as st

data = pd.read_csv("static/arquivos/circular3945/cadastro.csv", delimiter=";")

if "editor" not in st.session_state:
    st.session_state["editor"] = data.copy()

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)

st.subheader(":material/cycle: Circular BACEN 3945")
st.columns([3, 1])[0].write("##### Envio de arquivo à **BB Asset** com a informação do fechamento mensal das carteiras"
                            " dos fundos escriturados pelo BB, para atender a Carta Circular 3945 do Banco Central.")

with st.columns(4)[0]:
    code_user = st.text_input(label="**Código do Usuário:**")
    pass_user = st.text_input(label="**Senha - Mesop.:**", type="password")

col = st.columns([1.5, 0.5, 1, 1])

with col[0]:
    mes = st.slider(label="**Mês:**", min_value=1, max_value=12,
                    value=date.today().month - 1 if 1 <= date.today().month - 1 else 12, )

with col[1]:
    ano = st.selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1),
                       index=0 if 1 <= date.today().month - 1 else 1)

st.divider()

st.markdown("**Fundos enviados no último arquivo**")

with st.spinner(text=":material/hourglass: Obtendo os dados, aguarde...", show_time=True):
    st.session_state["editor"] = st.data_editor(
        data=st.session_state["editor"], num_rows="dynamic", row_height=25,
        column_config={
            "codigo": st.column_config.TextColumn(label="Código", required=True, max_chars=4,
                                                  validate="^[A-Z0-9]+$"),
            "mci": st.column_config.NumberColumn(label="MCI", required=True),
            "cnpj": st.column_config.NumberColumn(label="CNPJ", required=True),
            "nome": st.column_config.TextColumn(label="Nome", required=True),
            "qtdcotas": st.column_config.NumberColumn(label="Qtd Cotas", required=True),
            "tipocota": st.column_config.SelectboxColumn(label="Cota", required=True,
                                                         options=["Única", "Consolidada", "Sênior",
                                                                  "Júnior", "Mezanino"]),
            "tipotitulo": st.column_config.TextColumn(label="Título", required=True),
            "sistema": st.column_config.SelectboxColumn(label="Sistema", required=True,
                                                        options=["Drive", "YMF", "Itau"]),
            "carteira": st.column_config.NumberColumn(label="Carteira", required=True),
        },
    )

if st.button(label="**Enviar**", type="primary"):
    # st.session_state["editor"].to_csv("static/arquivos/circular3945/cadastro2.csv", index=False)
    st.toast("**A planilha foi enviada**", icon=":material/task_alt:")

if st.button("**Atualizou?**", type="primary"):
    if not st.session_state["editor"].equals(data):
        st.toast("**A planilha foi atualizada**", icon=":material/edit_square:")
    else:
        st.toast("**A planilha ainda não foi atualizada**", icon=":material/edit_square:")

if st.button(label="**Reverter**", type="primary"):
    st.session_state["editor"] = data.copy()
    st.toast("**A planilha foi restaurada**", icon=":material/check_circle:")
    st.rerun()
