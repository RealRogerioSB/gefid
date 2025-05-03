import glob

import pandas as pd
import streamlit as st
import xlsxwriter
from streamlit.connections import SQLConnection

st.cache_data.clear()

engine = st.connection("DB2", type=SQLConnection)

st.subheader(":material/dynamic_form: DIPJ")

st.columns(2)[0].markdown("##### Devem ser colocados 12 arquivos 064B da mesma empresa na pasta "
                          "P:\MER\Acoes_Escriturais\@deletar\, e não pode ter nenhum arquivo com "
                          "a mesma extensão de outra empresa ou ano")


@st.cache_data(show_spinner=":material/hourglass: Obtendo os dados, aguarde...")
def load_active(active: str) -> dict[int, str]:
    df1 = engine.query(
        sql=f"""
            SELECT
                t1.CD_CLI_EMT AS MCI,
                t2.NOM
            FROM
                DB2AEB.PRM_EMP AS t1
                INNER JOIN DB2MCI.CLIENTE AS t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE
                t1.DT_ECR_CTR IS {active.upper()}
        """,
        show_spinner=False,
        ttl=0,
    )
    return {k: v for k, v in zip(df1["mci"].to_list(), df1["nom"].to_list())}


@st.cache_data(show_spinner=False)
def load_report(_mci: int) -> tuple[int, str, str, int]:
    df2 = engine.query(
        sql="""
            SELECT t1.CD_CLI_EMT AS MCI_EMPRESA,
                   STRIP(t1.SG_EMP) AS SIGLA,
                   STRIP(t2.NOM) AS EMPRESA,
                   t2.COD_CPF_CGC AS CNPJ
            FROM DB2AEB.PRM_EMP t1
                INNER JOIN DB2MCI.CLIENTE t2
                    ON t2.COD = t1.CD_CLI_EMT
            WHERE t1.CD_CLI_EMT = :mci
            """,
        show_spinner=False,
        ttl=0,
        params=dict(mci=_mci),
    )
    return df2["mci_empresa"].iloc[0], df2["sigla"].iloc[0], df2["empresa"].iloc[0], df2["cnpj"].iloc[0]


st.radio(label="**Situação de Clientes:**", options=["ativos", "inativos"], key="option_active")

kv: dict[int, str] = load_active("null") if st.session_state["option_active"] == "ativos" else load_active("not null")

col1, _ = st.columns([2, 1])
col1.selectbox(
    label="**Clientes ativos:**" if st.session_state["option_active"] == "ativos" else "**Clientes inativos:**",
    options=sorted(kv.values()),
    key="empresa",
)

mci: int = next((chave for chave, valor in kv.items() if valor == st.session_state["empresa"]), 0)

