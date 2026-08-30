import streamlit as st
import pandas as pd
import re
from PIL import Image
import numpy as np
import easyocr

st.set_page_config(page_title="Leitor de Rotas", layout="centered", page_icon="📱")

st.title("📱 Leitor de Prints para Roteiros")
st.write("Selecione os prints da galeria (juntos ou um por vez).")

@st.cache_resource
def iniciar_leitor():
    return easyocr.Reader(['pt'], gpu=False)

try:
    reader = iniciar_leitor()
except Exception as e:
    st.error(f"Erro ao inicializar o motor de leitura: {e}")

if 'lista_paradas' not in st.session_state:
    st.session_state.lista_paradas = []

arquivos_prints = st.file_uploader(
    "Toque abaixo para abrir sua Galeria:", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if st.button("🚀 Processar Lote e Gerar CSV", use_container_width=True):
    if arquivos_prints:
        st.session_state.lista_paradas = []
        progresso = st.progress(0)
        total = len(arquivos_prints)
        
        for i, arquivo in enumerate(arquivos_prints):
            try:
                with Image.open(arquivo) as imagem:
                    imagem_np = np.array(imagem)
                    resultado = reader.readtext(imagem_np, detail=0)
                
                if not resultado:
                    continue
                
                # Guarda as informações temporárias de cada bloco detectado
                rua_atual = ""
                bairro_atual = ""
                cep_atual = ""
                qtd_atual = "1"
                final_etiq = "00"
                
                # Analisa linha por linha capturada pelo leitor de imagem
                for linha in resultado:
                    linha_limpa = linha.strip()
                    linha_lower = linha_limpa.lower()
                    
                    # 1. Identifica a Rua/Avenida e o Número
                    if any(p in linha_lower for p in ["rua", "av.", "avenida", "alameda", "travessa", "casa"]):
                        # Se já tínhamos uma rua guardada e achamos outra, salva a anterior primeiro
                        if rua_atual:
                            st.session_state.lista_paradas.append({
                                "Street Address": f"{rua_atual}, {bairro_atual} - CEP: {cep_atual}".strip(" , -"),
                                "First Name": f"Final: {final_etiq}",
                                "Notes": f"Qtd: {qtd_atual} vol"
                            })
                            # Reseta para a nova parada
                            bairro_atual, cep_atual, qtd_atual, final_etiq = "", "", "1", "00"
                        
                        rua_atual = linha_limpa
                    
                    # 2. Identifica o CEP (qualquer sequência de 5 números juntos ou com traço)
                    match_cep = re.search(r'(\d{5}[-\s]?\d{3})', linha_limpa)
                    if match_cep:
                        cep_atual = re.sub(r'\D', '', match_cep.group(1))
                        # Geralmente o bairro vem na mesma linha ou antes do CEP
                        if not bairro_atual:
                            bairro_atual = re.sub(r',?\s*CEP.*', '', linha_limpa, flags=re.IGNORECASE).strip()
                    
                    # 3. Identifica a Quantidade de volumes (Linha corrigida sem o erro de sintaxe)
                    if "unidade" in linha_lower or "vol" in linha_lower:
                        match_qtd = re.search(r'(\d+)', linha_limpa)
                        if match_qtd:
                            qtd_atual = match_qtd.group(1)
                    
                    # 4. Identifica o código da etiqueta (busca os 2 últimos dígitos de números de etiqueta)
                    if "_" in linha_limpa or len(re.sub(r'\D', '', linha_limpa)) >= 6:
                        match_etiq = re.search(r'(\d+)', linha_limpa)
                        if match_etiq:
                            num_completo = match_etiq.group(1)
                            final_etiq = num_completo[-2:] if len(num_completo) >= 2 else num_completo
                
                # Salva a última parada do print de tela
                if rua_atual:
                    st.session_state.lista_paradas.append({
                        "Street Address": f"{rua_atual}, {bairro_atual} - CEP: {cep_atual}".strip(" , -"),
                        "First Name": f"Final: {final_etiq}",
                        "Notes": f"Qtd: {qtd_atual} vol"
                    })
                    
            except Exception:
                continue
            
            progresso.progress((i + 1) / total)

        if st.session_state.lista_paradas:
            st.success(f"✓ {len(st.session_state.lista_paradas)} endereços processados!")
        else:
            st.error("Nenhum endereço contendo as palavras 'Rua', 'Av' ou 'CEP' foi identificado nas imagens.")

# --- EXIBIÇÃO DA TABELA E DOWNLOAD SEGURO ---
if st.session_state.lista_paradas:
    st.write("---")
    df_final = pd.DataFrame(st.session_state.lista_paradas)
    st.dataframe(df_final, use_container_width=True)
    
    csv_text = df_final.to_csv(index=False, encoding='utf-8')
    csv_bytes = csv_text.encode('utf-8')
    
    st.download_button(
        label="📥 Opção 1: Baixar Arquivo CSV",
        data=csv_bytes,
        file_name="roteiro_diario_circuit.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    st.write("---")
    st.subheader("💡 Plano B (Caso o botão acima não funcione)")
    st.write("Se o download falhar no celular, copie o texto do campo abaixo e jogue no seu Bloco de Notas:")
    st.text_area("Conteúdo do seu Roteiro (Copie daqui):", csv_text, height=250)
