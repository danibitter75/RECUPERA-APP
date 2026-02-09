import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.express as px
from fpdf import FPDF

# --- FUNÇÃO PDF ---
def gerar_pdf(empresa, base_xml, base_pgdas, diferenca, credito, aliquota):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Relatorio de Diagnostico Fiscal - Calcados", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Empresa: {empresa}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, "Analise: Recuperacao de ICMS (Simples Nacional)", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
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
    pdf.set_text_color(0, 128, 0)
    pdf.cell(0, 10, f"CREDITO ESTIMADO PARA RECUPERACAO: R$ {credito:,.2f}", ln=True)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 10, f"\nNota: Este calculo baseia-se na aliquota efetiva de {aliquota}% informada, aplicando o fator de 33,5% referente a parcela de ICMS do Simples Nacional.")
    return pdf.output(dest="S").encode("latin-1")

# Inicializa variáveis
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

# --- 2. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Módulo 1: Extração e Importação", layout="wide")
st.title("👞 Auditoria de Calçados - Grupo 1")

# Nome da Empresa para o PDF
empresa = st.sidebar.text_input("Nome do Cliente/Empresa", value="Empresa Exemplo")

aba_xml, aba_excel, aba_pgdas = st.tabs(["📥 Processar XML´s Avulsos", "📊 Importar XML´s por Planilha (Excel/CSV)", "📄 PGDAS"])

cfops_st = ['5401', '5402', '5403', '5405', '6401', '6403', '6404']

# --- ABA 1: XML ---
with aba_xml:
    st.markdown("### Leitura Direta de Arquivos XML")
    arquivos = st.file_uploader("Arraste os XMLs aqui", accept_multiple_files=True, type=['xml'], key="xml_up")
    lista_final = []
    if arquivos:
        soma_temp = 0.0
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
                    if tem_st:
                        soma_temp += v_prod
                    lista_final.append({
                        "Nota": n_nfe, "Data": data_emi, "Produto": x_prod,
                        "NCM": ncm, "CFOP": cfop, "CSOSN": csosn, "Valor": v_prod,
                        "Operação ST?": "Sim" if tem_st else "Não"
                    })
            except Exception as e:
                st.error(f"Erro no XML {arquivo.name}: {e}")
        st.session_state.total_g1 = soma_temp

# --- ABA 2: EXCEL ---
with aba_excel:
    st.markdown("### Importar Relatório de Itens (ERP)")
    arquivo_planilha = st.file_uploader("Upload Excel ou CSV", type=['xlsx', 'csv'], key="excel_up")
    if arquivo_planilha:
        try:
            df_importado = pd.read_csv(arquivo_planilha) if arquivo_planilha.name.endswith('.csv') else pd.read_excel(arquivo_planilha)
            df_importado.columns = [c.upper() for c in df_importado.columns]
            if 'CFOP' in df_importado.columns:
                df_importado['CFOP'] = df_importado['CFOP'].astype(str).str.replace('.0', '', regex=False)
                df_importado['Operação ST?'] = df_importado['CFOP'].apply(lambda x: "Sim" if x in cfops_st else "Não")
            
            valor_col = 'VALOR' if 'VALOR' in df_importado.columns else 'Valor'
            if valor_col in df_importado.columns:
                st.session_state.total_g2 = df_importado[df_importado["Operação ST?"] == "Sim"][valor_col].sum()
            
            lista_final = df_importado.to_dict('records')
            st.success("Planilha importada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao ler planilha: {e}")

# --- ABA 3: PGDAS (CORRIGIDA PARA O PDF APARECER) ---
# --- ABA 3: PGDAS (VERSÃO FINAL COM FIX DO PDF) ---
with aba_pgdas:
    st.header("📊 Cálculo de Recuperação Tributária")
    
    # Busca os totais salvos nas abas 1 e 2
    g1_disponivel = st.session_state.get('total_g1', 0.0)
    g2_disponivel = st.session_state.get('total_g2', 0.0)

    if g1_disponivel == 0 and g2_disponivel == 0:
        st.warning("⚠️ Nenhum dado de XML foi processado nas Abas 1 ou 2 ainda.")
    else:
        with st.container(border=True):
            st.markdown("### 📝 Dados do Confronto")
            origem = st.radio("Qual base de XML deseja utilizar?", ["Grupo 1", "Grupo 2"], horizontal=True)
            base_escolhida = g1_disponivel if origem == "Grupo 1" else g2_disponivel
            
            st.info(f"Base de XML selecionada: **R$ {base_escolhida:,.2f}**")

            col1, col2 = st.columns(2)
            valor_pgdas_st = col1.number_input("Valor de ST já declarado no PGDAS (R$)", min_value=0.0, format="%.2f", key="pgdas_val")
            aliquota_simples = col2.number_input("Alíquota Efetiva do Simples (%)", min_value=0.0, value=8.5, step=0.1, key="aliq_val")

        # BOTÃO DE CÁLCULO
        if st.button("🚀 Calcular Crédito Recuperável"):
            diferenca_base = base_escolhida - valor_pgdas_st
            
            if diferenca_base > 0:
                credito_final = (diferenca_base * (aliquota_simples / 100)) * 0.335
                
                # Exibe os resultados na tela
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.metric("Diferença de Faturamento ST", f"R$ {diferenca_base:,.2f}")
                c2.metric("Crédito de ICMS Estimado", f"R$ {credito_final:,.2f}")
                st.success(f"💰 Valor estimado para recuperação: **R$ {credito_final:,.2f}**")
                
                # GERAÇÃO DO PDF IMEDIATA
                try:
                    # O segredo: Geramos o PDF e já oferecemos o download no mesmo bloco
                    pdf_data = gerar_pdf(empresa, base_escolhida, valor_pgdas_st, diferenca_base, credito_final, aliquota_simples)
                    
                    st.download_button(
                        label="📥 Baixar Relatório em PDF",
                        data=pdf_data,
                        file_name=f"Relatorio_{empresa.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key="btn_pdf_download"
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro técnico ao gerar PDF: {e}")
                    st.info("Dica: Verifique se 'fpdf' está no seu arquivo requirements.txt")
            else:
                st.error("❌ A base declarada no PGDAS é maior ou igual aos XMLs. Não há crédito.")
# --- RESULTADOS CONSOLIDADOS ---
st.markdown("---")
if lista_final:
    df = pd.DataFrame(lista_final)
    if 'NCM' in df.columns:
        df['NCM'] = df['NCM'].astype(str)
        df['Calçado?'] = df['NCM'].apply(lambda x: "Sim" if x.startswith('64') else "Não")
    st.subheader("📋 Relatório Consolidado para Auditoria")
    st.dataframe(df, use_container_width=True)
    val_col = 'VALOR' if 'VALOR' in df.columns else 'Valor'
    total_st = df[df["Operação ST?"] == "Sim"][val_col].sum()
    st.success(f"**Total identificado com ST nesta carga:** R$ {total_st:,.2f}")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Exportar Resultado Final", csv, "auditoria_consolidada.csv", "text/csv")
else:
    st.warning("Aguardando upload dos arquivos.")
