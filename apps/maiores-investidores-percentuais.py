import os
import smtplib
from datetime import date, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import numpy as np
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

st.subheader(":material/workspace_premium: Declarações de Maiores Investidores Percentuais")


@st.cache_data(show_spinner="**:material/hourglass: Preparando a lista da empresa, aguarde...**")
def load_client() -> dict[str, int]:
    load: pd.DataFrame = engine.query(
        sql="""
            SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
            FROM DB2AEB.PRM_EMP t1 INNER JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_EMT
            WHERE t1.DT_ECR_CTR IS NULL
            ORDER BY STRIP(t2.NOM)
        """,
        show_spinner=False,
        ttl=0
    )
    return {k: v for k, v in zip(load["nom"].to_list(), load["mci"].to_list())}


def load_empresa(_mci: int, _data_ant: date, _data_atual: date) -> pd.DataFrame:
    return engine.query(
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
                            ELSE LPAD(CAST(t8.NR_CPF_CNPJ_INVR AS BIGINT), 11, '0')
                        END
                END AS CPF_CNPJ,
                t5.CD_TIP_TIT AS COD_TITULO,
                CONCAT(STRIP(t7.SG_TIP_TIT), STRIP(t7.CD_CLS_TIP_TIT)) AS SIGLA,
                CAST(t5.QUANTIDADE AS BIGINT) AS QTD,
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
                )
            ) t5
                LEFT JOIN DB2MCI.CLIENTE t6
                    ON t6.COD = t5.CD_CLI_ACNT
                LEFT JOIN DB2AEB.TIP_TIT t7
                    ON t7.CD_TIP_TIT = t5.CD_TIP_TIT
                LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                    ON t8.CD_CLI_ACNT = t5.CD_CLI_ACNT
            WHERE
                DATA BETWEEN :data_ant AND :data_atual AND
                t5.CD_CLI_ACNT NOT IN (:mci, 205007939)
            ORDER BY
                CAST(t5.CD_CLI_ACNT AS INTEGER),
                DATA DESC
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, data_ant=_data_ant, data_atual=_data_atual)
    )


def load_cadastro(_mci: int) -> tuple[str, ...]:
    load: pd.DataFrame = engine.query(
        sql="""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                STRIP(t2.NOM) AS EMPRESA,
                LPAD(t2.COD_CPF_CGC, 14, '0') AS CNPJ
            FROM
                DB2AEB.PRM_EMP t1
                INNER JOIN DB2MCI.CLIENTE t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.CD_CLI_EMT = :mci
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci)
    )

    return str(load["mci"].iloc[0]), load["empresa"].iloc[0], load["cnpj"].iloc[0]


@st.dialog("Despachar E-mail")
def send_mail():
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
            <div>Prezados(as),<br><br>
            Segue <b> em anexo </b> Declaração de Maiores Investidores.
            </div>
            <br><br>
            </body></html>""",
            "html"
        ))

        part = MIMEBase("application", "octet-stream")

        with open(f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-"
                  f"{st.session_state['empresa'].replace('/', '.')}-MaioresAcionistasPercentuais.pdf", "rb") as r:
            payload: bytes = r.read()

        part.set_payload(payload)

        encoders.encode_base64(part)

        part.add_header("Content-Disposition", "attachment; filename='maiores_investidores.pdf'")

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
            save_protocol.write(f"{date.today().year}-{last_protocol}-MaioresInvestidores - {nome_empresa}")

        st.rerun()


with open("static/arquivos/protocolador/protocolador.txt") as f:
    last_protocol: int = int([x.strip().split("-") for x in f.readlines()][-1][1]) + 1

st.markdown(f"Protocolo: **{date.today().year}** / DIEST: **{last_protocol}**")

kv: dict[str, int] = load_client()

st.columns(2)[0].selectbox("**Clientes Ativos:**", options=kv.keys(), key="empresa")

mci: int = kv.get(st.session_state["empresa"])

col1, col2, _ = st.columns([1, 0.9, 5.1])
col1.date_input("**Data:**", key="data", format="DD/MM/YYYY")
col2.number_input("**Percentual:**", min_value=1.0, max_value=100.0, value=5.0, step=0.5, key="percentual")

col1, col2, *_ = st.columns(6)
col1.button("**Montar Declaração**", key="montar", type="primary", icon=":material/picture_as_pdf:")
col2.button("**Preparar E-mail**", key="open_mail", type="primary", icon=":material/mail:", use_container_width=True)

