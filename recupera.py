import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.express as px

# Inicializa as variáveis de memória se elas não existirem
if 'total_g1' not in st.session_state:
    st.session_state.total_g1 = 0.0
if 'total_g2' not in st.session_state:
    st.session_state.total_g2 = 0.0

# --- 1. SEGURANÇA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "cea2024":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔐 Acesso Restrito - Auditoria Fiscal")
        st.text_input("Senha da Consultoria:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("Senha incorreta.")
        return False
    return True

if not check_password():
    st.stop()


###########################################

# --- 2. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Módulo 1: Extração e Importação", layout="wide")
st.title("👞 Auditoria de Calçados - Grupo 1")

# Criação de abas para organizar as duas formas de entrada
aba_xml, aba_excel, aba_pgdas = st.tabs(["📥 Processar XML´s Avulsos", "📊 Importar XML´s por Planilha (Excel/CSV)", "📄 PGDAS"])

cfops_st = ['5401', '5402', '5403', '5405', '6401', '6403', '6404']

# --- ABA 1: PROCESSAMENTO DE XML (DRAG AND DROP) ---
with aba_xml:
    st.markdown("### Leitura Direta de Arquivos XML")
    arquivos = st.file_uploader("Arraste os XMLs aqui", accept_multiple_files=True, type=['xml'], key="xml_up")

    lista_final = []
    if arquivos:
        for arquivo in arquivos:
            try:
                tree = ET.parse(arquivo)
                root = tree.getroot()
                ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                
                n_nfe = root.find('.//ns:ide/ns:nNF', ns).text
                data_emi = root.find('.//ns:ide/ns:dhEmi', ns).text[:10]
                
                for det in root.findall('.//ns:det', ns):
                    prod = det.find('ns:prod', ns)
                    imposto = det.find('ns:imposto', ns)
                    
                    ncm = prod.find('ns:NCM', ns).text
                    cfop = prod.find('ns:CFOP', ns).text
                    v_prod = float(prod.find('ns:vProd', ns).text)
                    x_prod = prod.find('ns:xProd', ns).text
                    
                    csosn = "N/A"
                    for sn in imposto.findall('.//ns:CSOSN', ns):
                        csosn = sn.text
                    
                    tem_st = cfop in cfops_st
                    lista_final.append({
                        "Nota": n_nfe, "Data": data_emi, "Produto": x_prod,
                        "NCM": ncm, "CFOP": cfop, "CSOSN": csosn, "Valor": v_prod,
                        "Operação ST?": "Sim" if tem_st else "Não"
                    })
            except Exception as e:
                st.error(f"Erro no XML {arquivo.name}: {e}")

# --- ABA 2: IMPORTAÇÃO DE EXCEL ---
with aba_excel:
    st.markdown("### Importar Relatório de Itens (ERP)")
    st.info("A planilha deve conter colunas com nomes similares a: NCM, CFOP, Valor e CSOSN.")
    arquivo_planilha = st.file_uploader("Upload Excel ou CSV", type=['xlsx', 'csv'], key="excel_up")

    if arquivo_planilha:
        try:
            if arquivo_planilha.name.endswith('.csv'):
                df_importado = pd.read_csv(arquivo_planilha)
            else:
                df_importado = pd.read_excel(arquivo_planilha)
            
            # Padronização básica das colunas para o motor de auditoria
            df_importado.columns = [c.upper() for c in df_importado.columns]
            
            # Criando a coluna de Operação ST baseada no CFOP importado
            if 'CFOP' in df_importado.columns:
                df_importado['CFOP'] = df_importado['CFOP'].astype(str).str.replace('.0', '', regex=False)
                df_importado['Operação ST?'] = df_importado['CFOP'].apply(lambda x: "Sim" if x in cfops_st else "Não")
                
            lista_final = df_importado.to_dict('records')
            st.success("Planilha importada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao ler planilha: {e}")

#####################################

# --- ABA 3: CONFRONTO COM O PGDAS ---
with aba_pgdas:
    st.subheader("📊 Diagnóstico de Recuperação (PGDAS-D)")
    st.markdown("Insira os dados do extrato do Simples Nacional para comparar com os XMLs.")
    
    with st.form("calculo_auditoria"):
        col1, col2 = st.columns(2)
        # O que o contador declarou como ST no PGDAS
        receita_st_pgdas = col1.number_input("Receita ST declarada no DAS (R$)", min_value=0.0)
        aliquota = col2.number_input("Alíquota Efetiva do Mês (%)", value=8.5)
        
        # Escolha qual grupo de XML servirá de base (G1 ou G2)
        origem = st.radio("Comparar DAS contra:", ["XML Grupo 1", "XML Grupo 2"])
        
        botao = st.form_submit_button("Gerar Diagnóstico")

    if botao:
        # Aqui o sistema pega o total que foi calculado lá nas abas 1 ou 2
        # (Certifique-se que suas variáveis de total se chamam total_g1 e total_g2)
        base_xml = total_g1 if origem == "XML Grupo 1" else total_g2
        
        diferenca = base_xml - receita_st_pgdas
        
        if diferenca > 0:
            # Cálculo do ICMS (33.5% da fatia do Simples)
            credito = (diferenca * (aliquota / 100)) * 0.335
            
            st.success(f"### 💰 Crédito Identificado: R$ {credito:,.2f}")
            st.info(f"O contador deixou de segregar R$ {diferenca:,.2f} de faturamento ST.")
        else:
            st.warning("Nenhuma diferença encontrada. Os valores declarados batem com os XMLs.")
            
#################################################################

# --- EXIBIÇÃO CONSOLIDADA DOS RESULTADOS ---
st.markdown("---")
if lista_final:
    df = pd.DataFrame(lista_final)
    
    # Filtro opcional: Mostrar apenas o que é calçado (NCM começa com 64)
    if 'NCM' in df.columns:
        df['NCM'] = df['NCM'].astype(str)
        df['Calçado?'] = df['NCM'].apply(lambda x: "Sim" if x.startswith('64') else "Não")

    st.subheader("📋 Relatório Consolidado para Auditoria")
    st.dataframe(df, use_container_width=True)
    
    total_st = df[df["Operação ST?"] == "Sim"]["VALOR"].sum() if "VALOR" in df.columns else df[df["Operação ST?"] == "Sim"]["Valor"].sum()
    st.success(f"**Total identificado com ST nesta carga:** R$ {total_st:,.2f}")
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Exportar Resultado Final", csv, "auditoria_consolidada.csv", "text/csv")
else:
    st.warning("Nenhum dado carregado via XML ou Planilha.")
