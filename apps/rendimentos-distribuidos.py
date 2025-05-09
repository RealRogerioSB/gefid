import io
import zipfile
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection

st.cache_data.clear()

engine = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/send_money: Rendimentos Distribuídos")


@st.cache_data(show_spinner=False)
def load_active(active: str) -> dict[int, str]:
    df = engine.query(
        sql=f"""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                STRIP(t2.NOM) AS NOM
            FROM
                DB2AEB.PRM_EMP AS t1
                INNER JOIN DB2MCI.CLIENTE AS t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.DT_ECR_CTR IS {active.upper()}
            ORDER BY
                STRIP(t2.NOM)
        """,
        show_spinner="**:material/hourglass: Preparando a lista de empresa, aguarde...**",
        ttl=0,
    )
    return {k: v for k, v in zip(df["mci"].to_list(), df["nom"].to_list())}


@st.cache_data(show_spinner=False)
def load_report(_mci: int, _ano: int, _mes: int) -> pd.DataFrame:
    return engine.query(
        sql="""
            SELECT
                t1.CD_CLI_TITR as MCI,
                STRIP(t2.NOM) AS INVESTIDOR,
                CAST(t2.COD_CPF_CGC AS BIGINT) AS CPF_CNPJ,
                CASE WHEN t2.COD_TIPO = 1 THEN 'PF' ELSE 'PJ' END AS TIPO_PESSOA,
                t1.DT_MVT_DRT AS DATA,
                t4.NM_TIP_DRT AS DIREITO,
                CONCAT(STRIP(t3.SG_TIP_TIT), STRIP(t3.CD_CLS_TIP_TIT)) AS SIGLA,
                t1.VL_MVT_REN AS VALOR,
                t1.VL_IR_CLCD_MVT_REN AS VALOR_IR,
                t1.VL_MVT_REN - t1.VL_IR_CLCD_MVT_REN AS VALOR_LIQUIDO
            FROM
                DB2AEB.MVT_REN t1
                FULL JOIN DB2MCI.CLIENTE t2
                    ON t2.COD = t1.CD_CLI_TITR
                INNER JOIN DB2AEB.TIP_TIT t3
                    ON t3.CD_TIP_TIT = t1.CD_TIP_TIT
                INNER JOIN DB2AEB.TIP_DRT t4
                    ON t4.CD_TIP_DRT = t1.CD_TIP_DRT
            WHERE
                t1.CD_CLI_DLBC = :mci AND
                t1.CD_EST_DRT IN (1) AND
                YEAR(t1.DT_MVT_DRT) = :ano AND
                MONTH(t1.DT_MVT_DRT) = :mes
            ORDER BY
                STRIP(t2.NOM),
                t1.DT_MVT_DRT
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, ano=_ano, mes=_mes),
    )


@st.cache_data(show_spinner=False)
def load_data(_mci: int) -> pd.DataFrame:
    return engine.query(
        sql="""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                STRIP(t1.SG_EMP) AS SIGLA,
                STRIP(t2.NOM) AS EMPRESA,
                CASE
                    WHEN t2.COD_TIPO = 2 THEN LPAD(t2.COD_CPF_CGC, 14, '0')
                    ELSE LPAD(t2.COD_CPF_CGC, 11, '0')
                END AS CNPJ
            FROM
                DB2AEB.PRM_EMP t1
                INNER JOIN DB2MCI.CLIENTE t2
                    ON t1.CD_CLI_EMT = t2.COD
            WHERE
                t1.CD_CLI_EMT = :mci
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci),
    )


st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"], key="option_active")

kv = load_active("null") if st.session_state["option_active"] == "ativos" else load_active("not null")

with st.columns(2)[0]:
    st.selectbox(
        label="**Clientes ativos:**" if st.session_state["option_active"] == "ativos" else "**Clientes inativos:**",
        options=sorted(kv.values()),
        key="empresa",
    )

    mci = next((chave for chave, valor in kv.items() if valor == st.session_state["empresa"]), 0)

    col = st.columns([2, 1, 1])
    col[0].slider(label="**Mês:**", min_value=1, max_value=12, value=date.today().month, key="mês")
    col[1].selectbox(label="**Ano:**", options=range(date.today().year, 1995, -1), key="ano")

    params = dict(type="primary", use_container_width=True)

    st.divider()

    col = st.columns(3)

    col[0].button(label="**Visualizar na tela**", key="view", icon=":material/preview:", **params)
    col[1].button(label="**Baixar CSV**", key="csv", icon=":material/download:", **params)
    col[2].button(label="**Baixar Excel**", key="xlsx", icon=":material/download:", **params)

