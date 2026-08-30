import streamlit as st
import pandas as pd
import re
from PIL import Image
import pytesseract

st.set_page_config(page_title="Leitor Leve Celular", layout="centered", page_icon="📱")

st.title("📱 Leitor de Prints para Roteiros")
st.write("Suba um print por vez para acumular e gerar sua lista do Circuit.")

# Inicializa a lista de paradas na memória se ela não existir
if 'lista_paradas' not in st.session_state:
    st.session_state.lista_paradas = []

# Upload simples e leve para celular
arquivo_print = st.file_uploader("Selecione um print da Galeria:", type=["png", "jpg", "jpeg"])

if arquivo_print:
    if st.button("➕ Adicionar esta Imagem à Lista", use_container_width=True):
        try:
            with st.spinner("📖 Processando imagem instantaneamente..."):
                imagem = Image.open(arquivo_print)
                
                # Executa o leitor leve nativo do servidor em português
                texto_completo = pytesseract.image_to_string(imagem, lang='por')
                
                # Divide o texto do print pelas seções de cada entrega
                blocos = texto_completo.split("Estou chegando")
                
                contador_locais = 0
                for bloco in blocos:
                    linhas = [l.strip() for l in bloco.split("\n") if l.strip()]
                    if len(linhas) >= 2:
                        rua_num = linhas[0]
                        if "entrega" in rua_num.lower() or "cep" in rua_num.lower() or len(rua_num) < 5:
                            continue
                            
                        bairro_cep = linhas[1]
                        match_cep = re.search(r'(\d{5}[-\s]?\d{3})', bairro_cep)
                        cep_limpo = re.sub(r'\D', '', match_cep.group(1)) if match_cep else ""
                        bairro = re.sub(r',?\s*CEP.*', '', bairro_cep, flags=re.IGNORECASE).strip()
                        
                        qtd = "1"
                        final_etiq = "00"
                        for l in linhas:
                            if "unidade" in l.lower():
                                match_qtd = re.search(r'(\d+)\s*unidade', l, re.IGNORECASE)
                                if match_qtd: qtd = match_qtd.group(1)
                            if "etiqueta" in l.lower() or "_" in l:
                                match_etiq = re.search(r'_(\d+)', l)
                                if match_etiq: final_etiq = match_etiq.group(1)[-2:]
                        
                        st.session_state.lista_paradas.append({
                            "Street Address": f"{rua_num}, {bairro} - CEP: {cep_limpo}".strip(" , -"),
                            "First Name": f"Final: {final_etiq}",
                            "Notes": f"Qtd: {qtd} vol"
                        })
                        contador_locais += 1
                
                if contador_locais > 0:
                    st.success(f"✓ Mais {contador_locais} endereços adicionados com sucesso!")
                else:
                    st.warning("Texto lido, mas nenhum endereço padrão foi identificado. Tente outro print.")
        except Exception as e:
            st.error(f"Erro ao processar imagem: {e}")

# --- EXIBIÇÃO DO ACUMULADO DO DIA ---
if st.session_state.lista_paradas:
    st.write("---")
    st.subheader(f"📋 Lista Acumulada ({len(st.session_state.lista_paradas)} paradas)")
    
    df_final = pd.DataFrame(st.session_state.lista_paradas)
    st.dataframe(df_final, use_container_width=True)
    
    csv_data = df_final.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 Baixar CSV Completo para o Circuit",
        data=csv_data,
        file_name="roteiro_acumulado_circuit.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    if st.button("🗑️ Limpar Lista Atual", type="secondary", use_container_width=True):
        st.session_state.lista_paradas = []
        st.st.rerun()
