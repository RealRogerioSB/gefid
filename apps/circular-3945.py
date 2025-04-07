from datetime import date

import pandas as pd
import streamlit as st

st.cache_data.clear()

st.subheader(":material/cycle: Circular BACEN 3945")
st.write("##### Envio de arquivo à **BB Asset** com a informação do fechamento mensal das carteiras dos fundos "
         "escriturados pelo BB, para atender a Carta Circular 3945 do Banco Central.")

with st.columns(4)[0]:
    code_user = st.text_input(label="**Código do Usuário:**")
    pass_user = st.text_input(label="**Senha - Mesop.:**", type="password")

col = st.columns([1.5, 0.5, 1, 1])

with col[0]:
    mes = st.slider(label="**Mês:**", min_value=1, max_value=12,
                    value=date.today().month - 1 if 1 <= date.today().month - 1 else 12,)

with col[1]:
    ano = st.selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1),
                       index=0 if 1 <= date.today().month - 1 else 1)

fundo1, fundo2 = st.tabs(["**Fundos enviados no último arquivo**", "**Fundos a serem adicionados**"])

with fundo1:
    with st.spinner("Obtendo os dados, aguarde..."):
        st.data_editor(data=pd.read_csv("static/arquivos/circular3945/cadastro.csv", delimiter=";"))

with fundo2:
    with st.spinner("Obtendo os dados, aguarde..."):
        df2 = st.empty()

st.columns(6)[0].button("**Enviar**", type="primary", use_container_width=True)
