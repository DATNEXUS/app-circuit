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
                
                texto_completo = "\n".join(resultado)
                blocos = texto_completo.split("Estou chegando")
                
                for bloco in blocos:
                    linhas = [l.strip() for l in bloco.split("\n") if l.strip()]
                    if len(linhas) >= 2:
                        rua_num = linhas
                        if "entrega" in rua_num.lower() or "cep" in rua_num.lower() or len(rua_num) < 5:
                            continue
                            
                        bairro_cep = linhas
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
            except Exception as e:
                continue
            
            progresso.progress((i + 1) / total)

        if st.session_state.lista_paradas:
            st.success(f"✓ {len(st.session_state.lista_paradas)} endereços processados!")
        else:
            st.error("Nenhum dado legível foi extraído. Verifique os arquivos selecionados.")

# --- EXIBIÇÃO DA TABELA E DOWNLOAD SEGURO ---
if st.session_state.lista_paradas:
    st.write("---")
    df_final = pd.DataFrame(st.session_state.lista_paradas)
    st.dataframe(df_final, use_container_width=True)
    
    # Conversão do DataFrame para Texto CSV puro
    csv_text = df_final.to_csv(index=False, encoding='utf-8')
    csv_bytes = csv_text.encode('utf-8')
    
    # Opção 1: Botão de baixar tradicional
    st.download_button(
        label="📥 Opção 1: Baixar Arquivo CSV",
        data=csv_bytes,
        file_name="roteiro_diario_circuit.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Opção 2: Plano B caso o celular bloqueie o download
    st.write("---")
    st.subheader("💡 Plano B (Caso o botão acima não funcione)")
    st.write("Se o download falhar, pressione e segure o texto abaixo, copie tudo e cole no seu Bloco de Notas salvando como rotas.csv:")
    st.text_area("Conteúdo do seu Roteiro (Copie daqui):", csv_text, height=250)
