import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from streamlit.connections import SQLConnection

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

st.subheader(":material/account_balance: Base de Investidores")


@st.cache_data(show_spinner="**:material/hourglass: Carregando a listagem da empresa, aguarde...**")
def load_active(active: str) -> dict[str, int]:
    load = engine.query(
        sql=f"""
            SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
            FROM DB2AEB.PRM_EMP AS t1 INNER JOIN DB2MCI.CLIENTE AS t2 ON t2.COD = t1.CD_CLI_EMT
            WHERE t1.DT_ECR_CTR IS {active.upper()}
            ORDER BY STRIP(t2.NOM)
        """,
        show_spinner=False,
        ttl=0,
    )
    return {k: v for k, v in zip(load["nom"].to_list(), load["mci"].to_list())}


def load_report(_mci: int, _data_ant: date, _data: date):
    load: pd.DataFrame = engine.query(
        sql="""
            SELECT
                t5.CD_CLI_ACNT AS MCI,
                STRIP(CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 THEN t6.NOM
                    ELSE t8.NM_INVR
                END) AS INVESTIDOR,
                CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 THEN
                        CASE
                            WHEN t6.COD_TIPO = 2 THEN LPAD(CAST(t6.COD_CPF_CGC AS BIGINT), 14, '0')
                            ELSE LPAD(CAST(t6.COD_CPF_CGC AS BIGINT), 11, '0')
                        END
                    ELSE
                        CASE
                            WHEN t6.COD_TIPO = 2 THEN LPAD(CAST(t8.NR_CPF_CNPJ_INVR AS BIGINT), 14, '0')
                            ELSE LPAD(CAST(t8.NR_CPF_CNPJ_INVR AS BIGINT), 14, '0')
                        END
                END AS CPF_CNPJ,
                CASE
                    WHEN t5.CD_CLI_ACNT < 1000000000 AND t6.COD_TIPO = 1 THEN 'PF'
                    WHEN t5.CD_CLI_ACNT < 1000000000 AND t6.COD_TIPO = 2 THEN 'PJ'
                    WHEN  t5.CD_CLI_ACNT >= 999999999 AND t8.CD_TIP_PSS = 1 THEN 'PF'
                    ELSE 'PJ'
                END AS TIPO,
                t5.DATA,
                t5.CD_TIP_TIT AS COD_TITULO,
                CONCAT(STRIP(t7.SG_TIP_TIT), STRIP(t7.CD_CLS_TIP_TIT)) AS SIGLA,
                CAST(t5.QUANTIDADE AS BIGINT) AS QUANTIDADE,
                CASE 
                    WHEN t5.CD_CLI_CSTD = 903485186 THEN 'ESCRITURAL'
                    ELSE 'CUSTÓDIA'
                END AS CUSTODIANTE
            FROM (
                SELECT
                    CD_CLI_EMT,
                    CD_TIP_TIT,
                    CD_CLI_ACNT,
                    CD_CLI_CSTD,
                    DATA,
                    QUANTIDADE
                FROM (
                    SELECT
                        t1.CD_CLI_EMT,
                        t1.CD_TIP_TIT,
                        t1.CD_CLI_ACNT,
                        t1.CD_CLI_CSTD,
                        t1.DT_MVTC AS DATA,
                        t1.QT_TIT_ATU AS QUANTIDADE
                    FROM
                        DB2AEB.MVTC_DIAR_PSC t1
                    WHERE
                        t1.CD_CLI_EMT = :mci
                    UNION ALL
                    SELECT
                        t1.CD_CLI_EMT,
                        t1.CD_TIP_TIT,
                        t1.CD_CLI_ACNT,
                        t1.CD_CLI_CSTD,
                        t1.DT_PSC - 1 DAY AS DATA,
                        t1.QT_TIT_INC_MM AS QUANTIDADE
                    FROM
                        DB2AEB.PSC_TIT_MVTD t1
                    WHERE
                        t1.CD_CLI_EMT = :mci
                ) t10
            ) t5
                LEFT JOIN DB2MCI.CLIENTE t6
                    ON t5.CD_CLI_ACNT = t6.COD
                LEFT JOIN DB2AEB.TIP_TIT t7
                    ON t5.CD_TIP_TIT = t7.CD_TIP_TIT
                LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                    ON t5.CD_CLI_ACNT = t8.CD_CLI_ACNT
            WHERE
                DATA BETWEEN :data_ant AND :data
            ORDER BY
                CAST(t5.CD_CLI_ACNT AS INTEGER),
                DATA DESC
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, data_ant=_data_ant, data=_data.strftime("%Y-%m-%d")),
    )
    load.columns = [str(columns).upper() for columns in load.columns]
    load["COD_TITULO"] = load["COD_TITULO"].astype(str)
    load = load[~load["MCI"].isin([205007939, 211684707]) & load["QUANTIDADE"].ne(0)]
    load.reset_index(inplace=True)

    dfixo = load[["MCI", "INVESTIDOR", "CPF_CNPJ", "TIPO"]].copy()
    dfixo.drop_duplicates(subset=["MCI"], inplace=True)

    lista_tit = []

    for xx in (load["COD_TITULO"] + load["SIGLA"]).unique():
        dfx = load.loc[(load["COD_TITULO"] + load["SIGLA"]) == xx].copy()
        dfx.reset_index(inplace=True)

        tipo = f"{dfx['SIGLA'].iloc[0]} {dfx['COD_TITULO'].iloc[0]}"

        dfbb = dfx[dfx["CUSTODIANTE"].eq("ESCRITURAL")].copy()[["MCI", "QUANTIDADE"]]
        dfbb.rename(columns={"QUANTIDADE": "BB_" + tipo}, inplace=True)

        dfb3 = dfx[dfx["CUSTODIANTE"].eq("CUSTÓDIA")].copy()[["MCI", "QUANTIDADE"]]
        dfb3.rename(columns={"QUANTIDADE": "B3_" + tipo}, inplace=True)

        dfx = pd.merge(dfbb, dfb3, how="outer", on=["MCI"])

        dfixo = pd.merge(dfixo, dfx, how="left", on=["MCI"])

        lista_tit.append(tipo)

    dfixo.fillna(0, inplace=True)

    cols = ["MCI", "INVESTIDOR", "CPF_CNPJ"]

    for tit in lista_tit:
        dfixo[f"TOTAL_{tit}"] = dfixo[f"BB_{tit}"] + dfixo[f"B3_{tit}"]
        cols.extend([f"BB_{tit}", f"B3_{tit}", f"TOTAL_{tit}"])

    dfixo = dfixo[cols]

    return dfixo, lista_tit


def load_data(_mci: int) -> tuple[str, ...]:
    load = engine.query(
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


params: dict[str, bool | str] = dict(type="primary", use_container_width=True)

st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"], key="option")

kv: dict[str, int] = load_active("null" if st.session_state["option"] == "ativos" else "not null")

with st.columns(2)[0]:
    st.selectbox(
        label="**Clientes ativos:**" if st.session_state["option"] == "ativos" else "**Clientes inativos:**",
        options=kv.keys(),
        key="empresa",
    )

    with st.columns(3)[0]:
        st.date_input(label="**Data:**", value=date.today(), key="data", format="DD/MM/YYYY")

mci: int = kv.get(st.session_state["empresa"])

data_ant: date = (st.session_state["data"].replace(day=1) - timedelta(days=1)).replace(day=28)

with st.columns(2)[0]:
    st.markdown("")

    col = st.columns(3)
    col[0].button(label="**Visualizar na tela**", key="view", icon=":material/preview:", **params)
    col[1].button(label="**Baixar CSV**", key="csv", icon=":material/download:", **params)
    col[2].button(label="**Baixar Excel**", key="xlsx", icon=":material/download:", **params)

if st.session_state["view"]:
    with st.spinner("**:material/hourglass: Preparando os dados para exibir, aguarde...**", show_time=True):
        get_report: pd.DataFrame = load_report(mci, data_ant, st.session_state["data"])[0]

        if not get_report.empty:
            get_title: tuple[str, ...] = load_data(mci)

            st.write(f"**MCI:** {get_title[0]}")
            st.write(f"**Empresa:** {get_title[1]}")
            st.write(f"**CNPJ:** {get_title[2]}")
            st.write(f"**Data:** {st.session_state['data']:%d/%m/%Y}")

            st.data_editor(
                data=get_report,
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

            st.button(label="**Voltar**", key="back_view", type="primary", icon=":material/reply:")

        else:
            st.toast(body="**Não há dados para exibir...**", icon=":material/error:")

if st.session_state["csv"]:
    with st.spinner("**:material/hourglass: Preparando os dados para baixar, aguarde...**", show_time=True):
        get_report: pd.DataFrame = load_report(mci, data_ant, st.session_state["data"])[0]

        if not get_report.empty:
            sigla: str = load_data(mci)[3]

            st.toast(body="**Arquivo CSV pronto para baixar**", icon=":material/check_circle:")

            st.download_button(
                label="**Baixar CSV**",
                data=get_report.to_csv(index=False).encode("utf-8"),
                file_name=f"{sigla}-{st.session_state['data']}.csv",
                mime="text/csv",
                key="download_csv",
                type="primary",
                icon=":material/download:",
            )

        else:
            st.toast(body="**Não há dados para baixar...**", icon=":material/error:")

if st.session_state["xlsx"]:
    with st.spinner("**:material/hourglass: Preparando os dados para baixar, aguarde...**", show_time=True):
        get_report, list_tit = load_report(mci, data_ant, st.session_state["data"])

        if not get_report.empty:
            get_title: tuple[str, ...] = load_data(mci)

            path_xlsx: io.BytesIO = io.BytesIO()

            writer: pd.ExcelWriter = pd.ExcelWriter(path_xlsx, engine="xlsxwriter")

            if len(get_report) <= int(1e6):
                get_report.to_excel(writer, sheet_name="1", startrow=5, header=False, index=False)
                workbook = writer.book
                worksheet1 = writer.sheets["1"]

            elif len(get_report) <= int(2e6):
                get_report[:int(1e6)].to_excel(writer, sheet_name="1", startrow=5, header=False, index=False)
                get_report[int(1e6):].to_excel(writer, sheet_name="2", startrow=2, header=False, index=False)
                workbook = writer.book
                worksheet1 = writer.sheets["1"]
                worksheet2 = writer.sheets["2"]

            else:
                get_report[:int(1e6)].to_excel(writer, sheet_name="1", startrow=5, header=False, index=False)
                get_report[int(1e6):int(2e6)].to_excel(writer, sheet_name="2", startrow=2, header=False, index=False)
                get_report[int(2e6):].to_excel(writer, sheet_name="3", startrow=2, header=False, index=False)
                workbook = writer.book
                worksheet1 = writer.sheets["1"]
                worksheet2 = writer.sheets["2"]
                worksheet3 = writer.sheets["3"]

            # criando formatos
            number_format = workbook.add_format(dict(num_format=0))

            titulo_1 = workbook.add_format(dict(bold=True, align="left", bg_color="#025AA5", right=2, font_size=14,
                                                font_color="white"))
            titulo_2 = workbook.add_format(dict(bold=True, align="left", bg_color="#025AA5", right=2, bottom=2,
                                                font_size=14, font_color="white"))

            texto_format = workbook.add_format(dict(align="left", bold=True, bg_color="#FFED00"))

            # formatando colunas (largura e número)
            worksheet1.set_column(0, 0, 12, number_format)
            worksheet1.set_column(1, 1, 40)
            worksheet1.set_column(2, 2, 16, number_format)

            # criando os dados básicos do emissor
            worksheet1.merge_range("A1:C1", f"Emissor......................: {get_title[1]}", titulo_1)
            worksheet1.merge_range("A2:C2", f"CNPJ.........................: {get_title[2]}", titulo_1)
            worksheet1.merge_range("A3:C3", f"Data de Liquidação...........: "
                                            f"{st.session_state['data']:%d/%m/%Y}", titulo_2)

            # escrevendo os nomes das colunas no xlsx
            worksheet1.write("A5", "MCI", texto_format)
            worksheet1.write("B5", "Nome", texto_format)
            worksheet1.write("C5", "CPF/CNPJ", texto_format)

            # escrevendo os nomes dos títulos nas colunas e pegando a quantidade de títulos
            for x in range(len(list_tit)):
                worksheet1.set_column(3, 3 + (x * 3), 13, number_format)
                worksheet1.set_column(4, 4 + (x * 3), 13, number_format)
                worksheet1.set_column(5, 5 + (x * 3), 13, number_format)
                worksheet1.write(4, 3 + (x * 3), list_tit[x] + " BB", texto_format)
                worksheet1.write(4, 4 + (x * 3), list_tit[x] + " B3", texto_format)
                worksheet1.write(4, 5 + (x * 3), list_tit[x] + " Total", texto_format)

            if len(get_report) > int(1e6):
                # formatando colunas (largura e número)
                worksheet2.set_column(0, 0, 12, number_format)
                worksheet2.set_column(1, 1, 40)
                worksheet2.set_column(2, 2, 16, number_format)

                # escrevendo os nomes das colunas no xlsx
                worksheet2.write("A2", "MCI", texto_format)
                worksheet2.write("B2", "Nome", texto_format)
                worksheet2.write("C2", "CPF/CNPJ", texto_format)

                # escrevendo os nomes dos títulos nas colunas e pegando a quantidade de títulos
                for x in range(len(list_tit)):
                    worksheet2.set_column(3, 3 + (x * 3), 13, number_format)
                    worksheet2.set_column(4, 4 + (x * 3), 13, number_format)
                    worksheet2.set_column(5, 5 + (x * 3), 13, number_format)
                    worksheet2.write(1, 3 + (x * 3), list_tit[x] + " BB", texto_format)
                    worksheet2.write(1, 4 + (x * 3), list_tit[x] + " B3", texto_format)
                    worksheet2.write(1, 5 + (x * 3), list_tit[x] + " Total", texto_format)

            # criando filtro
            worksheet1.autofilter(4, 0, 4, 2 + (3 * len(list_tit)))

            if len(get_report) > int(1e6):
                worksheet2.autofilter(1, 0, 1, 2 + (3 * len(list_tit)))

            # Congelando as primeiras 5 linhas
            worksheet1.freeze_panes(5, 0)

            if len(get_report) > int(1e6):
                worksheet2.freeze_panes(2, 0)

            workbook.close()
            writer.close()

            st.toast(body="**Arquivo XLSX pronto para baixar**", icon=":material/check_circle:")

            st.download_button(
                label="**Baixar XLSX**",
                data=path_xlsx.getvalue(),
                file_name=f"{get_title[3]}-{st.session_state['data']}.xlsx",
                mime="application/vnd.ms-excel",
                key="download_xlsx",
                type="primary",
                icon=":material/download:"
            )

        else:
            st.toast("**Não há dados para baixar...**", icon=":material/error:")
