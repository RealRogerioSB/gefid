from datetime import date

import pandas as pd
import streamlit as st

st.subheader(":material/diversity_3: EDIV")

st.markdown("#### Separação do EDIV por processos")

st.columns([3, 1])[0].write("##### Os arquivos EDIV e o IRMCI devem ser colocados na pasta "
                            "P:\MER\Acoes_Escriturais\@deletar\ e escolhidos abaixo")

col1, col2, _, _ = st.columns([1, 1, 0.5, 0.5])

up_ediv = col1.file_uploader(label="**Arquivo EDIV:**", help="**Importa o arquivo de EDIV**")

up_irmci = col2.file_uploader(label="**Arquivo IRMCI:**", help="**Importa o arquivo de IRMCI**")

if st.button(label="**:material/content_cut: Separar Processos**", type="primary"):
    if all([up_ediv, up_irmci]):
        # lendo ediv
        dados = pd.read_fwf(up_ediv, colspecs=[(0, 2), (2, 397)], names=["tp_registro", "restante"], encoding="latin")
        # primeiro filtro
        dados = dados[dados["tp_registro"].eq(2)]

        # separando e definindo tipos do df do ediv
        dados["processo"] = dados["restante"].str[:9].astype("int64")
        dados["isin"] = dados["restante"].str[9:21]
        dados["cpf_cnpj"] = dados["restante"].str[21:36].astype("int64")
        dados["nome"] = dados["restante"].str[47:107]
        dados["tp_pessoa"] = dados["restante"].str[107:108]
        dados["tp_cliente"] = dados["restante"].str[108:113].astype("int64")
        dados["pais"] = dados["restante"].str[294:297]
        dados["quantidade"] = dados["restante"].str[333:348].astype("int64")
        dados["valor_bruto"] = dados["restante"].str[351:369].astype("int64")
        dados["valor_liquido"] = dados["restante"].str[369:387].astype("int64")
        dados["evento"] = dados["restante"].str[393:394].astype("int64")
        dados["percent_ir"] = dados["restante"].str[387:392].astype("int64")

        # removendo os espaços na frente e atrás do nome
        dados_obj = dados.select_dtypes(["object"])
        dados[dados_obj.columns] = dados_obj.apply(lambda w: w.str.strip())

        # lendo IRMCI
        dfirmci = pd.read_fwf(up_irmci, colspecs=[(145, 152), (0, 15), (75, 89)],
                              names=["processo", "cpf_cnpj", "irmci"], encoding="latin")

        # definindo tipos do df do irmci
        dfirmci["processo"] = dfirmci["processo"].astype("int64")
        dfirmci["cpf_cnpj"] = dfirmci["cpf_cnpj"].astype("int64")

        # juntando dataframes
        df = pd.merge(dados, dfirmci, on=["cpf_cnpj", "processo"])

        # colocando na potenciação correta
        df["valor_bruto"] = df["valor_bruto"] / 100
        df["valor_liquido"] = df["valor_liquido"] / 100
        df["percent_ir"] = df["percent_ir"] / 100

        # apagando as colunas desnecessárias
        df.drop(["tp_registro", "restante"], axis=1, inplace=True)

        # incluindo a coluna de paraíso fiscal
        df.insert(7, "Paraiso?", '')

        # criando lista de países paraísos fiscais
        lista = [
            "ABW", "AIA", "AND", "ARE", "ASM", "ATG", "BHR", "BHS", "BLZ", "BMU", "BRB", "BRN", "COK", "CYM",
            "DJI", "DMA", "GGY", "GGY", "GIB", "GRD", "HKG", "IRL", "JEY", "JEY", "KIR", "LBN", "LBR", "LCA",
            "LIE", "MAC", "MDV", "MHL", "MSR", "MUS", "NFK", "NIU", "OMN", "PAN", "PNC", "PYF", "SHN", "SLB",
            "SPM", "SYC", "TON", "VCT", "VGB", "VIR", "VUT", "WSM"
        ]

        # criando lista de países paraísos fiscais
        df.loc[df["pais"].isin(lista), "Paraiso?"] = "Sim"
        df.loc[~df["pais"].isin(lista), "Paraiso?"] = "Não"

        # criando lista de processos
        lista_processos = df["processo"].unique()

        # incluindo a coluna de edvi_ant e irmci
        df.insert(12, "ediv_ant", '')

        df = df[["processo", "isin", "cpf_cnpj", "nome", "tp_pessoa", "tp_cliente", "pais", "Paraiso?", "quantidade",
                 "valor_bruto", "valor_liquido", "evento", "irmci", "ediv_ant", "percent_ir"]]

        # pegando a data de hoje
        today = str(date.today()).replace("-", '')

        for x in range(len(lista_processos)):
            # separando os dataframes por processos
            nome_df = f"df{x + 1}"
            globals()[nome_df] = df[(df["processo"].eq(lista_processos[x]))]

            # apagando a coluna de processo
            globals()[nome_df].drop(["processo"], axis=1, inplace=True)

            # pegando o ISIN
            isin = globals()[nome_df].iat[0, 0]

            # apagando a coluna de ISIN
            globals()[nome_df].drop(["isin"], axis=1, inplace=True)

            # Criando a engine usando XlsxWriter com o Pandas.
            writer = pd.ExcelWriter(f"static/escriturais/@deletar/EDIV {isin[2:6]} {str(lista_processos[x])} "
                                    f"{today}.xlsx", engine="xlsxwriter")

            # criando o workbook e worksheets na engine xlsxwriter
            workbook = writer.book

            # colando o df para criar a primeira planilha "Resumo"
            globals()[nome_df].to_excel(writer, sheet_name="Analítico", startrow=2, header=False, index=False,
                                        engine="xlsxwriter")

            # criando formatos do xlsxwriter
            number_format = workbook.add_format(dict(num_format="0", align="center"))

            text_format = workbook.add_format(dict(align="center"))
            text_format2 = workbook.add_format(dict(align="left", bold=True))
            text_format3 = workbook.add_format(dict(align="left", bg_color="#465EFF", font_color="#FCFC30", bold=True))
            text_format4 = workbook.add_format(dict(align="center", bg_color="#465EFF", font_color="FCFC30", bold=True))

            qtd_format = workbook.add_format(dict(num_format="#,##0", align="center"))
            qtd_format2 = workbook.add_format(dict(num_format="#,##0", align="center", bold=True))

            vlr_format = workbook.add_format(dict(num_format="#,##0.00", align="center"))
            vlr_format2 = workbook.add_format(dict(num_format="#,##0.00", align="center", bold=True))

            # estilizando as colunas
            worksheet = writer.sheets["Analítico"]

            worksheet.set_column(0, 0, 16, number_format)
            worksheet.set_column(1, 1, 67)
            worksheet.set_column(2, 2, 4, text_format)
            worksheet.set_column(3, 3, 6, number_format)
            worksheet.set_column(4, 4, 4.5, text_format)
            worksheet.set_column(5, 5, 8, text_format)
            worksheet.set_column(6, 6, 16, qtd_format)
            worksheet.set_column(7, 8, 16, vlr_format)
            worksheet.set_column(9, 9, 5, text_format)
            worksheet.set_column(10, 10, 17, text_format)
            worksheet.set_column(11, 13, 9, vlr_format)

            # montando o cabeçalho
            worksheet.merge_range("A1:B1", f"Processo  {str(lista_processos[x])}     ISIN  {isin}", text_format2)
            worksheet.write("A2", "CPF/CNPJ", text_format4)
            worksheet.write("B2", "Nome", text_format4)
            worksheet.write("C2", "Tipo", text_format3)
            worksheet.write("D2", "Classe", text_format3)
            worksheet.write("E2", "País", text_format3)
            worksheet.write("F2", "Paraíso?", text_format3)
            worksheet.write("G2", "Qtd", text_format4)
            worksheet.write("H2", "R$ Bruto", text_format4)
            worksheet.write("I2", "R$ Líquido", text_format4)
            worksheet.write("J2", "Status", text_format3)
            worksheet.write("K2", "IRMCI", text_format4)
            worksheet.write("L2", "EDIV Ant.", text_format3)
            worksheet.write("M2", "% IR B3", text_format3)
            worksheet.write("N2", "Novo % IR", text_format3)

            # fazendo o somatório
            worksheet.write_formula(0, 6, f"=SUBTOTAL(9,G3:G{str(len(globals()[nome_df].index) + 2)})", qtd_format2)
            worksheet.write_formula(0, 7, f"=SUBTOTAL(9,H3:H{str(len(globals()[nome_df].index) + 2)})", vlr_format2)
            worksheet.write_formula(0, 8, f"=SUBTOTAL(9,I3:I{str(len(globals()[nome_df].index) + 2)})", vlr_format2)

            # criando filtro
            worksheet.autofilter(1, 0, 1, 13)

            # Congelando as primeiras 5/2 linhas
            worksheet.freeze_panes(2, 0)

            # criando as outras sheets
            worksheet = workbook.add_worksheet("Alterações")
            worksheet = workbook.add_worksheet("Resumo")

            writer.close()
            workbook.close()
    else:
        st.toast("**Precisa de 2 arquivos para importar...**", icon=":material/warning:")
