import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.express as px
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTADO ---
st.set_page_config(page_title="Auditoria Fiscal - Calçados", layout="wide")

# Inicializa as variáveis no Session State para comunicação entre abas
if 'total_g1' not in st.session_state:
    st.session_state.total_g1 = 0.0
if 'total_g2' not in st.session_state:
    st.session_state.total_g2 = 0.0
if 'calculo_realizado' not in st.session_state:
    st.session_state.calculo_realizado = False

# --- 2. FUNÇÃO GERADORA DE PDF (SEM ACENTOS PARA EVITAR ERROS) ---
def gerar_pdf(empresa, base_xml, base_pgdas, diferenca, credito, aliquota):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio de Diagnostico Fiscal - Calcados", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Empresa: {empresa}", ln=True)
    pdf.ln(5)
    
    # Tabela de Dados
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, "Descricao", 1, 0, "L", True)
    pdf.cell(90, 10, "Valor (R$)", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(100, 10, "Faturamento Identificado (XML)", 1)
    pdf.cell(90, 10, f"{base_xml:,.2f}", 1, 1, "C")
    pdf.cell(100, 10, "Faturamento Declarado (PGDAS)", 1)
    pdf.cell(90, 10, f"{base_pgdas:,.2f}", 1, 1, "C")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, "Diferenca Omitida (ST)", 1)
    pdf.cell(90, 10, f"{diferenca:,.2f}", 1, 1, "C")
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(0, 100, 0)
    pdf.cell(0, 10, f"CREDITO ESTIMADO PARA RECUPERACAO: R$ {credito:,.2f}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(0, 0, 0)
    texto_nota = f"Nota: Calculo baseado na aliquota de {aliquota}% com fator de 33.5% (ICMS Simples Nacional)."
    pdf.multi_cell(0, 10, texto_nota)
    
    return pdf.output(dest="S").encode('latin-1', 'ignore')

# --- 3. BARRA LATERAL E SEGURANÇA ---
st.sidebar.title("Configurações")
senha = st.sidebar.text_input("Senha de Acesso", type="password")
if senha != "cea2024":
    st.warning("Por favor, insira a senha na barra lateral para acessar o sistema.")
    st.stop()

empresa = st.sidebar.text_input("Nome da Empresa", value="Empresa Exemplo")
cfops_st = ['5401', '5402', '5403', '5405', '6401', '6403', '6404']

st.title("Auditoria Para Recuperação de Créditos Tributários para Calçados - Recuperação de ICMS")

# --- 4. ESTRUTURA DE ABAS ---
aba1, aba2, aba3 = st.tabs(["📥 XML´s Avulsos", "📊 XML´s de Excel/CSV", "📄 PGDAS & Relatório"])

# --- ABA 1: XMLS AVULSOS ---
with aba1:
    st.header("Upload de XMLs de Venda")
    arquivos_xml = st.file_uploader("Selecione os arquivos XML", type="xml", accept_multiple_files=True)
    
    if arquivos_xml:
        soma_g1 = 0.0
        for arq in arquivos_xml:
            try:
                tree = ET.parse(arq)
                root = tree.getroot()
                ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
                for det in root.findall('.//ns:det', ns):
                    cfop = det.find('.//ns:CFOP', ns).text
                    if cfop in cfops_st:
                        v_prod = float(det.find('.//ns:vProd', ns).text)
                        soma_g1 += v_prod
            except:
                continue
        st.session_state.total_g1 = soma_g1
        st.success(f"Total Identificado no Grupo 1: R$ {soma_g1:,.2f}")

# --- ABA 2: EXCEL / CSV ---
with aba2:
    st.header("Importação por Planilha")
    arquivo_planilha = st.file_uploader("Selecione a planilha", type=["xlsx", "csv"])
    
    if arquivo_planilha:
        try:
            df = pd.read_csv(arquivo_planilha) if arquivo_planilha.name.endswith('.csv') else pd.read_excel(arquivo_planilha)
            df.columns = [c.upper() for c in df.columns]
            
            if 'CFOP' in df.columns and ('VALOR' in df.columns or 'VALOR TOTAL' in df.columns):
                val_col = 'VALOR' if 'VALOR' in df.columns else 'VALOR TOTAL'
                df['CFOP'] = df['CFOP'].astype(str).str.replace('.0', '', regex=False)
                total_g2 = df[df['CFOP'].isin(cfops_st)][val_col].sum()
                st.session_state.total_g2 = total_g2
                st.success(f"Total Identificado no Grupo 2: R$ {total_g2:,.2f}")
            else:
                st.error("Planilha deve conter as colunas 'CFOP' e 'VALOR'.")
        except Exception as e:
            st.error(f"Erro ao processar: {e}")

# --- ABA 3: PGDAS E PDF ---
with aba3:
    st.header("Confronto PGDAS")

# KPIs de Topo
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Identificado", f"R$ {valor_base:,.2f}")
    c2.metric("Base Declarada", f"R$ {pgdas_declarado:,.2f}", delta=f"R$ {valor_base - pgdas_declarado:,.2f}", delta_color="inverse")
    c3.metric("Recuperação Estimada", f"R$ {credito:,.2f}", help="Cálculo baseado em ICMS-ST e Alíquota Efetiva")

    # Gráfico de Comparação (Plotly)
    df_grafico = pd.DataFrame({
        'Categoria': ['Identificado (XML)', 'Declarado (PGDAS)'],
        'Valores': [valor_base, pgdas_declarado]
    })
    fig = px.bar(df_grafico, x='Categoria', y='Valores', color='Categoria', 
                 title="Confronto de Bases Tributárias", color_discrete_sequence=['#00CC96', '#EF553B'])
    st.plotly_chart(fig, use_container_width=True)
    
    soma_conciliada = st.session_state.total_g1 + st.session_state.total_g2
    
    base_xml = st.radio("Selecione a base de cálculo:", 
                        [f"Grupo 1 (XMLs): R$ {st.session_state.total_g1:,.2f}", 
                         f"Grupo 2 (Planilha): R$ {st.session_state.total_g2:,.2f}",
                         f"CONCILIADO (Soma Aba 1 + Aba 2): R$ {soma_conciliada:,.2f}"])

    # Lógica de seleção de valor base incluindo a soma
    if "Grupo 1" in base_xml:
        valor_base = st.session_state.total_g1
    elif "Grupo 2" in base_xml:
        valor_base = st.session_state.total_g2
    else:
        valor_base = soma_conciliada
    
    col1, col2 = st.columns(2)
    pgdas_declarado = col1.number_input("Valor ST declarado no PGDAS (R$)", min_value=0.0, format="%.2f")
    aliq_efetiva = col2.number_input("Alíquota Efetiva Simples (%)", value=8.5)

    if st.button("🚀 Calcular e Gerar Relatório"):
        diferenca = valor_base - pgdas_declarado
        if diferenca > 0:
            credito = (diferenca * (aliq_efetiva / 100)) * 0.335
            
            # Salva no session state para o download não sumir ao clicar
            st.session_state.res_final = {
                "base": valor_base,
                "pgdas": pgdas_declarado,
                "dif": diferenca,
                "cred": credito,
                "aliq": aliq_efetiva
            }
            st.session_state.calculo_realizado = True
        else:
            st.error("Não há diferença positiva para recuperação.")
            st.session_state.calculo_realizado = False

    # Exibição do Resultado e Botão de PDF
    if st.session_state.calculo_realizado:
        res = st.session_state.res_final
        st.markdown("---")
        st.subheader("Resultado do Diagnóstico")
        c1, c2, c3 = st.columns(3)
        c1.metric("Diferença Base", f"R$ {res['dif']:,.2f}")
        c2.metric("Alíquota ICMS", "33.5% (do Simples)")
        c3.metric("Crédito Estimado", f"R$ {res['cred']:,.2f}")
        
        # Gerar o PDF
        pdf_bytes = gerar_pdf(empresa, res['base'], res['pgdas'], res['dif'], res['cred'], res['aliq'])
        
        st.download_button(
            label="📥 Baixar Relatório em PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_{empresa.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
# --- BOTÃO TEMPORÁRIO PARA GERAR PLANILHA DE TESTE ---
st.sidebar.markdown("---")
if st.sidebar.button("🛠️ Gerar Planilha de Teste"):
    data_teste = {
        'DATA': ['01/01/2024', '02/01/2024', '03/01/2024', '04/01/2024'],
        'NOTA': [101, 102, 103, 104],
        'CFOP': [5405, 5102, 5405, 6404],  # 5405 e 6404 são ST
        'VALOR': [1500.00, 2000.00, 3500.00, 5000.00],
        'PRODUTO': ['Tenis Esportivo', 'Meia Algodao', 'Sapato Couro', 'Bota Feminina']
    }
    df_teste = pd.DataFrame(data_teste)
    csv_teste = df_teste.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Baixar Planilha_Teste.csv",
        data=csv_teste,
        file_name="planilha_teste_auditoria.csv",
        mime="text/csv"
    )
