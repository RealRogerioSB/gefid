import os
import smtplib
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import reportlab.rl_config
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from streamlit.connections import SQLConnection

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

message = st.empty()


def load_extract(join: str, field: str, value: int, active: int) -> pd.DataFrame:
    return engine.query(
        sql=f"""
            SELECT CAST(t1.DT_MVTC AS DATE)    AS DATA_MVTC,
                   CAST(t1.QT_TIT_MVTD AS INT) AS MVT,
                   CAST(t1.QT_TIT_ATU AS INT)  AS SALDO
            FROM DB2AEB.MVTC_DIAR_PSC t1{join}
            WHERE t1.CD_CLI_EMT = 906535030
              AND {field} = :value
              AND t1.CD_CLI_CSTD = 903485186
              AND t1.CD_TIP_TIT = :active
            ORDER BY CAST(t1.DT_MVTC AS DATE)
            """,
        show_spinner=False,
        ttl=0,
        params=dict(value=value, active=active),
    )


def load_cadastro(field: str, value: int) -> tuple[str, ...]:
    load: pd.DataFrame = engine.query(
        sql=f"""
            SELECT t1.COD AS MCI,
                   STRIP(t1.NOM) AS INVESTIDOR,
                   CASE
                       WHEN t1.COD_TIPO = 2 THEN LPAD(t1.COD_CPF_CGC, 14, '0')
                       ELSE LPAD(t1.COD_CPF_CGC, 11, '0')
                   END AS CPF_CNPJ
            FROM DB2MCI.CLIENTE t1
            WHERE t1.{field.upper()} = :value
        """,
        show_spinner=False,
        ttl=0,
        params=dict(value=value),
    )
    return str(load["mci"].iloc[0]), load["investidor"].iloc[0], load["cpf_cnpj"].iloc[0]


@st.dialog("Despachar E-mail")
def send_mail() -> None:
    st.text_input("**Para:**", key="to_addr", help="Mais e-mail, separa com a vírgula", icon=":material/mail:")
    st.text_input("**Cc:**", key="cc_addr", help="Mais e-mail, separa com a vírgula", icon=":material/mail:")
    st.columns(3)[1].button("**Despachar**", key="despachar", type="primary", icon=":material/send:",
                            use_container_width=True)

    if st.session_state["despachar"]:
        if not any([st.session_state["to_addr"], st.session_state["cc_addr"]]):
            st.stop()

        msg = MIMEMultipart()
        msg["From"] = "aescriturais@bb.com.br"
        msg["To"] = st.session_state["to_addr"]
        msg["Cc"] = st.session_state["cc_addr"]
        msg["Subject"] = "DECLARAÇÃO DE MAIORES INVESTIDORES"
        msg.attach(MIMEText(
            """<html><head></head><body>
            <br><br>
            <div>
                Prezados(as),<br><br>
                Segue <b> em anexo </b> Declaração de Maiores Investidores.
            </div><br><br></body></html>""",
            "html"
        ))

        part = MIMEBase("application", "octet-stream")

        with open(f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-"
                  f"CancelamentoCEPAC-Carta-DAF{st.session_state['carta_daf']}.pdf", "rb") as file1:
            payload: bytes = file1.read()

        part.set_payload(payload)

        encoders.encode_base64(part)

        part.add_header("Content-Disposition", f"attachment; filename='cancelamento_cepac.pdf'")

        msg.attach(part)

        with smtplib.SMTP("smtp.bb.com.br", 25) as server:
            server.set_debuglevel(1)

            try:
                server.sendmail(
                    from_addr="aescriturais@bb.com.br",
                    to_addrs=st.session_state["to_addr"] + st.session_state["cc_addr"],
                    msg=msg.as_string()
                )

            except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected):
                message.error("**Houve falha ao enviar e-mail**", icon=":material/error:", width=600)
                st.stop()

        message.info("**Declaração enviada com sucesso!**", icon=":material/check_circle:", width=600)

        with open("static/arquivos/protocolador/protocolador.txt", "a") as save_protocol:
            save_protocol.write(f"{date.today().year}-{last_protocol}-CancelamentoCEPAC-Carta-DAF"
                                f"{st.session_state['carta_daf']}")

        st.rerun()


st.subheader(":material/hide_source: Cancelamento de CEPAC")

with open("static/arquivos/protocolador/protocolador.txt") as f:
    last_protocol: int = int([x.strip().split("-") for x in f.readlines()][-1][1]) + 1

st.markdown(f"Protocolo: **{date.today().year}** / DIEST: **{last_protocol}**")

st.markdown("##### Preencher os dados do pedido da Prefeitura de São Paulo")

col1, col2, col3, _ = st.columns([1, 1, 1, 3])
col1.text_input("**Carta DAF:**", key="carta_daf")
col2.date_input("**Data da Carta DAF:**", key="data_daf", format="DD/MM/YYYY")
col3.text_input("**Processo SEI:**", key="processo_sei")

st.markdown("##### Preencher MCI ou CNPJ da empresa detentora do papel")

col1, col2, _ = st.columns([1, 1, 3])
col1.number_input("**MCI da Empresa:**", min_value=0, max_value=9999999999, key="mci_client")
col2.number_input("**CNPJ da Empresa:**", min_value=0, max_value=99999999999999, key="cnpj_client")

st.markdown("##### Preencher o tipo do papel")
st.radio("**Ativo:**", options=["Água Branca (CAB)", "Água Espraiada (CPC)", "Faria Lima (CFL)"], key="tipo_papel")

