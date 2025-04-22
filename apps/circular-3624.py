from datetime import date

import pandas as pd
import streamlit as st
import xlsxwriter
from streamlit.connections import SQLConnection

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)

engine = st.connection(name="DB2", type=SQLConnection)

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)

st.subheader(":material/cycle: Circular BACEN 3624")

st.markdown("#### Envio de arquivo à COGER, com a informação dos rendimentos pagos aos acionistas do Banco do Brasil, "
            "para atender Carta Circular 3624 do Banco Central")

st.cache_data.clear()


@st.cache_data(show_spinner=False)
def load_data(year: int, month: int) -> pd.DataFrame:
    return engine.query(
        sql="""
            SELECT
                t2.CD_CLSC_TIP_DRT,
                t1.DT_DLBC,
                YEAR(t1.DT_DLBC) AS ANO_DELIB,
                t1.VL_MVT_REN,
                t1.VL_IR_CLCD_MVT_REN,
                t1.VL_MVT_REN - t1.VL_IR_CLCD_MVT_REN AS LIQUIDO_PRINCIPAL,
                t1.VL_CORR_MVT_REN,
                t1.VL_IR_CORR_MVT_REN,
                t1.VL_IR_CORR_MVT_REN - t1.VL_IR_CORR_MVT_REN AS LIQUIDO_CORR
            FROM
                DB2AEB.MVT_REN t1
                INNER JOIN DB2AEB.TIP_DRT t2
                    ON t2.CD_TIP_DRT = t1.CD_TIP_DRT
            WHERE
                t1.CD_TIP_DRT IN (9) AND
                YEAR(t1.DT_MVT_DRT) = :year AND
                MONTH(t1.DT_MVT_DRT) = :month AND
                t1.CD_CLI_DLBC IN (903485186) AND
                t2.CD_CLSC_TIP_DRT IN (1, 5, 10, 14)
            ORDER BY
                t1.DT_DLBC DESC,
                t1.CD_TIP_DRT
        """,
        show_spinner=False,
        ttl=60,
        params=dict(year=year, month=month),
    )


