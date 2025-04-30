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
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from streamlit.connections import SQLConnection

reportlab.rl_config.warnOnMissingFontGlyphs = 0

pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
pdfmetrics.registerFont(TTFont("VeraBd", "VeraBd.ttf"))
pdfmetrics.registerFont(TTFont("VeraIt", "VeraIt.ttf"))
pdfmetrics.registerFont(TTFont("VeraBI", "VeraBI.ttf"))

st.cache_data.clear()

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)

st.subheader(":material/hide_source: Cancelamento de CEPAC")

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)


@st.cache_data(show_spinner="**:material/hourglass: Obtendo os dados, aguarde...**")
def load_extract_mci(mci: int, active: int) -> pd.DataFrame:
    return engine.query(
        sql="""
        SELECT CAST(t1.DT_MVTC AS DATE) AS DATA_MVTC,
               CAST(t1.QT_TIT_MVTD AS INT) AS MVT,
               CAST(t1.QT_TIT_ATU AS INT) AS SALDO
        FROM DB2AEB.MVTC_DIAR_PSC t1
        WHERE t1.CD_CLI_EMT = 906535030 
          AND t1.CD_CLI_ACNT = :mci
          AND t1.CD_CLI_CSTD = 903485186
          AND t1.CD_TIP_TIT = :active
        ORDER BY t1.DT_MVTC
        """,
        show_spinner=False,
        ttl=60,
        params=dict(mci=mci, active=active),
    )


@st.cache_data(show_spinner="**:material/hourglass: Obtendo os dados, aguarde...**")
def load_extract_cnpj(cnpj: int, active: int) -> pd.DataFrame:
    return engine.query(
        sql="""
        SELECT CAST(t1.DT_MVTC AS DATE) AS DATA_MVTC,
               CAST(t1.QT_TIT_MVTD AS INT) AS MVT,
               CAST(t1.QT_TIT_ATU AS INT) AS SALDO
        FROM DB2AEB.MVTC_DIAR_PSC t1
                INNER JOIN DB2MCI.CLIENTE t2
                        ON t2.COD = t1.CD_CLI_ACNT
        WHERE t1.CD_CLI_EMT = 906535030 
          AND t2.COD_CPF_CGC = :cnpj
          AND t1.CD_CLI_CSTD = 903485186
          AND t1.CD_TIP_TIT = :active
        ORDER BY t1.DT_MVTC
        """,
        show_spinner=False,
        ttl=60,
        params=dict(cnpj=cnpj, active=active),
    )


@st.cache_data(show_spinner="**:material/hourglass: Obtendo os dados, aguarde...**")
def load_cadastro(field: str, value: int) -> pd.DataFrame:
    return engine.query(
        sql=f"""
        SELECT t1.COD AS MCI_INVESTIDOR,
               STRIP(t1.NOM) AS INVESTIDOR,
               CASE
                   WHEN t1.COD_TIPO = 2 THEN LPAD(t1.COD_CPF_CGC, 14, '0')
                   ELSE LPAD(t1.COD_CPF_CGC, 11, '0')
               END AS CPF_CNPJ
        FROM DB2MCI.CLIENTE t1
        WHERE t1.{field.upper()} = :value
        """,
        show_spinner=False,
        ttl=60,
        params=dict(value=value),
    )


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
col1.number_input("**MCI da Empresa:**", min_value=0, max_value=9999999999, key="mci_empresa")
col2.number_input("**CNPJ da Empresa:**", min_value=0, max_value=99999999999999, key="cnpj_empresa")

st.markdown("##### Preencher o tipo do papel")
st.radio("**Ativo:**", options=("Água Branca (CAB)", "Água Espraiada (CPC)", "Faria Lima (CFL)"), key="tipo_papel")

st.button("**Montar Declaração**", key="btn_montar", type="primary", icon=":material/picture_as_pdf:")