if st.session_state["montar"]:
    with st.spinner("**:material/hourglass: Preparando a declaração, aguarde...**", show_time=True):
        reportlab.rl_config.warnOnMissingFontGlyphs = 0

        pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
        pdfmetrics.registerFont(TTFont("VeraBd", "VeraBd.ttf"))
        pdfmetrics.registerFont(TTFont("VeraIt", "VeraIt.ttf"))
        pdfmetrics.registerFont(TTFont("VeraBI", "VeraBI.ttf"))

        data_ant: date = (st.session_state["data"].replace(day=1) - timedelta(days=1)).replace(day=28)

        base: pd.DataFrame = load_empresa(mci, data_ant, st.session_state["data"]) \
            .rename(columns={"investidor": "INVESTIDOR", "cpf_cnpj": "CPF_CNPJ", "sigla": "SIGLA", "qtd": "QTD"})

        if base.empty:
            message.info("**Não há dados para montar a declaração...**", icon=":material/error:", width=600)
            st.stop()

        base["pk"] = base.apply(lambda x: f"{x['mci']}-{x['cod_titulo']}-{x['custodiante']}", axis=1)
        base = base.groupby("pk").first()
        base = base[base["QTD"].ne(0)]
        base["%"] = np.trunc(base["QTD"] / sum(base["QTD"]) * 100)
        base.drop(["mci", "cod_titulo", "custodiante"], axis=1, inplace=True)

        if len(base["SIGLA"].unique()) == 1:
            base.pop("SIGLA")
            base = base.groupby("CPF_CNPJ").agg({"INVESTIDOR": "first", "CPF_CNPJ": "first", "QTD": "sum", "%": "sum"})

        else:
            base = base.groupby(["CPF_CNPJ", "SIGLA"]).agg({"INVESTIDOR": "first", "CPF_CNPJ": "first",
                                                            "SIGLA": "first", "QTD": "sum", "%": "sum"})

        base = base.sort_values(["QTD"], ascending=False)
        base = base[base["%"].ge(st.session_state["percentual"])]

        # definindo estilos que serão usados na carta
        header: ParagraphStyle = ParagraphStyle("header", fontName="Vera", fontSize=11, textColor=colors.black,
                                                aligment="right")
        content: ParagraphStyle = ParagraphStyle("content", fontName="Vera", fontSize=11, textColor=colors.black,
                                                 aligment="justify")
        footer: ParagraphStyle = ParagraphStyle("header", fontName="Vera", fontSize=8, textColor=colors.black)

        mci_empresa, nome_empresa, cnpj_empresa = load_cadastro(mci)

        elements = [
            Image(filename="static/imagens/bb.jpg", width=300, height=38),
            Spacer(30, 30),
            Paragraph(f"Diretoria Operações - {date.today()}/DIEST-{last_protocol}", header),
            Paragraph(f"Rio de Janeiro, {date.today():%d/%m/%Y}", header),
            Spacer(30, 30),
            Paragraph("Ao (À)", header),
            Paragraph(nome_empresa, header),
            Spacer(30, 30),
            Paragraph("Prezados Senhores,", content),
            Spacer(30, 30),
            Paragraph(
                f"O Banco Brasil S.A., Instituição Depositária de Ações Escriturais conforme Ato Declaratório "
                f"nº 4581, de 14/11/1997, da Comissão de Valores Mobiliários - CVM, na execução dos atos relativos "
                f"serviços de escrituração das ações de emissão da empresa {nome_empresa}, cnpj: {cnpj_empresa} "
                f"(emissora) repassa a lista dos acionistas com maior representatividade no capital social total "
                f"ex-tesouraria de emissora em {st.session_state['data']:%d/%m/%Y}.",
                content
            )
        ]

        my_data = base.values.tolist()
        my_data.insert(0, base.columns)

        t: Table = Table(my_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
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
        elements.append(Paragraph("Avenida República do Chile, 330 - 9º andar - Torre Oeste - Centro - Rio"
                                  " de Janeiro RJ", footer))
        elements.append(Paragraph("Telefone: (21) 3808-3715", footer))
        elements.append(Paragraph("Ouvidoria BB - 0800 729 5678", footer))

        pdf: SimpleDocTemplate = SimpleDocTemplate(
            filename=f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-"
                     f"{st.session_state['empresa'].replace('/', '.')}-MaioresAcionistasPercentuais.pdf",
            pagesize=A4
        )
        pdf.build(elements)

        message.info("**Declaração gerada com sucesso! Pode clicar Preparar E-mail**",
                     icon=":material/check_circle:", width=600)

if st.session_state["open_mail"]:
    if os.path.exists(f"static/escriturais/@deletar/{date.today().year}-{last_protocol}-"
                      f"{st.session_state['empresa'].replace('/', '.')}-MaioresAcionistasPercentuais.pdf"):
        send_mail()

    else:
        message.warning("Ainda não, primeiro clicar Montar Declaração...", icon=":material/warning:", width=600)
