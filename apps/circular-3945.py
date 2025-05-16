from datetime import date

import pandas as pd
import streamlit as st

data: pd.DataFrame = pd.read_csv("static/arquivos/circular3945/cadastro.csv", delimiter=";")

if "editor" not in st.session_state:
    st.session_state["editor"] = data

message = st.empty()

st.subheader(":material/cycle: Circular BACEN 3945")

st.columns([3, 1])[0].write("##### Envio de arquivo à **BB Asset** com a informação do fechamento mensal das carteiras"
                            " dos fundos escriturados pelo BB, para atender a Carta Circular 3945 do Banco Central.")

col1, col2, *_ = st.columns(4)
col1.text_input(label="**Código do Usuário:**", key="code_user")
col2.text_input(label="**Senha - Mesop.:**", key="pass_user", type="password")

col = st.columns([1.5, 0.5, 1, 1])

col[0].slider(label="**Mês:**", min_value=1, max_value=12, key="mês",
              value=date.today().month - 1 if 1 <= date.today().month - 1 else 12)

col[1].selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1), key="ano",
                 index=0 if 1 <= date.today().month - 1 else 1)

st.markdown("")
st.markdown("##### Fundos enviados no último arquivo")

with st.spinner(text="**:material/hourglass: Preparando os dados, aguarde...**", show_time=True):
    editor: pd.DataFrame = st.data_editor(
        data=st.session_state["editor"],
        height=388,
        column_config={
            "codigo": st.column_config.TextColumn(label="Código", required=True, max_chars=4, validate="^[A-Z0-9]+$"),
            "mci": st.column_config.NumberColumn(label="MCI", required=True),
            "cnpj": st.column_config.NumberColumn(label="CNPJ", required=True),
            "nome": st.column_config.TextColumn(label="Nome", width="large", required=True),
            "qtdcotas": st.column_config.NumberColumn(label="Qtd Cotas", required=True),
            "tipocota": st.column_config.SelectboxColumn(
                label="Cota",
                required=True,
                options=["Consolidada", "Júnior", "Mezanino", "Sênior", "Única"]
            ),
            "tipotitulo": st.column_config.TextColumn(label="Título", required=True),
            "sistema": st.column_config.SelectboxColumn(
                label="Sistema",
                required=True,
                default="Drive",
                options=["Drive", "Itau", "YMF"]
            ),
            "carteira": st.column_config.NumberColumn(label="Carteira", required=True),
        },
        num_rows="dynamic",
    )

col = st.columns(9)

col[0].button(label="**Salvar**", key="save", type="primary", icon=":material/save:", use_container_width=True)

col[1].button(label="**Reverter**", key="reply", type="primary", icon=":material/reply:", use_container_width=True)

if st.session_state["save"]:
    if not editor.equals(data):
        message.info("**A planilha foi atualizada**", icon=":material/check_circle:", width=600)
        st.session_state["editor"].to_csv("static/arquivos/circular3945/cadastro2.csv", index=False)
        st.rerun()

    else:
        message.info("**A planilha ainda não foi atualizada**", icon=":material/error:", width=600)

if st.session_state["reply"]:
    if not editor.equals(data):
        st.session_state["editor"] = data.copy()
        message.info("**A planilha foi restaurada**", icon=":material/check_circle:", width=600)
        st.rerun()

    else:
        message.info("**A planilha ainda não foi atualizada**", icon=":material/error:", width=600)