if st.session_state.btn_montar:
    if not any([st.session_state["mci_empresa"], st.session_state["cnpj_empresa"]]):
        st.toast("**Deve preencher um dos campos de MCI ou CNPJ...**", icon=":material/warning:")

    elif all([st.session_state["mci_empresa"], st.session_state["cnpj_empresa"]]):
        st.toast("**Só pode preencher um dos campos MCI ou CNPJ e não dos dois...**", icon=":material/warning:")

    else:
        ativo: int = 123 if st.session_state["tipo_papel"] == "Água Branca (CAB)" else 55 \
            if st.session_state["tipo_papel"] == "Água Espraiada (CPC)" else 56

        extract: pd.DataFrame = load_extract_mci(st.session_state["mci_empresa"], ativo) \
            if st.session_state["mci_empresa"] else load_extract_cnpj(st.session_state["cnpj_empresa"], ativo)

        extract["data_mvtc"] = pd.to_datetime(extract["data_mvtc"]).dt.strftime("%d.%m.%Y")

        cadastro: pd.DataFrame = load_cadastro("cod", st.session_state["mci_empresa"]) \
            if st.session_state["mci_empresa"] else load_cadastro("cod_cpf_cgc", st.session_state["cnpj_empresa"])

        mci_investidor: int = cadastro["mci_investidor"].iloc[0]
        investidor: str = cadastro["investidor"].iloc[0]
        cpf_cnpj: str = cadastro["cpf_cnpj"].iloc[0]
        
        if len(extract) == 0:
            st.toast("**Empresa e ativo selecionados não apresentaram movimentações**", icon=":material/warning:")
            st.stop()
        else:
            # definindo estilos que serão usados na carta
            header: ParagraphStyle = ParagraphStyle(name="cabecalho", fontName="Vera", fontSize=11,
                                                    textColor=colors.black, aligment=TA_RIGHT)
            conteudo: ParagraphStyle = ParagraphStyle(name="conteudo", fontName="Vera", fontSize=11,
                                                      textColor=colors.black, aligment=TA_JUSTIFY)
            footer: ParagraphStyle = ParagraphStyle(name="cabecalho", fontName="Vera", fontSize=8,
                                                    textColor=colors.black)

            # montagem da carta
            elements: list = [
                Image("static/imagens/bb.jpg", 300, 38),
                Spacer(30, 30),
                Paragraph(f"Diretoria Operações - {date.today().year}/DIEST-{last_protocol}", header),
                Paragraph(f"Rio de Janeiro, {date.today():%d/%m/%Y}", header), Spacer(30, 30),
                Paragraph("-", conteudo), Paragraph("São Paulo Urbanismo", conteudo),
                Paragraph("Rua Líbero Badaró, 504 - 16º andar", conteudo),
                Paragraph("CEP: 01.008-906 - São Paulo-SP", conteudo),
                Paragraph("Ref. Cancelamento de CEPAC", conteudo), Spacer(30, 30),
                Paragraph(f"Confirmamos o cancelamento solicitado conforme carta DAF "
                          f"{st.session_state['carta_daf']}, de {st.session_state['data_daf']}, Processo SEI "
                          f"{st.session_state['processo_sei']}.", conteudo), Spacer(20, 20),
                Paragraph(f"Tipo: {st.session_state['tipo_papel']}", conteudo), Spacer(20, 20)
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

            elements.append(Paragraph("_" * 129, footer))
            elements.append(Paragraph("DIRETORIA OPERAÇÕES - DIOPE", footer))
            elements.append(Paragraph("Gerência Executiva de Negócios em Serviços Fiduciários - Gerência de "
                                      "Escrituração e Trustee", footer))
            elements.append(Paragraph("Avenida República do Chile, 330 - 9º andar - Torre Oeste - Centro - "
                                      "Rio de Janeiro RJ", footer))
            elements.append(Paragraph("Telefone: (021) 3808-3715", footer))
            elements.append(Paragraph("Ouvidoria BB - 0800 729 5678)", footer))

            arquivo: str = (f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-CancelamentoCEPAC-"
                            f"Carta-DAF{st.session_state['carta_daf']}.pdf")

            pdf: SimpleDocTemplate = SimpleDocTemplate(arquivo, pagesize=A4)
            pdf.build(elements)

            linha: str = (f"{date.today().year}-{last_protocol}-CancelamentoCEPAC-Carta-"
                          f"DAF{st.session_state['carta_daf']}")

            with open("static/arquivos/protocolador/protocolador.txt", "a") as save_protocol:
                save_protocol.write("\n")
                save_protocol.write(linha)

            st.toast("**Declaração de Cancelamento de CEPAC gerada com sucesso!**", icon=":material/check_circle:")

            with st.container():
                with st.columns(2)[0]:
                    st.text_input("**Remetente:**", key="from_email", help="Só pode ter um e-mail para remetente")
                    st.text_input("**Destinatário:**", key="to_email", help="Mais e-mails deve colocar vírgula")
                    st.text_input("**Com Cópia:**", key="cc_email", help="Mais e-mails deve colocar vírgula")

                if st.button("**Enviar**", key="enviar_email", icon=":material/send:"):
                    if not all([st.session_state["from_email"], st.session_state["to_email"]]):
                        st.toast("**Deve preencher e-mails de remetente e destinatário**", icon=":material/warning:")
                        st.stop()
                    else:
                        msgcp = MIMEMultipart()
                        msgcp["Subject"] = "DECLARAÇÃO CANCELAMENTO DE CEPAC"
                        msgcp["From"] = st.session_state["from_email"]
                        msgcp["To"] = st.session_state["to_email"]
                        msgcp["Cc"] = st.session_state["cc_email"]

                        html = """<html><head></head><body>
                        <br><br>
                        <div>Prezados,<br><br>
                        Segue <b>em anexo</b> Declaração de Cancelamento de CEPAC</div>
                        <br><br>
                        </body></html>"""

                        msgcp.attach(MIMEText(html, "html"))

                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(open(arquivo, "rb").read())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", "attachment; filename='cancelamentocepac.pdf'")
                        msgcp.attach(part)

                        with smtplib.SMTP("smtp.bb.com.br") as server:
                            server.set_debuglevel(1)

                            try:
                                server.sendmail(st.session_state["from_email"],
                                                st.session_state["to_email"] + st.session_state["cc_email"],
                                                msgcp.as_string())
                                st.toast("**Declaração de Cancelamento de CEPAC enviado por email com sucesso!**",
                                         icon=":material/check_circle:")
                            except smtplib.SMTPException:
                                st.toast("**Houve falha ao enviar e-mails...**", icon=":material/error:")