def preparo_xlsx(year: int, month: int) -> None:
    with st.spinner("Obtendo os dados, aguarde...", show_time=True):
        xlsx = load_data(year, month)
        if xlsx.empty:
            st.toast(body="**Não há dados para enviar**", icon=":material/warning:")
        else:
            with xlsxwriter.Workbook(f"static/escriturais/@deletar/circular3624-{year}-{month}.xlsx") as wb:
                ws = wb.add_worksheet(f"{year}{month:02d}")

                title = wb.add_format(dict(bold=True, align="center", bg_color="a6a6a6", border=2, font_size=14))
                title2 = wb.add_format(dict(bold=True, align="center", bg_color="FFED00", border=2, font_size=24))

                vlr_format = wb.add_format(dict(num_format="#,##0.00", border=2, align="center"))
                vlr_format2 = wb.add_format(dict(num_format="#,##0.00", border=2, align="center", bold=True))

                txt_format = wb.add_format(dict(align="center", bg_color="FFED00", border=2, font_size=12, bold=True))
                txt_format2 = wb.add_format(dict(align="center", bg_color="bfbfbf", border=2, bold=True))

                bruto_div_ano_corrente = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_CORR_MVT_REN'].sum())
                )

                ir_div_ano_corrente = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CLCD_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CORR_MVT_REN'].sum())
                )

                liquido_div_ano_corrente = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_PRINCIPAL'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_CORR'].sum())
                )

                bruto_div_ano_antes = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_CORR_MVT_REN'].sum())
                )

                ir_div_ano_antes = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CLCD_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CORR_MVT_REN'].sum())
                )

                liquido_div_ano_antes = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_PRINCIPAL'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_CORR'].sum())
                )

                bruto_div_ano_anterior = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14)))['VL_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_CORR_MVT_REN'].sum())
                )

                ir_div_ano_anterior = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CLCD_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CORR_MVT_REN'].sum())
                )

                liquido_div_ano_anterior = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_PRINCIPAL'].sum()
                          ) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_CORR'].sum())
                )

                bruto_jcp_ano_corrente = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['VL_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_CORR_MVT_REN'].sum())
                )

                ir_jcp_ano_corrente = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['VL_IR_CLCD_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CORR_MVT_REN'].sum())
                )

                liquido_jcp_ano_corrente = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['LIQUIDO_PRINCIPAL'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year) & ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_CORR'].sum())
                )

                bruto_jcp_ano_antes = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['VL_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_CORR_MVT_REN'].sum())
                )

                ir_jcp_ano_antes = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['VL_IR_CLCD_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CORR_MVT_REN'].sum())
                )

                liquido_jcp_ano_antes = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['LIQUIDO_PRINCIPAL'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] == year - 1) & (
                                    (xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_CORR'].sum())
                )

                bruto_jcp_ano_anterior = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['VL_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_CORR_MVT_REN'].sum())
                )

                ir_jcp_ano_anterior = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['VL_IR_CLCD_MVT_REN'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['VL_IR_CORR_MVT_REN'].sum())
                )

                liquido_jcp_ano_anterior = (
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 5) | (xlsx['CD_CLSC_TIP_DRT'] == 10))
                    )['LIQUIDO_PRINCIPAL'].sum()) +
                    float(xlsx.filter(
                        (xlsx['ANO_DELIB'] != year) & (xlsx['ANO_DELIB'] != year - 1) &
                        ((xlsx['CD_CLSC_TIP_DRT'] == 1) | (xlsx['CD_CLSC_TIP_DRT'] == 14))
                    )['LIQUIDO_CORR'].sum())
                )

                ws.set_column(0, 0, 20)
                ws.set_column(1, 6, 18)

                ws.merge_range("B1:G2", "BANCO DO BRASIL", title2)
                ws.merge_range("B3:D3", "DIVIDENDOS E ATUALIZAÇÃO", title)
                ws.merge_range("E3:G3", "JCP E ATUALIZAÇÃO", title)

                ws.write("A3", f"PAGOS EM {mes:02d}/{ano}", txt_format)
                ws.write("A4", "Ano de Deliberação", txt_format2)
                ws.write("B4", "VALOR BRUTO", txt_format2)
                ws.write("C4", "IR", txt_format2)
                ws.write("D4", "VALOR LÍQUIDO", txt_format2)
                ws.write("E4", "VALOR BRUTO", txt_format2)
                ws.write("F4", "IR", txt_format2)
                ws.write("G4", "VALOR LÍQUIDO", txt_format2)
                ws.write("A5", str(year), txt_format2)
                ws.write("A6", str(year - 1), txt_format2)
                ws.write("A7", f"Anteriores a {year - 1}", txt_format2)
                ws.write("A8", "TOTAL", txt_format2)

                ws.write("B5", bruto_div_ano_corrente, vlr_format)
                ws.write("C5", ir_div_ano_corrente, vlr_format)
                ws.write("D5", liquido_div_ano_corrente, vlr_format)
                ws.write("B6", bruto_div_ano_antes, vlr_format)
                ws.write("C6", ir_div_ano_antes, vlr_format)
                ws.write("D6", liquido_div_ano_antes, vlr_format)
                ws.write("B7", bruto_div_ano_anterior, vlr_format)
                ws.write("C7", ir_div_ano_anterior, vlr_format)
                ws.write("D7", liquido_div_ano_anterior, vlr_format)
                ws.write("E5", bruto_jcp_ano_corrente, vlr_format)
                ws.write("F5", ir_jcp_ano_corrente, vlr_format)
                ws.write("G5", liquido_jcp_ano_corrente, vlr_format)
                ws.write("E6", bruto_jcp_ano_antes, vlr_format)
                ws.write("F6", ir_jcp_ano_antes, vlr_format)
                ws.write("G6", liquido_jcp_ano_antes, vlr_format)
                ws.write("E7", bruto_jcp_ano_anterior, vlr_format)
                ws.write("F7", ir_jcp_ano_anterior, vlr_format)
                ws.write("G7", liquido_jcp_ano_anterior, vlr_format)

                ws.write_formula("B8", "=SUM(B5:B7)", vlr_format2)
                ws.write_formula("C8", "=SUM(C5:C7)", vlr_format2)
                ws.write_formula("D8", "=SUM(D5:D7)", vlr_format2)
                ws.write_formula("E8", "=SUM(E5:E7)", vlr_format2)
                ws.write_formula("F8", "=SUM(F5:F7)", vlr_format2)
                ws.write_formula("G8", "=SUM(G5:G7)", vlr_format2)

                xlsx.write_excel(workbook=wb, worksheet=ws)


with open("static/arquivos/email3624.txt") as f:
    email = f.readlines()

para = st.text_input(label="**PARA:**", value=email[0])
cc = st.text_input(label="**CC:**", value=email[1])

hoje = date.today()

col = st.columns([1.5, 0.5, 1])
mes = col[0].slider(label="**Mês:**", min_value=1, max_value=12, value=hoje.month - 1 if 1 <= hoje.month - 1 else 12)
ano = col[1].selectbox(label="**Ano:**", options=range(hoje.year, 1995, -1), index=0 if 1 <= hoje.month - 1 else 1)

if st.columns(7)[0].button("**ENVIAR**", type="primary", use_container_width=True):
    if all([para, cc]):
        preparo_xlsx(ano, mes)
    else:
        st.toast("**Ambos PARA: e CC: precisam ser preenchidos**", icon=":material/warning:")