if st.button("**Gerar DIPJ**", type="primary"):
    with st.spinner(":material/hourglass: Verificando os dados, aguarde...", show_time=True):
        mci_emissor, cod_aeb, nome_emissor, cnpj_emissor = load_report(mci)

        # diretórios
        diretorio_origem: str = "static/escriturais/@deletar"
        diretorio_destino: str = "static/escriturais/@deletar"

        # pegando os arquivos com final ".PAGO"
        all_files: list[str] = glob.glob(diretorio_origem + "/*.PAGO")

        # Verificando se foram localizados 12 arquivos *.PAGO no diretório
        if len(all_files) < 12:
            st.toast("**Tem menos de 12 arquivos de rendimentos pagos no diretório.Favor corrigir e reiniciar**",
                     icon=":material/warning:")

        elif len(all_files) > 12:
            st.toast("**Tem mais de 12 arquivos de rendimentos pagos no diretório.Favor corrigir e reiniciar**",
                     icon=":material/warning:")

        else:
            # criando a lista
            li: list[pd.DataFrame] = []

            # criando dict para modelar o dataframe com os 12 meses
            mod = {
                "Ano Ref": ["9999", "9999", "9999", "9999", "9999", "9999",
                            "9999", "9999", "9999", "9999", "9999", "9999"],
                "MCI Emissor": ["999999999", "999999999", "999999999",
                                "999999999", "999999999", "999999999",
                                "999999999", "999999999", "999999999",
                                "999999999", "999999999", "999999999"],
                "País": ["BRA", "BRA", "BRA", "BRA", "BRA", "BRA",
                         "BRA", "BRA", "BRA", "BRA", "BRA", "BRA"],
                "Tipo Pessoa": ["99", "99", "99", "99", "99", "99",
                                "99", "99", "99", "99", "99", "99"],
                "Mês Ref": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "Tipo Direito": ["DIVIDENDOS", "DIVIDENDOS", "DIVIDENDOS",
                                 "DIVIDENDOS", "DIVIDENDOS", "DIVIDENDOS",
                                 "DIVIDENDOS", "DIVIDENDOS", "DIVIDENDOS",
                                 "DIVIDENDOS", "DIVIDENDOS", "DIVIDENDOS"],
                "Vlr Bruto": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "Vlr IR": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "Vlr Líquido": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            }

            # adicionando o modelo na lista
            li.append(pd.DataFrame.from_dict(mod))

            # iterando a leitura do Pandas em todos os arquivos da pasta
            for filename in all_files:
                df: pd.DataFrame = pd.read_fwf(
                    filename,
                    colspecs=[(0, 4), (4, 6), (6, 15), (15, 18), (18, 19), (19, 59),
                              (59, 76), (76, 93), (93, 110), (110, 133)],
                    names=["Ano Ref", "Mês Ref", "MCI Emissor", "País", "Tipo Pessoa",
                           "Tipo Direito", "Vlr Bruto", "Vlr IR", "Vlr Líquido", "Controle"],
                    encoding="latin"
                )

                # guardando a informação do ano do último arquivo lido
                ano: str = str(df.iat[0, 0])
                dfs: pd.DataFrame = df[pd.isnull(df["Controle"]) &
                                       df["Mês Ref"].ne(99) &
                                       df["MCI Emissor"].eq(mci_emissor)].copy()

                # adicionando no final da lista
                li.append(dfs)

            # concatenando o li
            dfs = pd.concat(li, axis=0, ignore_index=True, verify_integrity=True)

            print(dfs["Ano Ref"].unique())

            # Verificando se todos os arquivos sÃ£o do mesmo ano e guardando o ano caso
            if len(dfs["Ano Ref"].unique()) == 1:
                st.toast("**Não achamos ninguém**", icon=":material/warning:")
                st.stop()

            # Verificando se todos os arquivos são do mesmo ano e guardando o ano caso
            if len(dfs["Ano Ref"].unique()) > 2:
                # eliminando a primeira linha que foi criada só para gerar o modelo com os 12 meses
                dfs.drop(labels=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], axis=0, inplace=True)

                st.toast(f"**Identificamos arquivos de anos diferentes {dfs['Ano Ref'].unique()}.\nTodos os arquivos "
                         f"precisam ser do mesmo ano.\nIremos encerrar o processo.**", icon=":material/warning:")
                st.stop()

            # pivotando o dfs
            table = pd.pivot_table(dfs, values=["Vlr Bruto", "Vlr IR", "Vlr Líquido"],
                                   index=["País", "Tipo Pessoa", "Tipo Direito"],
                                   columns=["Mês Ref"], sort=False)

            # substitui nan por zeros
            table = table.fillna(0)

            # resetando os index para eliminar a hierarquia
            table = table.reset_index()

            # eliminando a primeira linha que foi criada só para gerar o modelo com os 12 meses
            table = table.drop(labels=0, axis=0)

            # criando o workbook e a worksheet com o xlsxwriter
            workbook = xlsxwriter.Workbook(f"{diretorio_destino}/DIPJ {cod_aeb} {ano}.xlsx")
            ws = workbook.add_worksheet(f"DIPJ {ano}")

            titulo1 = workbook.add_format(dict(bold=True, align="left", bg_color="ffc000", right=2, font_size=14))
            titulo2 = workbook.add_format(dict(bold=True, align="center", bg_color="yellow", border=2, font_size=14))
            titulo3 = workbook.add_format(
                dict(bold=True, align="left", bg_color="ffc000", right=2, bottom=2, font_size=14))

            total_format = workbook.add_format(dict(bold=True, align="right"))

            # criando formato de número
            vlr_format = workbook.add_format(dict(num_format="#,##0.00", align="center"))
            vlr_format2 = workbook.add_format(dict(num_format="#,##0.00", align="center", bold=True))

            texto_format = workbook.add_format(dict(align="center", bold=True))
            texto_format2 = workbook.add_format(dict(align="left", bold=True))

            # formatando as colunas da worksheet
            ws.set_column(0, 0, 6, texto_format)
            ws.set_column(1, 1, 5, texto_format)
            ws.set_column(2, 2, 34, texto_format2)
            ws.set_column(3, 41, 15, vlr_format)

            ws.merge_range("A1:C1", f"Emissor............:  {nome_emissor}", titulo1)
            ws.merge_range("A2:C2", f"CNPJ.................:  {cnpj_emissor}", titulo1)
            ws.merge_range("A3:C3", f"Ano Referência:  {ano}", titulo3)

            # setando a linha inicial da worksheet para escrever a informação
            row = 3

            # escrevendo os cabeçalhos
            ws.merge_range(f"D{row}:F{row}", "Janeiro", titulo2)
            ws.merge_range(f"G{row}:I{row}", "Fevereiro", titulo2)
            ws.merge_range(f"J{row}:L{row}", "Março", titulo2)
            ws.merge_range(f"M{row}:O{row}", "Abril", titulo2)
            ws.merge_range(f"P{row}:R{row}", "Maio", titulo2)
            ws.merge_range(f"S{row}:U{row}", "Junho", titulo2)
            ws.merge_range(f"V{row}:X{row}", "Julho", titulo2)
            ws.merge_range(f"Y{row}:AA{row}", "Agosto", titulo2)
            ws.merge_range(f"AB{row}:AD{row}", "Setembro", titulo2)
            ws.merge_range(f"AE{row}:AG{row}", "Outubro", titulo2)
            ws.merge_range(f"AH{row}:AJ{row}", "Novembro", titulo2)
            ws.merge_range(f"AK{row}:AM{row}", "Dezembro", titulo2)
            ws.merge_range(f"AN{row}:AP{row}", f"Total de {ano}", titulo2)

            # escrevendo os cabeçalhos
            ws.write(f"A{row + 1}", "País", texto_format2)
            ws.write(f"B{row + 1}", "TI", texto_format2)
            ws.write(f"C{row + 1}", "Direito", texto_format)

            # janeiro
            ws.write(f"D{row + 1}", "Bruto R$", texto_format)
            ws.write(f"E{row + 1}", "IR R$", texto_format)
            ws.write(f"F{row + 1}", "Líquido R$", texto_format)

            # fevereiro
            ws.write(f"G{row + 1}", "Bruto R$", texto_format)
            ws.write(f"H{row + 1}", "IR R$", texto_format)
            ws.write(f"I{row + 1}", "Líquido R$", texto_format)

            # março
            ws.write(f"J{row + 1}", "Bruto R$", texto_format)
            ws.write(f"K{row + 1}", "IR R$", texto_format)
            ws.write(f"L{row + 1}", "Líquido R$", texto_format)

            # abril
            ws.write(f"M{row + 1}", "Bruto R$", texto_format)
            ws.write(f"N{row + 1}", "IR R$", texto_format)
            ws.write(f"O{row + 1}", "Líquido R$", texto_format)

            # maio
            ws.write(f"P{row + 1}", "Bruto R$", texto_format)
            ws.write(f"Q{row + 1}", "IR R$", texto_format)
            ws.write(f"R{row + 1}", "Líquido R$", texto_format)

            # junho
            ws.write(f"S{row + 1}", "Bruto R$", texto_format)
            ws.write(f"T{row + 1}", "IR R$", texto_format)
            ws.write(f"U{row + 1}", "Líquido R$", texto_format)

            # julho
            ws.write(f"V{row + 1}", "Bruto R$", texto_format)
            ws.write(f"W{row + 1}", "IR R$", texto_format)
            ws.write(f"X{row + 1}", "Líquido R$", texto_format)

            # agosto
            ws.write(f"Y{row + 1}", "Bruto R$", texto_format)
            ws.write(f"Z{row + 1}", "IR R$", texto_format)
            ws.write(f"AA{row + 1}", "Líquido R$", texto_format)

            # setembro
            ws.write(f"AB{row + 1}", "Bruto R$", texto_format)
            ws.write(f"AC{row + 1}", "IR R$", texto_format)
            ws.write(f"AD{row + 1}", "Líquido R$", texto_format)

            # outubro
            ws.write(f"AE{row + 1}", "Bruto R$", texto_format)
            ws.write(f"AF{row + 1}", "IR R$", texto_format)
            ws.write(f"AG{row + 1}", "Líquido R$", texto_format)

            # novembro
            ws.write(f"AH{row + 1}", "Bruto R$", texto_format)
            ws.write(f"AI{row + 1}", "IR R$", texto_format)
            ws.write(f"AJ{row + 1}", "Líquido R$", texto_format)

            # dezembro
            ws.write(f"AK{row + 1}", "Bruto R$", texto_format)
            ws.write(f"AL{row + 1}", "IR R$", texto_format)
            ws.write(f"AM{row + 1}", "Líquido R$", texto_format)

            # total
            ws.write(f"AN{row + 1}", "Bruto R$", texto_format)
            ws.write(f"AO{row + 1}", "IR R$", texto_format)
            ws.write(f"AP{row + 1}", "Líquido R$", texto_format)

            # escrevendo as informações
            for x in range(len(table.index)):
                ws.write(row + 1, 0, table.iat[x, 0])
                ws.write(row + 1, 1, table.iat[x, 1])
                ws.write(row + 1, 2, table.iat[x, 2])

                # janeiro
                ws.write(row + 1, 3, int(table.iat[x, 3]) / 100)
                ws.write(row + 1, 4, int(table.iat[x, 15]) / 100)
                ws.write(row + 1, 5, int(table.iat[x, 27]) / 100)

                # fevereiro
                ws.write(row + 1, 6, int(table.iat[x, 4]) / 100)
                ws.write(row + 1, 7, int(table.iat[x, 16]) / 100)
                ws.write(row + 1, 8, int(table.iat[x, 28]) / 100)

                # marÃ§o
                ws.write(row + 1, 9, int(table.iat[x, 5]) / 100)
                ws.write(row + 1, 10, int(table.iat[x, 17]) / 100)
                ws.write(row + 1, 11, int(table.iat[x, 29]) / 100)

                # abril
                ws.write(row + 1, 12, int(table.iat[x, 6]) / 100)
                ws.write(row + 1, 13, int(table.iat[x, 18]) / 100)
                ws.write(row + 1, 14, int(table.iat[x, 30]) / 100)

                # maio
                ws.write(row + 1, 15, int(table.iat[x, 7]) / 100)
                ws.write(row + 1, 16, int(table.iat[x, 19]) / 100)
                ws.write(row + 1, 17, int(table.iat[x, 31]) / 100)

                # junho
                ws.write(row + 1, 18, int(table.iat[x, 8]) / 100)
                ws.write(row + 1, 19, int(table.iat[x, 20]) / 100)
                ws.write(row + 1, 20, int(table.iat[x, 32]) / 100)

                # julho
                ws.write(row + 1, 21, int(table.iat[x, 9]) / 100)
                ws.write(row + 1, 22, int(table.iat[x, 21]) / 100)
                ws.write(row + 1, 23, int(table.iat[x, 33]) / 100)

                # agosto
                ws.write(row + 1, 24, int(table.iat[x, 10]) / 100)
                ws.write(row + 1, 25, int(table.iat[x, 22]) / 100)
                ws.write(row + 1, 26, int(table.iat[x, 34]) / 100)

                # setembro
                ws.write(row + 1, 27, int(table.iat[x, 11]) / 100)
                ws.write(row + 1, 28, int(table.iat[x, 23]) / 100)
                ws.write(row + 1, 29, int(table.iat[x, 35]) / 100)

                # outubro
                ws.write(row + 1, 30, int(table.iat[x, 12]) / 100)
                ws.write(row + 1, 31, int(table.iat[x, 24]) / 100)
                ws.write(row + 1, 32, int(table.iat[x, 36]) / 100)

                # novembro
                ws.write(row + 1, 33, int(table.iat[x, 13]) / 100)
                ws.write(row + 1, 34, int(table.iat[x, 25]) / 100)
                ws.write(row + 1, 35, int(table.iat[x, 37]) / 100)

                # dezembro
                ws.write(row + 1, 36, int(table.iat[x, 14]) / 100)
                ws.write(row + 1, 37, int(table.iat[x, 26]) / 100)
                ws.write(row + 1, 38, int(table.iat[x, 38]) / 100)

                # totais por linha
                ws.write_formula(row + 1, 39, f"=D{row + 2}+G{row + 2}+J{row + 2}+M{row + 2}+P{row + 2}+S{row + 2}+"
                                              f"V{row + 2}+Y{row + 2}+AB{row + 2}+AE{row + 2}+AH{row + 2}+AK{row + 2}",
                                 vlr_format2)
                ws.write_formula(row + 1, 40, f"=E{row + 2}+H{row + 2}+K{row + 2}+N{row + 2}+Q{row + 2}+T{row + 2}+"
                                              f"W{row + 2}+Z{row + 2}+AC{row + 2}+AF{row + 2}I{row + 2}+AL{row + 2}",
                                 vlr_format2)
                ws.write_formula(row + 1, 41, f"=F{row + 2}+I{row + 2}+L{row + 2}+O{row + 2}+R{row + 2}+U{row + 2}+"
                                              f"X{row + 2}+AA{row + 2}+AD{row + 2}+AG{row + 2}+AJ{row + 2}+AM{row + 2}",
                                 vlr_format2)

                row += 1

            # totais por coluna
            ws.write("C" + str(row + 3), "Subtotal", total_format)

            ws.write_formula(row + 2, 3, f"=SUBTOTAL(9,D5:D{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 4, f"=SUBTOTAL(9,E5:E{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 5, f"=SUBTOTAL(9,F5:F{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 6, f"=SUBTOTAL(9,G5:G{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 7, f"=SUBTOTAL(9,H5:H{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 8, f"=SUBTOTAL(9,I5:I{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 9, f"=SUBTOTAL(9,J5:J{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 10, f"=SUBTOTAL(9,K5:K{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 11, f"=SUBTOTAL(9,L5:L{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 12, f"=SUBTOTAL(9,M5:M{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 13, f"=SUBTOTAL(9,N5:N{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 14, f"=SUBTOTAL(9,O5:O{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 15, f"=SUBTOTAL(9,P5:P{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 16, f"=SUBTOTAL(9,Q5:Q{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 17, f"=SUBTOTAL(9,R5:R{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 18, f"=SUBTOTAL(9,S5:S{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 19, f"=SUBTOTAL(9,T5:T{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 20, f"=SUBTOTAL(9,U5:U{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 21, f"=SUBTOTAL(9,V5:V{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 22, f"=SUBTOTAL(9,W5:W{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 23, f"=SUBTOTAL(9,X5:X{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 24, f"=SUBTOTAL(9,Y5:Y{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 25, f"=SUBTOTAL(9,Z5:Z{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 26, f"=SUBTOTAL(9,AA5:AA{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 27, f"=SUBTOTAL(9,AB5:AB{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 28, f"=SUBTOTAL(9,AC5:AC{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 29, f"=SUBTOTAL(9,AD5:AD{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 30, f"=SUBTOTAL(9,AE5:AE{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 31, f"=SUBTOTAL(9,AF5:AF{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 32, f"=SUBTOTAL(9,AG5:AG{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 33, f"=SUBTOTAL(9,AH5:AH{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 34, f"=SUBTOTAL(9,AI5:AI{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 35, f"=SUBTOTAL(9,AJ5:AJ{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 36, f"=SUBTOTAL(9,AK5:AK{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 37, f"=SUBTOTAL(9,AL5:AL{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 38, f"=SUBTOTAL(9,AM5:AM{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 39, f"=SUBTOTAL(9,AN5:AN{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 40, f"=SUBTOTAL(9,AO5:AO{row + 1})", vlr_format2)
            ws.write_formula(row + 2, 41, f"=SUBTOTAL(9,AP5:AP{row + 1})", vlr_format2)

            # criando filtro
            ws.autofilter("A4:AP4")

            # Congelando as primeiras 5 linhas
            ws.freeze_panes(4, 0)

            workbook.close()
