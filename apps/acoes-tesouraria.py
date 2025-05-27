import locale
import os
import smtplib
from datetime import date, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPConnectError, SMTPServerDisconnected

import pandas as pd
import reportlab.rl_config
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from streamlit.connections import SQLConnection

locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")

engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)


@st.cache_data(show_spinner="**:material/hourglass: Preparando a listagem da empresa, aguarde...**")
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
                END)  AS INVESTIDOR,
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
                t5.DATA AS DATA,
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
                        t1.CD_CLI_EMT = :mci AND
                        t1.CD_CLI_ACNT = :mci
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
                        t1.CD_CLI_EMT = :mci AND
                        t1.CD_CLI_ACNT = :mci
                )
            ) t5
            LEFT JOIN DB2MCI.CLIENTE t6
                ON t6.COD = t5.CD_CLI_ACNT
            LEFT JOIN DB2AEB.TIP_TIT t7
                ON t7.CD_TIP_TIT = t5.CD_TIP_TIT
            LEFT JOIN DB2AEB.VCL_ACNT_BLS t8
                ON t8.CD_CLI_ACNT = t5.CD_CLI_ACNT
            WHERE
                data BETWEEN :data_ant AND :data_atual
            ORDER BY
                CAST(t5.CD_CLI_ACNT AS INTEGER),
                data DESC
        """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci, data_ant=_data_ant, data_atual=_data_atual)
    )


@st.dialog("Despachar E-mail")
def send_mail() -> None:
    st.text_input("**Para:**", key="to_addr", help="Mais e-mails, coloca a vírgula", icon=":material/mail:")
    st.text_input("**Cc:**", key="cc_addr", help="Mais e-mails, coloca a vírgula", icon=":material/mail:")
    st.columns(3)[1].button("Despachar", key="despachar", type="primary", icon=":material/send:",
                            use_container_width=True)

    if st.session_state["despachar"]:
        if not any([st.session_state["to_addr"], st.session_state["cc_addr"]]):
            st.stop()

        msg: MIMEMultipart = MIMEMultipart()
        msg["From"] = "aescriturais@bb.com.br"
        msg["To"] = st.session_state["to_addr"]
        msg["Cc"] = st.session_state["cc_addr"]
        msg["Subject"] = "DECLARAÇÃO AÇÕES EM TESOURARIA"
        msg.attach(MIMEText(
            """<html><head></head><body><br><br>
            <div>
                Prezados,<br><br>
                Segue <b>em anexo</b> Declaração de Ações em Tesouraria
            </div>
            <br><br></body></html>""",
            "html"
        ))

        part: MIMEBase = MIMEBase("application", "octet-stream")

        with open(f"static/escriturais/@deletar/AcoesEmTesouraria-{st.session_state['empresa'].replace('/', '.')} - "
                  f"{st.session_state['data']:%d.%m.%Y}.pdf", "rb") as file:
            payload: bytes = file.read()

        part.set_payload(payload)

        encoders.encode_base64(part)

        part.add_header(
            "Content-Disposition",
            "attachment; filename='acoesemtesouraria.pdf'"
        )

        msg.attach(part)

        with smtplib.SMTP("smtp.bb.com.br") as server:
            server.set_debuglevel(1)
            try:
                server.sendmail(
                    from_addr="aescriturais@bb.com.br",
                    to_addrs=st.session_state["to_addr"] + st.session_state["cc_addr"],
                    msg=msg.as_string()
                )

            except (SMTPConnectError, SMTPServerDisconnected):
                st.toast("###### Falha ao conectar o serviço de e-mail...", icon=":material/error:")

            else:
                with open("static/arquivos/protocolador/protocolador.txt", "a") as save_protocol:
                    save_protocol.write("\n")
                    save_protocol.write(f"{date.today().year}-{last_protocol}-Protocolo Ações em Tesouraria-"
                                        f"{st.session_state['empresa']}")

                st.session_state["addr_mail"] = None

                st.toast("###### E-mail enviado com sucesso!", icon=":material/check_circle:")


st.markdown("##### :material/bar_chart_4_bars: Declaração de Ações em Tesouraria")

with open("static/arquivos/protocolador/protocolador.txt") as f:
    last_protocol: int = int([x.strip().split("-") for x in f.readlines()][-1][1]) + 1

st.markdown(f"Protocolo: **{date.today().year}** / DIEST: **{last_protocol}**")

with st.columns(2)[0]:
    kv: dict[str, int] = load_client()

    st.selectbox(label="**Empresa:**", options=kv.keys(), key="empresa")

    mci: int = kv.get(st.session_state["empresa"])

    st.columns(3)[0].date_input("**Data:**", value=date.today(), key="data", format="DD/MM/YYYY")

col1, col2, *_ = st.columns(6)
col1.button("**Montar Declaração**", key="montar", type="primary",
            icon=":material/picture_as_pdf:", use_container_width=True)
col2.button("**Preparar E-mail**", key="open_mail", type="primary", icon=":material/mail:", use_container_width=True)

if st.session_state["montar"]:
    with st.spinner("**:material/hourglass: Preparando os dados para a declaração, aguarde...**", show_time=True):
        data_ant: date = (st.session_state["data"].replace(day=1) - timedelta(days=1)).replace(day=28)

        office: pd.DataFrame = load_empresa(mci, data_ant, st.session_state["data"])
        office["pk"] = office.apply(lambda x: f"{x['mci']}-{x['cod_titulo']}-{x['custodiante']}", axis=1)
        office = office.groupby(["pk"]).first()
        office = office[office["quantidade"].ne(0)]

        if office.empty:
            st.toast("###### Não identificamos ações em tesouraria para a referida empresa", icon=":material/error:")

        else:
            reportlab.rl_config.warnOnMissingFontGlyphs = 0

            pdfmetrics.registerFont(TTFont("VeraBI", "VeraBI.ttf"))
            pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
            pdfmetrics.registerFont(TTFont("VeraBd", "VeraBd.ttf"))
            pdfmetrics.registerFont(TTFont("VeraIt", "VeraIt.ttf"))

            cnv: canvas.Canvas = canvas.Canvas(
                filename=f"static/escriturais/@deletar/AcoesEmTesouraria-"
                         f"{st.session_state['empresa'].replace('/', '.')} - {st.session_state['data']:%d.%m.%Y}.pdf",
                pagesize=A4
            )
            cnv.drawImage("static/imagens/bb.jpg", 40, 780, 300, 38)
            cnv.setFont("Vera", 11)
            cnv.drawString(330, 750, f"Diretoria Operações - {date.today().year}/DIEST-{last_protocol}")
            cnv.drawString(330, 730, f"Rio de Janeiro, {date.today():%d de %B de %Y}")
            cnv.drawString(40, 680, "Prezados Senhores,")
            cnv.drawString(40, 650, f"O Banco Brasil S.A., Instituição Depositária de Ações Escriturais "
                                    f"conforme Ato Declaratório")
            cnv.drawString(40, 635, f"nº 4581, de 14/11/1997, da Comissão de Valores Mobiliários - CVM, "
                                    f"na execução dos atos")
            cnv.drawString(40, 620, f"relativos aos serviços de escrituração das ações de emissão da "
                                    f"empresa abaixo informa a")
            cnv.drawString(40, 605, f"quantidade de ativos na tesouraria no ambiente escritural (Livro) "
                                    f"em {st.session_state['data']:%d/%m/%Y}.")

            cnpj: str = office["cpf_cnpj"].iloc[0]

            cnv.drawString(40, 575, f"Razão Social: {st.session_state['empresa']}")
            cnv.drawString(40, 560, f"CNPJ: {cnpj}")

            y: int = 0
            for x in office.index:
                cnv.drawString(40, 530 - y, f"Tipo: {list(office['sigla'].loc[office.index == x])[0]}"
                                            f" {list(office['custodiante'].loc[office.index == x])[0]}")
                cnv.drawString(40, 515 - y, f"Saldo: {list(office['quantidade'].loc[office.index == x])[0]}")
                y += 45

            cnv.setFont("Vera", 8)
            cnv.drawString(40, 90, "_" * 129)
            cnv.drawString(40, 75, "DIRETORIA OPERAÇÕES - DIOPE")
            cnv.drawString(40, 60, "Gerência Executiva de Negócios em Serviços Fiduciários - Gerência de "
                                   "Escrituração e Trustee")
            cnv.drawString(40, 45, "Avenida República do Chile, 330 - 9º andar - Torre Oeste - Centro - "
                                   "Rio de Janeiro RJ")
            cnv.drawString(40, 30, "Telefone: (21) 3808-3715")
            cnv.drawString(40, 15, "Ouvidoria BB - 0800 729 5678")

            cnv.save()

            st.toast("###### Declaração de Ações em Tesouraria gerada com sucesso! Pode clicar Despachar E-mail",
                     icon=":material/check_circle:")

if st.session_state["open_mail"]:
    if os.path.exists(f"static/escriturais/@deletar/AcoesEmTesouraria-{st.session_state['empresa'].replace('/', '.')} "
                      f"- {st.session_state['data']:%d.%m.%Y}.pdf"):
        send_mail()

    else:
        st.toast("###### Ainda não, primeiro clicar Montar Declaração...", icon=":material/warning:")