col1, col2, *_ = st.columns(6)
col1.button("**Montar Declaração**", key="montar", type="primary",
            icon=":material/picture_as_pdf:", use_container_width=True)
col2.button("**Preparar E-mail**", key="open_mail", type="primary",
            icon=":material/mail:", use_container_width=True)

if st.session_state["montar"]:
    if all([st.session_state["mci_client"], st.session_state["cnpj_client"]]):
        message.warning("**Só pode preencher um dos campos MCI ou CNPJ e não dos dois...**",
                        icon=":material/warning:", width=600)
        st.stop()

    if not any([st.session_state["mci_client"], st.session_state["cnpj_client"]]):
        message.warning("**Deve preencher um dos campos de MCI ou CNPJ...**",
                        icon=":material/warning:", width=600)
        st.stop()

    with st.spinner("**:material/hourglass: Preparando para montar PDF, aguarde...**", show_time=True):
        ativo: int = 123 if st.session_state["tipo_papel"] == "Água Branca (CAB)" else 55 \
            if st.session_state["tipo_papel"] == "Água Espraiada (CPC)" else 56

        extract: pd.DataFrame = load_extract(
            join="" if st.session_state["mci_client"] else " INNER JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_ACNT",
            field="t1.CD_CLI_ACNT" if st.session_state["mci_client"] else "t2.COD_CPF_CGC",
            value=st.session_state["mci_client"] if st.session_state["mci_client"] else st.session_state["cnpj_client"],
            active=ativo
        )

        extract["data_mvtc"] = pd.to_datetime(extract["data_mvtc"]).dt.strftime("%d.%m.%Y")

        if extract.empty:
            message.info("**Empresa e ativo selecionados não apresentaram movimentações**",
                         icon=":material/error:", width=600)
            st.stop()

        mci_investidor, investidor, cpf_cnpj = load_cadastro(
            field="cod" if st.session_state["mci_client"] else "cod_cpf_cgc",
            value=st.session_state["mci_client"] if st.session_state["mci_client"] else st.session_state["cnpj_client"],
        )

        reportlab.rl_config.warnOnMissingFontGlyphs = 0

        pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
        pdfmetrics.registerFont(TTFont("VeraBd", "VeraBd.ttf"))
        pdfmetrics.registerFont(TTFont("VeraIt", "VeraIt.ttf"))
        pdfmetrics.registerFont(TTFont("VeraBI", "VeraBI.ttf"))

        # definindo estilos que serão usados na carta
        header: ParagraphStyle = ParagraphStyle(name="header", fontName="Vera", fontSize=11,
                                                textColor=colors.black, aligment="right")
        content: ParagraphStyle = ParagraphStyle(name="content", fontName="Vera", fontSize=11,
                                                 textColor=colors.black, aligment="justify")
        footer: ParagraphStyle = ParagraphStyle(name="header", fontName="Vera", fontSize=8,
                                                textColor=colors.black)

        # montagem da carta
        elements: list = [
            Image("static/imagens/bb.jpg", 300, 38),
            Spacer(30, 30),
            Paragraph(f"Diretoria Operações - {date.today().year}/DIEST-{last_protocol}", header),
            Paragraph(f"Rio de Janeiro, {date.today():%d/%m/%Y}", header),
            Spacer(30, 30),
            Paragraph("-", content),
            Paragraph("São Paulo Urbanismo", content),
            Paragraph("Rua Líbero Badaró, 504 - 16º andar", content),
            Paragraph("CEP: 01.008-906 - São Paulo-SP", content),
            Paragraph("Ref. Cancelamento de CEPAC", content),
            Spacer(30, 30),
            Paragraph(f"Confirmamos o cancelamento solicitado conforme carta DAF "
                      f"{st.session_state['carta_daf']}, de {st.session_state['data_daf']}, Processo SEI "
                      f"{st.session_state['processo_sei']}.", content),
            Spacer(20, 20),
            Paragraph(f"Tipo: {st.session_state['tipo_papel']}", content),
            Spacer(20, 20)
        ]

        my_data = extract.values.tolist()
        my_data.insert(0, extract.columns)

        t: Table = Table(my_data, colWidths=100, repeatRows=1)
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), colors.black)
        ]))

        elements.append(Spacer(30, 30))
        elements.append(t)
        elements.append(Spacer(30, 30))

        elements.append(Paragraph("_" * 109, footer))
        elements.append(Paragraph("DIRETORIA OPERAÇÕES - DIOPE", footer))
        elements.append(Paragraph("Gerência Executiva de Negócios em Serviços Fiduciários - Gerência de "
                                  "Escrituração e Trustee", footer))
        elements.append(Paragraph("Avenida República do Chile, 330 - 9º andar - Torre Oeste - Centro - "
                                  "Rio de Janeiro RJ", footer))
        elements.append(Paragraph("Telefone: (021) 3808-3715", footer))
        elements.append(Paragraph("Ouvidoria BB - 0800 729 5678)", footer))

        pdf: SimpleDocTemplate = SimpleDocTemplate(
            filename=f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-CancelamentoCEPAC-Carta-"
                     f"DAF{st.session_state['carta_daf']}.pdf",
            pagesize=A4
        )
        pdf.build(elements)

        message.info("**Declaração de Cancelamento de CEPAC pronta para enviar e-mail**",
                     icon=":material/check_circle:", width=600)

if st.session_state["open_mail"]:
    if os.path.exists(f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-CancelamentoCEPAC-Carta-DAF"
                      f"{st.session_state['carta_daf']}.pdf"):
        send_mail()

    else:
        message.warning("Ainda não, primeiro clicar Montar Declaração...", icon=":material/warning:", width=600)
