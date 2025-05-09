from datetime import date

import pandas as pd
import streamlit as st

data = pd.read_csv("static/arquivos/circular3945/cadastro.csv", delimiter=";")

if "editor" not in st.session_state:
    st.session_state["editor"] = data

st.subheader(":material/cycle: Circular BACEN 3945")
st.columns([3, 1])[0].write("##### Envio de arquivo à **BB Asset** com a informação do fechamento mensal das carteiras"
                            " dos fundos escriturados pelo BB, para atender a Carta Circular 3945 do Banco Central.")

with st.columns(4)[0]:
    st.text_input(label="**Código do Usuário:**", key="code_user")
    st.text_input(label="**Senha - Mesop.:**", key="pass_user", type="password")

col = st.columns([1.5, 0.5, 1, 1])

with col[0]:
    st.slider(label="**Mês:**", min_value=1, max_value=12, key="mês",
              value=date.today().month - 1 if 1 <= date.today().month - 1 else 12)

with col[1]:
    st.selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1), key="ano",
                 index=0 if 1 <= date.today().month - 1 else 1)

st.divider()

st.markdown("**Fundos enviados no último arquivo**")

with st.spinner(text=":material/hourglass: Preparando os dados, aguarde...", show_time=True):
    editor = st.data_editor(
        data=st.session_state["editor"],
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
        num_rows="dynamic",
        row_height=25,
    )

st.button(label="**Salvar**", key="save", type="primary", icon=":material/save:")

st.button(label="**Reverter**", key="reply", type="primary", icon=":material/reply:")

if st.session_state["save"]:
    if not editor.equals(data):
        st.toast("**A planilha foi atualizada**", icon=":material/edit_square:")
        st.session_state["editor"].to_csv("static/arquivos/circular3945/cadastro2.csv", index=False)
        st.rerun()

    else:
        st.toast("**A planilha ainda não foi atualizada**", icon=":material/edit_square:")

if st.session_state["reply"]:
    st.session_state["editor"] = data.copy()
    st.toast("**A planilha foi restaurada**", icon=":material/check_circle:")
    st.rerun()
