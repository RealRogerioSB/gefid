import io

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/savings: Rendimentos Pendentes")


@st.cache_data(show_spinner="**:material/hourglass: Carregando a listagem de empresa, aguarde...**")
def load_active(active: str) -> dict[str, int]:
    load: pd.DataFrame = engine.query(
        sql=f"""
            SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
            FROM DB2AEB.PRM_EMP AS t1 INNER JOIN DB2MCI.CLIENTE AS t2 ON t2.COD = t1.CD_CLI_EMT
            WHERE t1.DT_ECR_CTR IS {active}
            ORDER BY STRIP(t2.NOM)
        """,
        show_spinner=False,
        ttl=0,
    )
    return {k: v for k, v in zip(load["nom"].to_list(), load["mci"].to_list())}


def load_report(_mci: int) -> pd.DataFrame:
    return engine.query(
        sql="""
            SELECT
                t1.CD_CLI_TITR AS MCI,
                STRIP(t2.NOM) AS INVESTIDOR,
                CASE
                    WHEN t2.COD_TIPO = 2 THEN LPAD(CAST(t2.COD_CPF_CGC AS BIGINT), 14, '0')
                    ELSE LPAD(CAST(t2.COD_CPF_CGC AS BIGINT), 11, '0')
                END AS CPF_CNPJ,
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
                t1.CD_EST_DRT IN (2, 22, 23)
            ORDER BY
                STRIP(t2.NOM),
                t1.DT_MVT_DRT
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci),
    )


def load_data(_mci: int) -> tuple[str, ...]:
    load: pd.DataFrame = engine.query(
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
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.CD_CLI_EMT = :mci
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci),
    )

    return str(load["mci"].iloc[0]), load["empresa"].iloc[0], load["cnpj"].iloc[0], load["sigla"].iloc[0]


st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"], key="option_active")

kv: dict[str, int] = load_active("null") if st.session_state["option_active"] == "ativos" else load_active("not null")

with st.columns(2)[0]:
    st.selectbox(
        label="**Clientes ativos:**" if st.session_state["option_active"] == "ativos" else "**Clientes inativos:**",
        options=kv.keys(),
        key="empresa"
    )

    mci: int = kv.get(st.session_state["empresa"])

    params: dict[str, bool | str] = dict(type="primary", use_container_width=True)

    st.markdown("")

    col = st.columns(3)
    col[0].button(label="**Visualizar na tela**", key="view", icon=":material/preview:", **params)
    col[1].button(label="**Baixar CSV**", key="csv", icon=":material/download:", **params)
    col[2].button(label="**Baixar Excel**", key="xlsx", icon=":material/download:", **params)

if st.session_state["view"]:
    with st.spinner("**:material/hourglass: Preparando os dados para exibir, aguarde...**", show_time=True):
        get_view: pd.DataFrame = load_report(mci)

        if not get_view.empty:
            mci_inv, nome_inv, cnpj_inv, _ = load_data(mci)

            st.write(f"**MCI:** {mci_inv}")
            st.write(f"**EMPRESA:** {nome_inv}")
            st.write(f"**CNPJ:** {cnpj_inv}")
            st.write(f"**TOTAL BRUTO:** R$ {float(get_view['valor'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.write(f"**TOTAL IR:** R$ {float(get_view['valor_ir'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))
            st.write(f"**TOTAL LÍQUIDO:** R$ {float(get_view['valor_liquido'].sum()):_.2f}"
                     .replace(".", ",").replace("_", "."))

            st.data_editor(
                data=get_view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "mci": st.column_config.NumberColumn("MCI"),
                    "investidor": st.column_config.TextColumn("Investidor"),
                    "cpf_cnpj": st.column_config.TextColumn("CPF / CNPJ"),
                    "tipo_pessoa": st.column_config.TextColumn("Tipo Pessoa"),
                    "DATA": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "direito": st.column_config.TextColumn("Direito"),
                    "sigla": st.column_config.TextColumn("Sigla"),
                    "valor": st.column_config.NumberColumn("Valor", format="dollar"),
                    "valor_ir": st.column_config.NumberColumn("Valor IR", format="dollar"),
                    "valor_liquido": st.column_config.NumberColumn("Valor Líquido", format="dollar"),
                },
            )

            st.button("**Voltar**", key="back_view", type="primary", icon=":material/reply:")

        else:
            st.toast(body="**Não há dados para exibir...**", icon=":material/error:")

if st.session_state["csv"]:
    with st.spinner("**:material/hourglass: Preparando os dados para baixar, aguarde...**", show_time=True):
        get_csv: pd.DataFrame = load_report(mci)

        if not get_csv.empty:
            sigla: str = load_data(mci)[3]

            st.download_button(
                label="**Baixar CSV**",
                data=get_csv.to_csv(index=False).encode("utf-8"),
                file_name=f"{sigla}-Rendimentos Pendentes.csv",
                mime="text/csv",
                key="download_csv",
                type="primary",
                icon=":material/download:",
            )

            st.toast(body="**Arquivo CSV pronto para baixar**", icon=":material/check_circle:")

        else:
            st.toast(body="**Não há dados para exibir...**", icon=":material/error:")

if st.session_state["xlsx"]:
    with st.spinner("**:material/hourglass: Preparando os dados para baixar...**", show_time=True):
        get_report: pd.DataFrame = load_report(mci)

        if not get_report.empty:
            sigla: str = load_data(mci)[3]

            path_xls: io.BytesIO = io.BytesIO()

            with pd.ExcelWriter(path_xls, engine="xlsxwriter") as writer:
                if len(get_report) <= int(1e6):
                    get_report[:int(1e6)].to_excel(writer, sheet_name="1", index=False)

                elif len(get_report) <= int(2e6):
                    get_report[:int(1e6)].to_excel(writer, sheet_name="1", index=False)
                    get_report[int(1e6):].to_excel(writer, sheet_name="2", index=False)

                elif len(get_report) <= int(3e6):
                    get_report[:int(1e6)].to_excel(writer, sheet_name="1", index=False)
                    get_report[int(1e6):int(2e6)].to_excel(writer, sheet_name="2", index=False)
                    get_report[int(2e6):].to_excel(writer, sheet_name="3", index=False)

                elif len(get_report) <= int(4e6):
                    get_report[:int(1e6)].to_excel(writer, sheet_name="1", index=False)
                    get_report[int(1e6):int(2e6)].to_excel(writer, sheet_name="2", index=False)
                    get_report[int(2e6):int(3e6)].to_excel(writer, sheet_name="3", index=False)
                    get_report[int(3e6):].to_excel(writer, sheet_name="4", index=False)

                else:
                    get_report[:int(1e6)].to_excel(writer, sheet_name="1", index=False)
                    get_report[int(1e6):int(2e6)].to_excel(writer, sheet_name="2", index=False)
                    get_report[int(2e6):int(3e6)].to_excel(writer, sheet_name="3", index=False)
                    get_report[int(3e6):int(4e6)].to_excel(writer, sheet_name="4", index=False)
                    get_report[int(4e6):].to_excel(writer, sheet_name="5", index=False)

            st.toast(body="**Arquivo XLSX pronto para baixar**", icon=":material/check_circle:")

            st.download_button(
                label="**Baixar XLSX**",
                data=path_xls.getvalue(),
                file_name=f"{sigla}-Rendimentos Pendentes.xlsx",
                mime="application/vnd.ms-excel",
                key="download_xlsx",
                type="primary",
                icon=":material/download:",
            )

        else:
            st.toast(body="**Não há dados para baixar...**", icon=":material/error:")
