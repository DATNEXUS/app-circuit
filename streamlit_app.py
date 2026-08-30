import streamlit as st
import pandas as pd
import re
from PIL import Image
import pytesseract

st.set_page_config(page_title="Leitor de Rotas", layout="centered", page_icon="📱")

st.title("📱 Leitor de Prints para Roteiros")
st.write("Selecione vários prints da sua galeria de uma vez só.")

# Configura o Tesseract para usar os caminhos corretos do servidor Linux
import shutil
pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

# Inicializa a lista de paradas na memória
if 'lista_paradas' not in st.session_state:
    st.session_state.lista_paradas = []

# Ativado para selecionar multiplas fotos de uma vez só na galeria do celular
arquivos_prints = st.file_uploader("Escolha os prints das ruas:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.button("🚀 Processar Imagens e Gerar CSV", use_container_width=True):
    if arquivos_prints:
        # Limpa o histórico anterior para gerar uma lista nova limpa
        st.session_state.lista_paradas = []
        
        barra_progresso = st.progress(0)
        total = len(arquivos_prints)
        
        for i, arquivo in enumerate(arquivos_prints):
            try:
                imagem = Image.open(arquivo)
                
                # Executa a leitura em português
                texto_completo = pytesseract.image_to_string(imagem, lang='por')
                
                # Divide o texto do print pelas seções de cada entrega
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
            except Exception as e:
                continue
            
            barra_progresso.progress((i + 1) / total)

        if st.session_state.lista_paradas:
            st.success(f"✓ Sucesso! {len(st.session_state.lista_paradas)} paradas encontradas nos prints.")
        else:
            st.error("Nenhum endereço foi reconhecido. Verifique se as imagens estão nítidas.")
    else:
        st.warning("Selecione as imagens antes de processar.")

# --- EXIBIÇÃO DO ACUMULADO DO DIA ---
if st.session_state.lista_paradas:
    st.write("---")
    df_final = pd.DataFrame(st.session_state.lista_paradas)
    st.dataframe(df_final, use_container_width=True)
    
    csv_data = df_final.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 Baixar CSV Completo para o Circuit",
        data=csv_data,
        file_name="roteiro_diario_circuit.csv",
        mime="text/csv",
        use_container_width=True
    )
