import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.express as px

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

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Módulo 1: Extração XML", layout="wide")
st.title("👞 Auditoria de Calçados - Grupo 1: XMLs")
st.markdown("""
Esta etapa consiste em ler as **NF-e de Saída** para identificar vendas que sofreram 
Substituição Tributária (ST) mas que podem ter sido tributadas novamente no Simples.
""")

# --- UPLOAD ---
arquivos = st.file_uploader("Arraste os XMLs de Saída aqui", accept_multiple_files=True, type=['xml'])

if arquivos:
    lista_final = []
    
    # CFOPs de Indústria que indicam Substituição Tributária
    cfops_st = ['5401', '5402', '5403', '5405', '6401', '6403', '6404']

    for arquivo in arquivos:
        try:
            tree = ET.parse(arquivo)
            root = tree.getroot()
            ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
            
            # 1. Dados da Nota
            n_nfe = root.find('.//ns:ide/ns:nNF', ns).text
            data_emi = root.find('.//ns:ide/ns:dhEmi', ns).text[:10]
            
            # 2. Varredura de Itens (det)
            for det in root.findall('.//ns:det', ns):
                prod = det.find('ns:prod', ns)
                imposto = det.find('ns:imposto', ns)
                
                # Dados básicos do produto
                x_prod = prod.find('ns:xProd', ns).text
                ncm = prod.find('ns:NCM', ns).text
                cfop = prod.find('ns:CFOP', ns).text
                v_prod = float(prod.find('ns:vProd', ns).text)
                
                # 3. Captura do CSOSN (Fundamental para Simples Nacional)
                # O CSOSN pode estar em diferentes tags dependendo da tributação
                csosn = "N/A"
                for icms in imposto.findall('.**.//ns:CSOSN', ns):
                    csosn = icms.text
                
                # 4. Regras de Auditoria
                e_calcado = ncm.startswith('64') # Capítulo 64 é Calçados
                tem_st = cfop in cfops_st
                
                # Cruzamento Crítico: Se tem ST, o CSOSN deveria ser 500
                alerta_segregacao = "VERIFICAR" if (tem_st and csosn != "500") else "OK"

                lista_final.append({
                    "Nota": n_nfe,
                    "Data": data_emi,
                    "Produto": x_prod,
                    "NCM": ncm,
                    "CFOP": cfop,
                    "CSOSN": csosn,
                    "Valor": v_prod,
                    "Calçado?": "Sim" if e_calcado else "Não",
                    "Operação ST?": "Sim" if tem_st else "Não",
                    "Status Auditoria": alerta_segregacao
                })
        except Exception as e:
            st.error(f"Erro ao processar {arquivo.name}: {e}")

    # --- EXIBIÇÃO DOS DADOS ---
    if lista_final:
        df = pd.DataFrame(lista_final)
        
        st.subheader("📋 Dados Extraídos e Auditados")
        st.dataframe(df, use_container_width=True)
        
        # Resumo Rápido
        total_st = df[df["Operação ST?"] == "Sim"]["Valor"].sum()
        st.success(f"**Total Identificado com ST:** R$ {total_st:,.2f}")
        
        # Botão de Exportação para o seu trabalho de análise fora do app
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar Dados (CSV)", csv, "extração_xml.csv", "text/csv")
else:
    st.info("Aguardando upload dos arquivos para iniciar a varredura."
else:
    st.warning("Aguardando upload dos arquivos XML para processamento.")
