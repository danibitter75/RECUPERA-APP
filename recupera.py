import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.express as px # Biblioteca para gráficos bonitos

# --- 1. CONFIGURAÇÃO DE SEGURANÇA ---
def check_password():
    """Retorna True se a senha estiver correta."""
    def password_entered():
        # ALTERE 'sua_senha_aqui' PARA A SENHA QUE VOCÊ DESEJAR
        if st.session_state["password"] == "cea2024": 
            st.session_state["password_correct"] = True
            del st.session_state["password"] # Limpa a senha da memória
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acesso Restrito - Consultoria")
        st.text_input("Por favor, insira a senha de acesso:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Acesso Restrito - Consultoria")
        st.text_input("Senha incorreta. Tente novamente:", type="password", on_change=password_entered, key="password")
        st.error("Acesso negado.")
        return False
    return True

# Se a senha não estiver correta, o script para aqui
if not check_password():
    st.stop()

#######################################################

# --- 2. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Auditoria Calçadista CEA", layout="wide")
st.title("👞 Inteligência Tributária: Setor de Calçados")

# --- 3. BARRA LATERAL - PARÂMETROS ---
st.sidebar.header("Configurações do Cliente")
empresa = st.sidebar.text_input("Nome da Empresa", "Indústria de Calçados X")
aliquota_simples = st.sidebar.slider("Alíquota Efetiva do Simples (%)", 4.0, 15.0, 8.5)
percentual_icms_no_simples = 33.5 # Percentual médio de ICMS dentro da guia do Simples

st.sidebar.markdown("---")
st.sidebar.header("Projeção Financeira")
selic = st.sidebar.number_input("Selic Atual (% a.a.)", value=11.25)

# --- 4. ÁREA DE UPLOAD ---
st.markdown(f"### 📁 Diagnóstico: {empresa}")
arquivos = st.file_uploader("Selecione os arquivos XML (Notas de Saída)", accept_multiple_files=True, type=['xml'])

# --- 5. PROCESSAMENTO LOGÍSTICO ---
if arquivos:
    dados = []
    # Lista de CFOPs de Indústria com ST (Onde está o dinheiro!)
    cfops_st = ['5401', '5402', '5403', '5405', '6401', '6403', '6404']

#################################################
    
 # --- NOVO BLOCO DE PROCESSAMENTO MÓDULO 1 ---   
for arquivo in arquivos_xml:
    try:
        tree = ET.parse(arquivo)
        root = tree.getroot()
        ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Dados da Nota
        ide = root.find('.//ns:ide', ns)
        n_nfe = ide.find('ns:nNF', ns).text
        data_emi = ide.find('ns:dhEmi', ns).text[:10]
        
        # Dados do Emitente (Para confirmar se é o seu cliente)
        emit = root.find('.//ns:emit/ns:xNome', ns).text

        for det in root.findall('.//ns:det', ns):
            prod = det.find('ns:prod', ns)
            imposto = det.find('ns:imposto', ns)
            
            ncm = prod.find('ns:NCM', ns).text
            cfop = prod.find('ns:CFOP', ns).text
            v_prod = float(prod.find('ns:vProd', ns).text)
            x_prod = prod.find('ns:xProd', ns).text
            
            # Buscando o CSOSN (Crucial para Simples Nacional)
            # Ele fica dentro de ICMS / ICMSSN101, 102, 500, etc.
            csosn = ""
            for icms in imposto.findall('.//ns:CSOSN', ns):
                csosn = icms.text

            # LÓGICA DE AUDITORIA:
            # 1. É calçado? (NCM começa com 64)
            # 2. CFOP é de ST? (Inicia com 54 ou 64)
            # 3. Foi tributado errado? (CFOP de ST mas CSOSN diferente de 500)
            
            e_calcado = ncm.startswith('64')
            e_st = cfop in ['5401', '5402', '5403', '5405', '6401', '6403', '6404']
            alerta_erro = e_st and csosn != '500'

            dados.append({
                "Data": data_emi,
                "Nota": n_nfe,
                "Produto": x_prod,
                "NCM": ncm,
                "CFOP": cfop,
                "CSOSN": csosn,
                "Valor": v_prod,
                "É Calçado?": "Sim" if e_calcado else "Não",
                "Operação ST?": "Sim" if e_st else "Não",
                "Possível Erro": "SIM" if alerta_erro else "Não"
            })
    except Exception as e:
        st.error(f"Erro no XML {arquivo.name}: {e}")

    ################################################

    df = pd.DataFrame(dados)

    # --- 6. DASHBOARD DE RESULTADOS ---
    total_faturado = df['Valor'].sum()
    total_credito = df['Crédito'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento Analisado", f"R$ {total_faturado:,.2f}")
    col2.metric("Crédito Total Identificado", f"R$ {total_credito:,.2f}", delta="Cashback Fiscal")
    
    # Visão CEA: Valorização
    valor_futuro = total_credito * (1 + (selic/100))
    col3.metric("Valor c/ Selic (12 meses)", f"R$ {valor_futuro:,.2f}")

    # --- 7. GRÁFICOS ---
    st.markdown("---")
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("Concentração por CFOP")
        fig_cfop = px.pie(df, values='Valor', names='CFOP', hole=.3)
        st.plotly_chart(fig_cfop, use_container_width=True)
        
    with c_right:
        st.subheader("Top 5 NCMs por Faturamento")
        top_ncm = df.groupby('NCM')['Valor'].sum().nlargest(5).reset_index()
        fig_ncm = px.bar(top_ncm, x='NCM', y='Valor', color='NCM')
        st.plotly_chart(fig_ncm, use_container_width=True)

    # --- 8. EXPORTAÇÃO ---
    st.markdown("### 📄 Relatório Detalhado")
    st.dataframe(df.style.format({"Valor": "R$ {:.2f}", "Crédito": "R$ {:.2f}"}))
    
    # Botão para baixar Excel
    df.to_excel("diagnostico_fiscal.xlsx", index=False)
    with open("diagnostico_fiscal.xlsx", "rb") as f:
        st.download_button("Baixar Relatório em Excel", f, file_name=f"auditoria_{empresa}.xlsx")

else:
    st.warning("Aguardando upload dos arquivos XML para processamento.")
