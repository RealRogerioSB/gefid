import streamlit as st

col1, _, col2 = st.columns([2.2, 1, 0.8])

col1.subheader(":material/home: Plataforma de Serviços de Escrituração")

col1.write("##### :material/right_panel_open: Basta escolher as opções ao seu lado")


with col2.container(border=True):
    st.markdown("**Navegação**")

    st.link_button("**Intranet BB**", url="https://intranet.bb.com.br",
                   type="primary", icon=":material/link:", use_container_width=True)

    st.link_button("**Portal DIOPE**", url="https://portal.diope.bb.com.br",
                   type="primary", icon=":material/link:", use_container_width=True)

    st.link_button("**Portal GEFID**", url="https://gefid-aplic-1.intranet.bb.com.br",
                   type="primary", icon=":material/link:", use_container_width=True)
