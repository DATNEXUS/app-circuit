import streamlit as st
import pandas as pd
import re
from PIL import Image
import numpy as np
import easyocr

st.set_page_config(page_title="Leitor de Rotas", layout="centered", page_icon="📱")
st.title("📱 Leitor de Prints de Rotas")

@st.cache_resource
def iniciar_leitor():
    return easyocr.Reader(['pt'])

reader = iniciar_leitor()

arquivos_prints = st.file_uploader("Escolha os prints da sua Galeria:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.button("🚀 Gerar CSV para o Circuit", use_container_width=True):
    if arquivos_prints:
        lista_enderecos, lista_finais, lista_quantidades = [], [], []
        
        for arquivo in arquivos_prints:
            try:
                imagem = Image.open(arquivo)
                resultado = reader.readtext(np.array(imagem), detail=0)
                
                # Agrupa o texto em blocos de paradas baseado no padrão "Estou chegando" ou quebras de seção
                texto_completo = "\n".join(resultado)
                # Divide o print pelas seções de cada entrega
                blocos = texto_completo.split("Estou chegando")
                
                for bloco in blocos:
                    linhas = [l.strip() for l in bloco.split("\n") if l.strip()]
                    if len(linhas) >= 2:
                        # Primeira linha tende a ser a rua e número
                        rua_num = linhas[0]
                        # Ignora se for lixo de sistema ou botões residuais
                        if "entrega" in rua_num.lower() or "cep" in rua_num.lower():
                            continue
                            
                        # Segunda linha tende a ser o Bairro e o CEP
                        bairro_cep = linhas[1]
                        match_cep = re.search(r'(\d{5}[-\s]?\d{3})', bairro_cep)
                        cep_limpo = re.sub(r'\D', '', match_cep.group(1)) if match_cep else ""
                        bairro = re.sub(r',?\s*CEP.*', '', bairro_cep, flags=re.IGNORECASE).strip()
                        
                        # Procura valores de volumes e código nas próximas linhas do bloco
                        qtd = "1"
                        final_etiq = "00"
                        for l in linhas:
                            if "unidade" in l.lower() or "vol" in l.lower():
                                match_qtd = re.search(r'(\d+)\s*unidade', l, re.IGNORECASE)
                                if match_qtd: qtd = match_qtd.group(1)
                            if "etiqueta" in l.lower() or "_" in l:
                                match_etiq = re.search(r'_(\d+)', l)
                                if match_etiq: final_etiq = match_etiq.group(1)[-2:]
                        
                        lista_enderecos.append(f"{rua_num}, {bairro} - CEP: {cep_limpo}".strip(" , -"))
                        lista_finais.append(f"Final: {final_etiq}")
                        lista_quantidades.append(f"Qtd: {qtd} vol")
            except:
                continue

        if lista_enderecos:
            df = pd.DataFrame({"Street Address": lista_enderecos, "First Name": lista_finais, "Notes": lista_quantidades})
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Baixar CSV para o Circuit", data=df.to_csv(index=False, encoding='utf-8').encode('utf-8'), file_name="rotas_circuit.csv", mime="text/csv", use_container_width=True)