if st.session_state["view"]:
    with st.spinner("**:material/hourglass: Preparando os dados para exibir, aguarde...**", show_time=True):
        get_view = load_report(mci, st.session_state["ano"], st.session_state["mês"])

        if not get_view.empty:
            get_data = load_data(mci)

            st.write(f"**MCI:** {get_data['mci'].iloc[0]}")
            st.write(f"**EMPRESA:** {get_data['empresa'].iloc[0]}")
            st.write(f"**CNPJ:** {get_data['cnpj'].iloc[0]}")
            st.write(f"**MÊS/ANO:** {st.session_state['mês']:02d}/{st.session_state['ano']}")
            st.write(f"**TOTAL BRUTO:** R$ {float(get_view['valor'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.write(f"**TOTAL IR:** R$ {float(get_view['valor_ir'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.write(f"**TOTAL LÍQUIDO:** R$ {float(get_view['valor_liquido'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))

            st.data_editor(get_view, hide_index=True)

            st.button("**Voltar**", key="back_view", icon=":material/reply:")

        else:
            st.toast(body="**Não há dados para exibir...**", icon=":material/error:")

if st.session_state["csv"]:
    with st.spinner("**:material/hourglass: Preparando os dados para baixar, aguarde...**", show_time=True):
        get_csv = load_report(mci, st.session_state["ano"], st.session_state["mês"])

        if not get_csv.empty:
            sigla = load_data(mci)["sigla"].iloc[0]

            st.download_button(
                label="**Baixar CSV**",
                data=get_csv.to_csv(index=False).encode("utf-8"),
                file_name=f"{sigla}-{st.session_state['mês']}-{st.session_state['ano']}-"
                          f"Rendimentos Distribuídos.csv",
                mime="text/csv",
                key="download_csv",
                type="primary",
                icon=":material/download:",
            )

        else:
            st.toast(body="**Não há dados para baixar...**", icon=":material/error:")

if st.session_state["xlsx"]:
    with st.spinner("**:material/hourglass: Preparando os dados para baixar...**", show_time=True):
        get_xlsx = load_report(mci, st.session_state["ano"], st.session_state["mês"])

        if not get_xlsx.empty:
            sigla = load_data(mci)["sigla"].iloc[0]

            if len(get_xlsx) <= int(1e6):
                path_xlsx: io.BytesIO = io.BytesIO()

                st.toast(body="**Arquivo CSV pronto para baixar**", icon=":material/check_circle:")

                st.download_button(
                    label="Baixar XLSX",
                    data=get_xlsx.to_excel(path_xlsx, index=False, engine="xlsxwriter"),
                    file_name=f"{sigla}-{st.session_state['mês']}-{st.session_state['ano']}-"
                              f"Rendimentos Distribuídos.xlsx",
                    mime="application/vnd.ms-excel",
                    key="download_csv",
                    type="primary",
                    icon=":material/download:",
                )

            else:
                path_xlsx_1: io.BytesIO = io.BytesIO()
                path_xlsx_2: io.BytesIO = io.BytesIO()
                path_xlsx_3: io.BytesIO = io.BytesIO()

                xlsx_files: dict[io.BytesIO, str] = {
                    path_xlsx_1: get_xlsx[:int(1e6)].to_excel(
                        excel_writer=f"{sigla}-{st.session_state['mês']}-{st.session_state['ano']}-"
                                     f"Rendimentos Distribuídos-parte1.xlsx",
                        index=False,
                        engine="xlsxwriter"
                    ),
                    path_xlsx_2: get_xlsx[int(1e6):int(2e6)].to_excel(
                        excel_writer=f"{sigla}-{st.session_state['mês']}-{st.session_state['ano']}-"
                                     f"Rendimentos Distribuídos-parte2.xlsx",
                        index=False,
                        engine="xlsxwriter"
                    ),
                    path_xlsx_3: get_xlsx[int(2e6):].to_excel(
                        excel_writer=f"{sigla}-{st.session_state['mês']}-{st.session_state['ano']}-"
                                     f"Rendimentos Distribuídos-parte3.xlsx",
                        index=False,
                        engine="xlsxwriter"
                    ),
                }

                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(file=zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, xlsx_data in xlsx_files.items():
                        zip_file.writestr(filename, xlsx_data)

                zip_buffer.seek(0)

                st.toast(body="**Arquivo ZIP pronto para baixar**", icon=":material/check_circle:")

                st.download_button(
                    label="**Baixar ZIP**",
                    data=zip_buffer,
                    file_name="arquivos_xlsx.zip",
                    mime="application/zip",
                    key="download_xlsx",
                    type="primary",
                    icon=":material/download:",
                )

        else:
            st.toast(body="**Não há dados para baixar...**", icon=":material/error:")
