import streamlit as st
import pandas as pd
import re
from PIL import Image
import numpy as np
import easyocr

# Configuração da página para visualização perfeita no celular
st.set_page_config(page_title="Leitor de Prints", layout="centered", page_icon="📱")

st.title("📱 Leitor de Prints para Circuit")
st.write("Selecione os prints da sua galeria para gerar o roteiro.")

# Inicializa o leitor de imagem (OCR) em português
@st.cache_resource
def iniciar_leitor():
    return easyocr.Reader(['pt'])

reader = iniciar_leitor()

# Botão adaptado para o celular (abre a galeria de fotos ou a câmera do aparelho)
arquivos_prints = st.file_uploader(
    "Escolha os prints das etiquetas:", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if st.button("🚀 Gerar CSV para o Circuit", use_container_width=True):
    if arquivos_prints:
        lista_enderecos = []
        lista_finais_etiqueta = []
        lista_quantidades = []
        
        barra_progresso = st.progress(0)
        total = len(arquivos_prints)
        
        for i, arquivo in enumerate(arquivos_prints):
            try:
                # Abre a imagem da galeria do celular
                imagem = Image.open(arquivo)
                imagem_np = np.array(imagem)
                
                # Extrai o texto do print de tela
                resultado = reader.readtext(imagem_np, detail=0)
                texto_print = " ".join(resultado)
                
                # Procura os dados específicos (Endereço, CEP, Qtd, Etiqueta)
                end_match = re.search(r'(?:Endereço|Rua|Logradouro|Local):\s*(.*?)(?:CEP|$)', texto_print, re.IGNORECASE)
                endereco = end_match.group(1).strip() if end_match else "Endereço não identificado"
                
                cep_match = re.search(r'CEP[:\s]*([\d\s-]+)', texto_print, re.IGNORECASE)
                cep_limpo = re.sub(r'\D', '', cep_match.group(1)) if cep_match else ""
                
                qtd_match = re.search(r'(?:Quantidade|Qtd|Pacotes|Volumes):\s*(\d+)', texto_print, re.IGNORECASE)
                quantidade = qtd_match.group(1) if qtd_match else "1"
                
                etiq_match = re.search(r'(?:Etiqueta|Nº|Código):\s*(\d+)', texto_print, re.IGNORECASE)
                if etiq_match:
                    num_completo = etiq_match.group(1).strip()
                    final_etiq = num_completo[-2:]
                else:
                    final_etiq = "00"
                
                # Formata a linha no padrão exato que o Circuit lê de primeira
                lista_enderecos.append(f"{endereco}, CEP: {cep_limpo}".strip(", CEP: ") if cep_limpo else endereco)
                lista_finais_etiqueta.append(f"Final Etiqueta: {final_etiq}")
                lista_quantidades.append(f"Qtd: {quantidade} vol")
                
            except Exception as e:
                st.warning(f"Erro ao ler uma das imagens da galeria.")
                continue
                
            barra_progresso.progress((i + 1) / total)
            
        if lista_enderecos:
            # Monta o DataFrame com os nomes de colunas que o Circuit reconhece no celular
            df = pd.DataFrame({
                "Street Address": lista_enderecos,
                "First Name": lista_finais_etiqueta,
                "Notes": lista_quantidades
            })
            
            st.success(f"✓ {len(df)} paradas processadas!")
            st.dataframe(df, use_container_width=True)
            
            # Converte para download
            csv_data = df.to_csv(index=False, encoding='utf-8').encode('utf-8')
            
            # Botão de download gigante para o celular
            st.download_button(
                label="📥 Baixar Roteiro e Abrir no Circuit",
                data=csv_data,
                file_name="rotas_celular.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.warning("Selecione ao menos um print na galeria.")

