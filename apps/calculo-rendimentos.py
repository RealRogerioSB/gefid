import glob
import numpy as np
import pandas as pd
import streamlit as st

st.subheader(":material/calculate: Cálculo de Rendimentos")

st.markdown("##### Os arquivos com a extensão AEBF543A devem ser colocadas na pasta P:\MER\Acoes_Escriturais\@deletar")
st.markdown("##### Certifique-se que não existam outros arquivos com a mesma extensão além daqueles que deseja que "
            "sejam processadas")

if st.button(label="**:material/description: Gerar 543**", type="primary"):
    with st.spinner("**Criando tabela, aguarde...**", show_time=True):
        diretorio_destino = "/mnt/escriturais/@deletar/"
        diretorio_origem = "static/escriturais/@deletar"

        tamanho = 1048000

        # função para retirar pontos e vírgulas dos números para poder trabalhar como float
        def replace_comma_and_dot(_x):
            return _x.replace(".", "").replace(",", "")

        # função para substituir vírgula por ponto para poder trabalhar como float
        def replace_comma_for_dot(_x):
            return _x.replace(",", ".")

        # função para eliminar vírgulas, traços e barras co CPF/CNPJ
        def replace_comma_for_nothing(_x):
            for char in [".", ",", "-", "/"]:
                _x = _x.replace(char, "")
            return _x

        # pegando os arquivos com início "BBM.AEBF543A."
        all_files = glob.glob(f"{diretorio_origem}/*.AEBF543A.*")

        len(all_files)

        # Verificando se achou algum arquivo do tipo no diretório
        if len(all_files) == 0:
            st.toast("**Não foram localizados arquivos 543a no diretório selecionado**", icon=":material/warning:")
            st.stop()
        else:
            # criando a lista
            li = []

            # iterando a leitura do Pandas em todos os arquivos da pasta
            for filename in all_files:
                df = pd.read_fwf(
                    filename,
                    colspecs=[(29, 33), (34, 38), (43, 53), (54, 58), (117, 121), (123, 144), (145, 154),
                              (155, 173), (174, 214), (220, 240), (241, 245), (246, 250), (251, 253),
                              (254, 260), (268, 274), (282, 301), (302, 322), (323, 341), (378, 400),
                              (401, 423)],
                    names=["cod_emissor", "tipo_delib", "data_delib", "direito", "ativo", "valor_por_ativo",
                           "mci_investidor", "cpfcnpj_investidor", "nome_investidor", "forma_pagamento",
                           "pais_bb", "pais_b3", "tipo_pessoa", "faixa_ir_bb", "faixa_ir_b3", "qtd_ativos",
                           "vlr_bruto_bb", "vlr_ir_bb", "vlr_bruto_b3", "vlr_ir_b3"],
                    converters={
                        "cpfcnpj_investidor": replace_comma_for_nothing, "valor_por_ativo": replace_comma_for_dot,
                        "faixa_ir_bb": replace_comma_for_dot, "faixa_ir_b3": replace_comma_for_dot,
                        "qtd_ativos": replace_comma_and_dot, "vlr_bruto_bb": replace_comma_and_dot,
                        "vlr_ir_bb": replace_comma_and_dot, "vlr_bruto_b3": replace_comma_and_dot,
                        "vlr_ir_b3": replace_comma_and_dot
                    },
                    encoding="iso-8859-1"
                )
                li.append(df)

            # concatenando o li
            df = pd.concat(li, axis=0, ignore_index=True, verify_integrity=True)

            # criando lista de títulos
            lista_dir = df["direito"].unique()

            # Verificando se todos os arquivos são do mesmo emissor
            if len(df["cod_emissor"].unique()) > 1:
                st.toast(f"**Identificamos que os arquivos contém dois emissores diferentes "
                         f"{df['cod_emissor'].unique()}.\nTodos os arquivos precisam ser do "
                         f"mesmo emissor.\nIremos encerrar o processo**", icon=":material/warning:")
                st.stop()

            else:
                # convertendo o type de algumas colunas
                df["cpfcnpj_investidor"] = df["cpfcnpj_investidor"].astype(float)
                df["qtd_ativos"] = df["qtd_ativos"].astype(int)
                df["valor_por_ativo"] = df["valor_por_ativo"].astype(float)
                df["faixa_ir_bb"] = df["faixa_ir_bb"].astype(float)
                df["faixa_ir_b3"] = df["faixa_ir_b3"].astype(float)
                df["vlr_bruto_bb"] = df["vlr_bruto_bb"].astype(float)
                df["vlr_ir_bb"] = df["vlr_ir_bb"].astype(float)
                df["vlr_bruto_b3"] = df["vlr_bruto_b3"].astype(float)
                df["vlr_ir_b3"] = df["vlr_ir_b3"].astype(float)

                # pegando o código aeb
                cod_AEB = df.iat[0, 0]

                # Pegando o MCI, nome e CNPJ do emissor
                def dados_emissor(sigla: str) -> tuple[int, int, str, str, str]:
                    global cod_AEB
                    global mci_emissor
                    global nome_emissor
                    global cnpj_emissor
                    global tipo_emissor

                    match sigla.upper():
                        case "AFLU":
                            mci_emissor = 32380485
                            nome_emissor = "Afluente Geração de Energia Elétrica S.A."
                            cnpj_emissor = "07.620.094/0001-40"
                            tipo_emissor = "cia"
                        case "BBSA":
                            mci_emissor = 903485186
                            nome_emissor = "Banco do Brasil S.A."
                            cnpj_emissor = "00.000.000/0001-91"
                            tipo_emissor = "cia"
                        case "BBBR":
                            mci_emissor = 518448409
                            nome_emissor = "BB ETF IBOVESPA Fundo de Índice"
                            cnpj_emissor = "34.606.480/0001-50"
                            tipo_emissor = "fundo"
                        case "AGRI":
                            mci_emissor = 520316230
                            nome_emissor = "BB ETF IAGRO-FFS B3 Fundo de Índice"
                            cnpj_emissor = "45.081.470/0001-65"
                            tipo_emissor = "fundo"
                        case "BBTF":
                            mci_emissor = 511042034
                            nome_emissor = "BB ETF S&P Dividendos Brasil Fundo de Índice"
                            cnpj_emissor = "17.817.528/0001-50"
                            tipo_emissor = "fundo"
                        case "BBFN":
                            mci_emissor = 519093363
                            nome_emissor = "BB FUNDO DE FUNDOS - Fundo de Investimento Imobiliário"
                            cnpj_emissor = "37.180.091/0001-02"
                            tipo_emissor = "fundo"
                        case "BBGO":
                            mci_emissor = 519987114
                            nome_emissor = "BB Fundo de Investimento de Crédito FIAGRO-Imobiliário"
                            cnpj_emissor = "42.592.257/0001-20"
                            tipo_emissor = "fundo"
                        case "BBLS":
                            mci_emissor = 300876574
                            nome_emissor = "BB Leasing S.A. Arrendamento Mercantil"
                            cnpj_emissor = "31.546.476/0001-56"
                            tipo_emissor = "debenture"
                        case "BBRC":
                            mci_emissor = 512957939
                            nome_emissor = "BB Recebíveis Imobiliários Fundo de Investimento Imobiliário"
                            cnpj_emissor = "20.716.161/0001-93"
                            tipo_emissor = "fundo"
                        case "BBSE":
                            mci_emissor = 510636490
                            nome_emissor = "BB Seguridade Participações S.A."
                            cnpj_emissor = "17.344.597/0001-94"
                            tipo_emissor = "cia"
                        case "OIBR":
                            mci_emissor = 700717699
                            nome_emissor = "Oi S.A. - Em Recuperação Judicial"
                            cnpj_emissor = "76.535.764/0001-43"
                            tipo_emissor = "cia"
                        case "ORIZ":
                            mci_emissor = 506064467
                            nome_emissor = "Orizon Valorização de Resíduos S.A."
                            cnpj_emissor = "11.421.994/0001-36"
                            tipo_emissor = "cia"
                        case "IRBR":
                            mci_emissor = 100131376
                            nome_emissor = "IRB - Brasil Resseguros S.A."
                            cnpj_emissor = "33.376.989/0001-91"
                            tipo_emissor = "cia"
                        case "P521":
                            mci_emissor = 902115269
                            nome_emissor = "521 Participações S.A."
                            cnpj_emissor = "01.547.749/0001-16"
                            tipo_emissor = "cia"
                        case "CPFL":
                            mci_emissor = 911469949
                            nome_emissor = "CPFL Energia S.A."
                            cnpj_emissor = "02.429.144/0001-93"
                            tipo_emissor = "cia"
                        case "RPMG":
                            mci_emissor = 100333964
                            nome_emissor = "Refinaria de Petróleos de Manguinhos S.A."
                            cnpj_emissor = "33.412.081/0001-96"
                            tipo_emissor = "cia"
                        case "VLID":
                            mci_emissor = 100281915
                            nome_emissor = "Valid Soluções S.A."
                            cnpj_emissor = "33.113.309/0001-47"
                            tipo_emissor = "cia"
                        case _:
                            cod_AEB = None
                            mci_emissor = None
                            nome_emissor = None
                            cnpj_emissor = None
                            tipo_emissor = None

                    return cod_AEB, mci_emissor, nome_emissor, cnpj_emissor, tipo_emissor

                # Pegando os dados do emissor com o Código do AEB
                dados_emissor(cod_AEB)

                # pegando informações importantes
                tipo_delib = df.iat[0, 1]
                data_base = df.iat[0, 2]

                # criando as colunas finais
                df.insert(12, "pais_final", "")
                df.insert(16, "faixa_ir_final", "")
                df.insert(22, "vlr_bruto_final", "")
                df.insert(23, "vlr_ir_final", "")

                # pegando o país, faixa e valores da bolsa para pagamento em bolsa e pais,
                # faixa e valores do BB para os demais tipos de pagamento
                df.loc[df["forma_pagamento"] == "STR/SISPAG", "pais_final"] = df["pais_b3"]
                df.loc[df["forma_pagamento"] != "STR/SISPAG", "pais_final"] = df["pais_bb"]

                df.loc[df["forma_pagamento"] == "STR/SISPAG", "faixa_ir_final"] = df["faixa_ir_b3"]
                df.loc[df["forma_pagamento"] != "STR/SISPAG", "faixa_ir_final"] = df["faixa_ir_bb"]

                df.loc[df["forma_pagamento"] == "STR/SISPAG", "vlr_bruto_final"] = df["vlr_bruto_b3"]
                df.loc[df["forma_pagamento"] != "STR/SISPAG", "vlr_bruto_final"] = df["vlr_bruto_bb"]

                df.loc[df["forma_pagamento"] == "STR/SISPAG", "vlr_ir_final"] = df["vlr_ir_b3"]
                df.loc[df["forma_pagamento"] != "STR/SISPAG", "vlr_ir_final"] = df["vlr_ir_bb"]

                # criando a coluna de valor líquido final
                df["vlr_liquido_final"] = df["vlr_bruto_final"] - df["vlr_ir_final"]

                # apagando as colunas desnecessárias
                df.drop(["cod_emissor", "tipo_delib", "data_delib", "pais_bb", "pais_b3", "faixa_ir_bb",
                         "faixa_ir_b3", "vlr_bruto_bb", "vlr_bruto_b3", "vlr_ir_bb", "vlr_ir_b3"], axis=1, inplace=True)

                df["vlr_bruto_final"] = df["vlr_bruto_final"] / 100
                df["vlr_ir_final"] = df["vlr_ir_final"] / 100
                df["vlr_liquido_final"] = df["vlr_liquido_final"] / 100

                for x in range(len(lista_dir)):
                    # separando os dataframes por tipo de direito
                    nome_df = f"df{x + 1}"
                    globals()[nome_df] = df[(df["direito"] == str(lista_dir[x]))]

                    # apagando a coluna do direito
                    globals()[nome_df].drop(["direito"], axis=1, inplace=True)

                    # fazendo somatórios importantes
                    vlr_bruto_caixa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CAIXA",
                              ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_caixa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CAIXA",
                              ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_caixa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CAIXA",
                              ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_contacorrentebb = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CONTA-CORRENTE BB",
                              ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_contacorrentebb = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CONTA-CORRENTE BB",
                              ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_contacorrentebb = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CONTA-CORRENTE BB",
                              ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_empresa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "EMPRESA",
                              ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_empresa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "EMPRESA",
                              ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_empresa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "EMPRESA",
                              ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_poupancaourobb = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "POUPANCA OURO BB",
                              ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_poupancaourobb = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "POUPANCA OURO BB",
                              ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_poupancaourobb = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "POUPANCA OURO BB",
                              ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_credtesouronacional = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CRED TESOURO NAC",
                              ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_credtesouronacional = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CRED TESOURO NAC",
                              ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_credtesouronacional = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "CRED TESOURO NAC",
                              ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_strsispag = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "STR/SISPAG",
                              ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_strsispag = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "STR/SISPAG",
                              ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_strsispag = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] == "STR/SISPAG",
                              ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_doctedcustinvest = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DOC/TED CUSTO INVEST", ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_doctedcustinvest = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DOC/TED CUSTO INVEST", ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_doctedcustinvest = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DOC/TED CUSTO INVEST", ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_doctedcustempresa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DOC/TED CUSTO EMPRES", ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_doctedcustempresa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DOC/TED CUSTO EMPRES", ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_doctedcustempresa = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DOC/TED CUSTO EMPRES", ["vlr_liquido_final"]].sum()), 2)
                    vlr_bruto_depositojudicial = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DEPOSITO JUDICIAL EF", ["vlr_bruto_final"]].sum()), 2)
                    vlr_ir_depositojudicial = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DEPOSITO JUDICIAL EF", ["vlr_ir_final"]].sum()), 2)
                    vlr_liquido_depositojudicial = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["forma_pagamento"] ==
                                                           "DEPOSITO JUDICIAL EF", ["vlr_liquido_final"]].sum()), 2)
                    vlr_ir_domestico = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["pais_final"] ==
                                                           105, ["vlr_ir_final"]].sum()), 2)
                    vlr_ir_estrangeiro = \
                        round(float(globals()[nome_df].loc[globals()[nome_df]["pais_final"] !=
                                                           105, ["vlr_ir_final"]].sum()), 2)

                    # dividindo em partes iguais se for maior que o "tamanho"
                    globals()[nome_df] = np.array_split(globals()[nome_df],
                                                        int(len(globals()[nome_df].index) / tamanho) + 1)

                    # Create a Pandas Excel writer using XlsxWriter as the engine.
                    writer = pd.ExcelWriter(f"{diretorio_destino}/Cálculo {lista_dir[x]} {cod_AEB} Base de "
                                            f"{data_base}.xlsx", engine="xlsxwriter")

                    # criando o workbook e worksheets na engine xlsxwriter
                    workbook = writer.book

                    # criando um df vazio para colar na primeira planilha
                    dft = pd.DataFrame()

                    # colando o df vazio para criar a primeira planilha "Resumo"
                    dft.to_excel(writer, sheet_name="Resumo", startrow=2, header=False, index=False)
                    worksheet = writer.sheets["Resumo"]

                    # criando formatos do xlsxwriter
                    titulo_1 = workbook.add_format(dict(bold=True, align="left", bg_color="#025AA5", right=2,
                                                        font_size=14, font_color="white"))
                    titulo_2 = workbook.add_format(dict(bold=True, align="center", bg_color="#FFED00", border=2,
                                                        font_size=11))
                    titulo_2b = workbook.add_format(dict(bold=True, align="left", bg_color="#465EFF",
                                                         font_color="FCFC30", border=2, font_size=11))
                    titulo_3 = workbook.add_format(dict(bold=True, align="left", bg_color="#025AA5", right=2, bottom=2,
                                                        font_size=14, font_color="white"))

                    total_format = workbook.add_format(dict(bold=True, align="right"))

                    number_format = workbook.add_format(dict(num_format="0"))
                    number_format2 = workbook.add_format(dict(num_format="#,##0"))

                    qtd_format = workbook.add_format(dict(num_format="#,##0"))

                    vlr_format = workbook.add_format(dict(num_format="#,##0.00", align="center", border=1))
                    vlr_format2 = workbook.add_format(dict(num_format="#,##0.00", align="center", bold=True, border=1))
                    vlr_format3 = workbook.add_format(dict(num_format="#,##0.00000000000", align="center"))
                    vlr_format4 = workbook.add_format(dict(num_format="#,##0.00", align="center"))

                    texto_format = workbook.add_format(dict(align="left", border=1))
                    texto_format2 = workbook.add_format(dict(align="left", bold=True, border=1))
                    texto_format3 = workbook.add_format(dict(align="left", bg_color="#465EFF", font_color="#FCFC30",
                                                             bold=True, border=1))
                    texto_format4 = workbook.add_format(dict(align="center", bg_color="#465EFF", font_color="FCFC30",
                                                             bold=True, border=1))
                    texto_format5 = workbook.add_format(dict(align="left", bg_color="#DCA09B", bold=True, border=1))

                    # formatando colunas (largura e número)
                    worksheet.set_column(0, 0, 24)
                    worksheet.set_column(1, 3, 18)

                    # montando o leiaute do resumo
                    worksheet.write("A1", "Emissor", texto_format3)
                    worksheet.write("A2", "Tipo de Deliberação", texto_format3)
                    worksheet.write("A3", "Tipo de Direito", texto_format3)
                    worksheet.write("A4", "Data Base", texto_format3)
                    worksheet.write("A5", "Data de Pagamento", texto_format3)

                    worksheet.write("A7", "Forma de Pagamento", texto_format3)
                    worksheet.write("B7", "Valor Bruto", texto_format4)
                    worksheet.write("C7", "Valor de IR", texto_format4)
                    worksheet.write("D7", "Valor Líquido", texto_format4)
                    worksheet.write("A8", "CAIXA", texto_format)
                    worksheet.write("A9", "CONTA-CORRENTE BB", texto_format)
                    worksheet.write("A10", "EMPRESA", texto_format)
                    worksheet.write("A11", "POUPANÇA OURO BB", texto_format)
                    worksheet.write("A12", "CRED TESOURO NACIONAL", texto_format)
                    worksheet.write("A13", "STR/SISPAG", texto_format)
                    worksheet.write("A14", "DOC/TED", texto_format)
                    worksheet.write("A15", "DEPÓSITO JUDICIAL", texto_format)
                    worksheet.write("A16", "TOTAL", texto_format2)

                    # escrevendo as variáveis na planilha
                    worksheet.merge_range("B1:D1", nome_emissor, texto_format2)

                    if tipo_delib == 1:
                        worksheet.merge_range("B2:D2", "AGE", texto_format2)
                    elif tipo_delib == 2:
                        worksheet.merge_range("B2:D2", "AGO", texto_format2)
                    elif tipo_delib == 3:
                        worksheet.merge_range("B2:D2", "RCA", texto_format2)
                    elif tipo_delib == 8:
                        worksheet.merge_range("B2:D2", "FATO RELEVANTE", texto_format2)
                    elif tipo_delib == 9:
                        worksheet.merge_range("B2:D2", "REGULAMENTO DO FUNDO", texto_format2)
                    else:
                        worksheet.merge_range("B2:D2", "OUTROS", texto_format2)

                    worksheet.merge_range("B3:D3", lista_dir[x], texto_format2)
                    worksheet.merge_range("B4:D4", data_base.replace(".", "/"), texto_format2)
                    worksheet.merge_range("B5:D5", "", texto_format5)

                    # escrevendo valores
                    worksheet.write("B8", vlr_bruto_caixa, vlr_format)
                    worksheet.write("C8", vlr_ir_caixa, vlr_format)
                    worksheet.write("D8", vlr_liquido_caixa, vlr_format)

                    worksheet.write("B9", vlr_bruto_contacorrentebb, vlr_format)
                    worksheet.write("C9", vlr_ir_contacorrentebb, vlr_format)
                    worksheet.write("D9", vlr_liquido_contacorrentebb, vlr_format)

                    worksheet.write("B10", vlr_bruto_empresa, vlr_format)
                    worksheet.write("C10", vlr_ir_empresa, vlr_format)
                    worksheet.write("D10", vlr_liquido_empresa, vlr_format)

                    worksheet.write("B11", vlr_bruto_poupancaourobb, vlr_format)
                    worksheet.write("C11", vlr_ir_poupancaourobb, vlr_format)
                    worksheet.write("D11", vlr_liquido_poupancaourobb, vlr_format)

                    worksheet.write("B12", vlr_bruto_credtesouronacional, vlr_format)
                    worksheet.write("C12", vlr_ir_credtesouronacional, vlr_format)
                    worksheet.write("D12", vlr_liquido_credtesouronacional, vlr_format)

                    worksheet.write("B13", vlr_bruto_strsispag, vlr_format)
                    worksheet.write("C13", vlr_ir_strsispag, vlr_format)
                    worksheet.write("D13", vlr_liquido_strsispag, vlr_format)

                    worksheet.write("B14", vlr_bruto_doctedcustinvest + vlr_bruto_doctedcustempresa, vlr_format)
                    worksheet.write("C14", vlr_ir_doctedcustinvest + vlr_ir_doctedcustempresa, vlr_format)
                    worksheet.write("D14", vlr_liquido_doctedcustinvest + vlr_liquido_doctedcustempresa, vlr_format)

                    worksheet.write("B15", vlr_bruto_depositojudicial, vlr_format)
                    worksheet.write("C15", vlr_ir_depositojudicial, vlr_format)
                    worksheet.write("D15", vlr_liquido_depositojudicial, vlr_format)

                    worksheet.write_formula(15, 1, "=SUM(B8:B15)", vlr_format2)
                    worksheet.write_formula(15, 2, "=SUM(C8:C15)", vlr_format2)
                    worksheet.write_formula(15, 3, "=SUM(D8:D15)", vlr_format2)

                    # colocando as informações de estrangeiros para os fundos
                    if tipo_emissor == "fundo":
                        worksheet.write("A18", "Tipo de Investidor", texto_format3)
                        worksheet.write("B18", "Total de IR", texto_format4)
                        worksheet.write("A19", "DOMÉSTICO", texto_format)
                        worksheet.write("A20", "ESTRANGEIRO", texto_format)
                        worksheet.write("A21", "TOTAL", texto_format2)
                        worksheet.write("B19", vlr_ir_domestico, vlr_format)
                        worksheet.write("B20", vlr_ir_estrangeiro, vlr_format)
                        worksheet.write_formula(20, 1, "=SUM(B19:B20)", vlr_format2)

                    # colando o df nas demais planilhas
                    for i in range(len(globals()[nome_df])):
                        globals()[nome_df][i].to_excel(writer, sheet_name=str(i + 1),
                                                       startrow=2, header=False, index=False)

                    for i in range(len(globals()[nome_df])):
                        # separando os dataframes por tipo de direito
                        nome_sheet = f"worksheet{i + 1}"

                        globals()[nome_sheet] = writer.sheets[str(i + 1)]
                        globals()[nome_sheet].set_column(0, 0, 5)
                        globals()[nome_sheet].set_column(1, 1, 14, vlr_format3)
                        globals()[nome_sheet].set_column(2, 2, 12, number_format)
                        globals()[nome_sheet].set_column(3, 3, 18, number_format)
                        globals()[nome_sheet].set_column(4, 4, 50)
                        globals()[nome_sheet].set_column(5, 5, 20)
                        globals()[nome_sheet].set_column(6, 6, 4)
                        globals()[nome_sheet].set_column(7, 7, 3)
                        globals()[nome_sheet].set_column(8, 8, 5, vlr_format4)
                        globals()[nome_sheet].set_column(9, 9, 12, number_format2)
                        globals()[nome_sheet].set_column(10, 12, 16, vlr_format4)

                        # escrevendo os cabeçalhos da primeira planilha
                        globals()[nome_sheet].write("A2", "Ativo", titulo_2b)
                        globals()[nome_sheet].write("B2", "R$/Ativo", titulo_2b)
                        globals()[nome_sheet].write("C2", "Cod. investidor", titulo_2b)
                        globals()[nome_sheet].write("D2", "CPF/CNPJ", titulo_2b)
                        globals()[nome_sheet].write("E2", "Nome", titulo_2b)
                        globals()[nome_sheet].write("F2", "Forma de Pag.", titulo_2b)
                        globals()[nome_sheet].write("G2", "País", titulo_2b)
                        globals()[nome_sheet].write("H2", "Tipo Invest.", titulo_2b)
                        globals()[nome_sheet].write("I2", "Faixa IR", titulo_2b)
                        globals()[nome_sheet].write("J2", "Qtd Ativos", titulo_2b)
                        globals()[nome_sheet].write("K2", "Vlr Bruto", titulo_2b)
                        globals()[nome_sheet].write("L2", "Vlr IR", titulo_2b)
                        globals()[nome_sheet].write("M2", "Vlr Líquido", titulo_2b)

                        # criando filtro
                        globals()[nome_sheet].autofilter(1, 0, 1, 12)

                        # Congelando as primeiras 5/2 linhas
                        globals()[nome_sheet].freeze_panes(2, 0)

                        # fazendo o somatório
                        globals()[nome_sheet].write_formula(0, 10, f"=SUBTOTAL(9,K3:K"
                                                                   f"{len(globals()[nome_df][i].index) + 2})",
                                                            vlr_format2)
                        globals()[nome_sheet].write_formula(0, 11, f"=SUBTOTAL(9,L3:L"
                                                                   f"{len(globals()[nome_df][i].index) + 2})",
                                                            vlr_format2)
                        globals()[nome_sheet].write_formula(0, 12, f"=SUBTOTAL(9,M3:M"
                                                                   f"{len(globals()[nome_df][i].index) + 2})",
                                                            vlr_format2)

                    workbook.close()
                    writer.close()

                st.toast("**543 processado com sucesso. Arquivo salvo na mesma pasta de origem**",
                         icon=":material/check_circle:")

st.markdown("""
<style>
    [data-testid='stHeader'] {display: none;}
    #MainMenu {visibility: hidden} footer {visibility: hidden}
</style>
""", unsafe_allow_html=True)
