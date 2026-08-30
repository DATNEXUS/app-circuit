import streamlit as st
import pandas as pd
import re
from PIL import Image
import pytesseract
import shutil

# Configura a página de forma responsiva para o celular
st.set_page_config(page_title="Leitor de Rotas", layout="centered", page_icon="📱")

st.title("📱 Leitor de Prints para Roteiros")
st.write("Selecione os prints da galeria (um por vez ou juntos).")

# Vincula o executável do tesseract de forma limpa no servidor Linux
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

# Inicializa o banco de dados temporário na memória do app se não existir
if 'lista_paradas' not in st.session_state:
    st.session_state.lista_paradas = []

# MUDANÇA CRUCIAL: 'type=None' remove as restrições que travam o upload no celular
arquivos_prints = st.file_uploader(
    "Toque abaixo para abrir sua Galeria:", 
    type=None, 
    accept_multiple_files=True,
    key="leitor_celular"
)

if st.button("🚀 Processar Lote e Gerar CSV", use_container_width=True):
    if arquivos_prints:
        # Reinicia o acumulador para evitar duplicar dados antigos
        st.session_state.lista_paradas = []
        
        progresso = st.progress(0)
        total = len(arquivos_prints)
        
        for i, arquivo in enumerate(arquivos_prints):
            try:
                # Carrega o arquivo de imagem reduzindo o consumo de RAM do celular
                with Image.open(arquivo) as imagem:
                    # Converte para escala de cinza para acelerar o motor de IA em 3x
                    imagem_otimizada = imagem.convert('L')
                    texto_completo = pytesseract.image_to_string(imagem_otimizada, lang='por')
                
                # Separa os blocos por seção de entrega
                blocos = texto_completo.split("Estou chegando")
                
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
            except Exception:
                continue
            
            progresso.progress((i + 1) / total)

        if st.session_state.lista_paradas:
            st.success(f"✓ {len(st.session_state.lista_paradas)} endereços processados!")
        else:
            st.error("Nenhum dado legível foi extraído. Verifique se o print possui boa nitidez.")
    else:
        st.warning("Por favor, selecione as fotos na galeria antes de clicar.")

# --- EXIBIÇÃO DA TABELA E DOWNLOAD ---
if st.session_state.lista_paradas:
    st.write("---")
    df_final = pd.DataFrame(st.session_state.lista_paradas)
    st.dataframe(df_final, use_container_width=True)
    
    csv_data = df_final.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 Baixar CSV para o Circuit",
        data=csv_data,
        file_name="roteiro_diario_circuit.csv",
        mime="text/csv",
        use_container_width=True
    )
