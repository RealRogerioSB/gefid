import locale
import smtplib
from datetime import date, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import reportlab.rl_config
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from streamlit.connections import SQLConnection

locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")

st.cache_data.clear()

if "state_selectbox" not in st.session_state:
    st.session_state["state_selectbox"] = True


def state():
    st.session_state["state_selectbox"] = True


engine: SQLConnection = st.connection(name="DB2", type=SQLConnection)

st.markdown("##### :material/bar_chart_4_bars: Declaração de Ações em Tesouraria")

with open("static/arquivos/protocolador/protocolador.txt") as f:
    ultimo_protocolo = int([x.strip().split("-") for x in f.readlines()][-1][1]) + 1

st.markdown(f"Protocolo: **{date.today().year}** / DIEST: **{ultimo_protocolo}**")


@st.cache_data(show_spinner=False)
def load_client() -> dict[int, str]:
    load: pd.DataFrame = engine.query(
        sql="""
        SELECT t1.CD_CLI_EMT AS MCI, STRIP(t2.NOM) AS NOM
        FROM DB2AEB.PRM_EMP t1 INNER JOIN DB2MCI.CLIENTE t2 ON t2.COD = t1.CD_CLI_EMT
        WHERE t1.DT_ECR_CTR IS NULL
        ORDER BY STRIP(t2.NOM)
        """,
        show_spinner="**:material/hourglass: Preparando a listagem da empresa, aguarde...**",
        ttl=0
    )
    return {k: v for k, v in zip(load["mci"].to_list(), load["nom"].to_list())}


@st.cache_data(show_spinner=False)
def load_empresa(_mci: int, _data_ant: date, _data_atual: date) -> pd.DataFrame:
    return engine.query(
        sql="""
        SELECT
            t5.CD_CLI_ACNT AS MCI,
            STRIP(CASE
                WHEN t5.CD_CLI_ACNT < 1000000000 THEN t6.NOM
                ELSE t8.NM_INVR
            END) AS INVESTIDOR,
            LPAD(CASE
                WHEN t5.CD_CLI_ACNT < 1000000000 THEN CAST(t6.COD_CPF_CGC AS BIGINT)
                ELSE CAST(t8.NR_CPF_CNPJ_INVR AS BIGINT)
            END, 14, '0') AS CPF_CNPJ,
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


with st.columns(2)[0]:
    kv: dict[int, str] = load_client()

    st.selectbox(label="**Empresa:**", options=kv.values(), key="empresa", on_change=state)

    mci: int = next((chave for chave, valor in kv.items() if valor == st.session_state["empresa"]), 0)

    st.columns(3)[0].date_input("**Data:**", value=date.today(), key="data", format="DD/MM/YYYY")

    st.button("**Montar Declaração**", key="montar", type="primary", icon=":material/picture_as_pdf:")

    st.text_input("Para:", key="to_addrs", placeholder="Digite o e-mail de destinatário",
                  help="Mais e-mails, coloca a vírgula", disabled=st.session_state["state_selectbox"])

    st.text_input("CC:", key="cc_addrs", placeholder="Digite o e-mail de destinatário",
                  help="Mais e-mails, coloca a vírgula", disabled=st.session_state["state_selectbox"])

    st.button("**Enviar Declaração por E-mail**", key="enviar", type="primary", icon=":material/send:",
              disabled=st.session_state["state_selectbox"])

if st.session_state["montar"]:
    with st.spinner("**:material/hourglass: Preparando os dados para a declaração, aguarde...**", show_time=True):
        data_ant: date = (st.session_state["data"].replace(day=1) - timedelta(days=1)).replace(day=28)

        office: pd.DataFrame = load_empresa(mci, data_ant, st.session_state["data"])

        if not office.empty:
            # office["pk"] = f"{office['mci']}-{office['cod_titulo']}-{office['custodiante']}"
            # office = office.groupby("pk").first()
            office = office[office["quantidade"].ne(0)]

            reportlab.rl_config.warnOnMissingFontGlyphs = 0

            pdfmetrics.registerFont(TTFont("VeraBI", "VeraBI.ttf"))
            pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
            pdfmetrics.registerFont(TTFont("VeraBd", "VeraBd.ttf"))
            pdfmetrics.registerFont(TTFont("VeraIt", "VeraIt.ttf"))

            cnv: canvas.Canvas = canvas.Canvas(
                filename=f"static/escriturais/@deletar/AcoesEmTesouraria-{st.session_state['empresa']} - "
                         f"{st.session_state['data']:%d.%m.%Y}.pdf",
                pagesize=A4
            )
            cnv.drawImage("static/imagens/bb.jpg", 40, 780, 300, 38)
            cnv.setFont("Vera", 11)
            cnv.drawString(330, 750, f"Diretoria Operações - {date.today().year}/DIEST-{ultimo_protocolo}")
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

            cnpj: int = office["cpf_cnpj"].iloc[0]

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

            st.toast("**Declaração de Ações em Tesouraria gerada com sucesso! Favor preencher e-mails.**",
                     icon=":material/check_circle:")

            st.session_state["state_selectbox"] = False
            st.rerun()

        else:
            st.toast("**Não identificamos ações em tesouraria para o referido cliente**", icon=":material/warning:")

if st.session_state["enviar"]:
    if not any([st.session_state["to_addrs"], st.session_state["cc_addrs"]]):
        st.toast("**É obrigatório preencher um dos campos de e-mail**", icon=":material/warning:")
        st.stop()

    with st.spinner("**:material/hourglass: Preparando para enviar e-mail, aguarde...**", show_time=True):
        from_addr: str = "aescriturais@bb.com.br"
        to_addrs: list[str] = st.session_state["to_addrs"].replace(" ", "").split(",")
        cc_addrs: list[str] = st.session_state["cc_addrs"].replace(" ", "").split(",")

        msg: MIMEMultipart = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)
        msg["Cc"] = ", ".join(cc_addrs)
        msg["Subject"] = "DECLARAÇÃO AÇÕES EM TESOURARIA"
        msg.attach(MIMEText(
            """<html>
                    <head></head>
                    <body>
                        <br><br>
                        <div>Prezados,<br><br>
                        Segue <b>em anexo</b> Declaração de Ações em Tesouraria</div>
                        <br><br>
                    </body>
                </html>""",
            "html"
        ))

        part: MIMEBase = MIMEBase("application", "octet-stream")

        arquivo: str = (f"static/escriturais/@deletar/AcoesEmTesouraria-{st.session_state['empresa']} - "
                        f"{st.session_state['data']:%d.%m.%Y}.pdf")

        with open(arquivo, "rb") as f:
            payload: bytes = f.read()

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
                server.sendmail(from_addr, to_addrs + cc_addrs, msg.as_string())

            except smtplib.SMTPException:
                st.toast("**Falha ao enviar e-mail...**", icon=":material/error:")

            else:
                with open("static/arquivos/protocolador/protocolador.txt", "a") as save_protocol:
                    save_protocol.write("\n")
                    save_protocol.write(f"{date.today().year}-{ultimo_protocolo}-Protocolo Ações em "
                                        f"Tesouraria-{st.session_state['empresa']}")

                st.toast("**E-mail enviado com sucesso!**", icon=":material/check_circle:")

                st.session_state["state_selectbox"] = True
                st.rerun()
