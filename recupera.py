import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    if "password_correct" not in st.session_state:
        st.text_input("Digite a senha da Consultoria", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

def password_entered():
    if st.session_state["password"] == "SUA_SENHA_AQUI": # Defina sua senha
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()  # Trava o app aqui se a senha estiver errada

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Consultoria Tributária CEA", layout="wide", page_icon="👞")

# Estilização básica
st.title("👞 Auditoria Digital: Indústria de Calçados")
st.subheader("Recuperação de Créditos para Simples Nacional")
st.markdown("---")

# 2. BARRA LATERAL (INPUTS DE CONSULTOR)
st.sidebar.header("Parâmetros do Diagnóstico")
aliquota_simples = st.sidebar.slider("Alíquota efetiva do Simples (%)", 4.0, 15.0, 8.5)
selic_anual = st.sidebar.number_input("Taxa Selic atual (% a.a.)", value=11.25)

# 3. ÁREA DE UPLOAD
st.info("Arraste os arquivos XML das Notas Fiscais de Saída dos últimos meses abaixo.")
arquivos_xml = st.file_uploader("Upload de XMLs", accept_multiple_files=True, type=['xml'])

if arquivos_xml:
    lista_itens = []
    
    # Lista de CFOPs comuns de Substituição Tributária (onde mora o crédito na indústria)
    cfops_recuperaveis = ['5401', '5402', '5403', '5405', '6401', '6403', '6404']

    for arquivo in arquivos_xml:
        try:
            tree = ET.parse(arquivo)
            root = tree.getroot()
            ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
            
            n_nfe = root.find('.//ns:ide/ns:nNF', ns).text
            
            for det in root.findall('.//ns:det', ns):
                ncm = det.find('.//ns:prod/ns:NCM', ns).text
                cfop = det.find('.//ns:prod/ns:CFOP', ns).text
                valor = float(det.find('.//ns:prod/ns:vProd', ns).text)
                
                # Regra: Se for calçado (NCM 64) e CFOP de ST, marca como possível crédito
                status = "Recuperável" if cfop in cfops_recuperaveis else "Tributado"
                
                lista_itens.append({
                    "Nota": n_nfe,
                    "NCM": ncm,
                    "CFOP": cfop,
                    "Valor": valor,
                    "Status": status
                })
        except Exception as e:
            st.warning(f"Erro ao ler o arquivo {arquivo.name}")

    # 4. PROCESSAMENTO DOS DADOS
    df = pd.DataFrame(lista_itens)
    df_recuperavel = df[df['Status'] == "Recuperável"]
    
    total_faturado = df['Valor'].sum()
    total_recuperavel = df_recuperavel['Valor'].sum()
    
    # Estimativa de Crédito (Simplificada: parcela de ICMS dentro do Simples)
    # Geralmente o ICMS representa cerca de 33.5% da guia do Simples na Indústria
    estimativa_credito = (total_recuperavel * (aliquota_simples / 100)) * 0.335

    # 5. DASHBOARD EXECUTIVO (AQUI VOCÊ BRILHA COMO CEA)
    st.markdown("### 📊 Resultado do Diagnóstico")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Total Analisado", f"R$ {total_faturado:,.2f}")
    c2.metric("Base de Crédito (ST)", f"R$ {total_recuperavel:,.2f}")
    c3.metric("Crédito Estimado (Cashback)", f"R$ {estimativa_credito:,.2f}", delta="Recuperável")

    st.markdown("---")
    
    # 6. VISÃO FINANCEIRA E INVESTIMENTO
    st.subheader("📈 Projeção de Valorização (Visão CEA)")
    col_inv1, col_inv2 = st.columns(2)
    
    valor_com_selic = estimativa_credito * (1 + (selic_anual/100))
    
    with col_inv1:
        st.write(f"Se este valor de **R$ {estimativa_credito:,.2f}** for recuperado e aplicado na Selic atual:")
        st.info(f"**Valor após 12 meses:** R$ {valor_com_selic:,.2f}")
    
    with col_inv2:
        st.bar_chart(pd.DataFrame({
            "Cenários": ["Crédito Inicial", "Crédito + Selic (1 ano)"],
            "Valores": [estimativa_credito, valor_com_selic]
        }).set_index("Cenários"))

    # 7. TABELA DETALHADA
    with st.expander("Ver detalhes das notas analisadas"):
        st.dataframe(df)

else:
    st.warning("Aguardando upload de arquivos para iniciar o diagnóstico.")
