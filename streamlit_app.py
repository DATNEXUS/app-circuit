import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json

st.set_page_config(page_title="Leitor de Rotas - Circuit", page_icon="🚚", layout="centered")

st.title("🚚 Meu Leitor de Etiquetas")
st.write("Transforme seus prints de entrega no arquivo correto para o Circuit.")

# Campo para salvar a chave do Google
api_key = st.text_input("Cole sua Gemini API Key aqui:", type="password")

st.markdown("---")
st.subheader("📸 Forma 1: Enviar um arquivo por vez")
# Primeiro campo caso seu celular só aceite selecionar 1 arquivo
uploaded_file = st.file_uploader("Escolha o print 1:", type=["png", "jpg", "jpeg"], key="file1")
uploaded_file2 = st.file_uploader("Escolha o print 2 (Opcional):", type=["png", "jpg", "jpeg"], key="file2")
uploaded_file3 = st.file_uploader("Escolha o print 3 (Opcional):", type=["png", "jpg", "jpeg"], key="file3")
uploaded_file4 = st.file_uploader("Escolha o print 4 (Opcional):", type=["png", "jpg", "jpeg"], key="file4")

st.markdown("---")
st.subheader("📂 Forma 2: Enviar múltiplos arquivos juntos")
# Segundo campo (se o seu navegador liberar a seleção múltipla)
uploaded_multiple = st.file_uploader("Selecione os 4 prints juntos aqui:", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="multiple")

# Junta todos os arquivos que foram colocados em qualquer uma das duas opções
all_uploaded_files = []
if uploaded_file: all_uploaded_files.append(uploaded_file)
if uploaded_file2: all_uploaded_files.append(uploaded_file2)
if uploaded_file3: all_uploaded_files.append(uploaded_file3)
if uploaded_file4: all_uploaded_files.append(uploaded_file4)
if uploaded_multiple: all_uploaded_files.extend(uploaded_multiple)

if all_uploaded_files:
    if not api_key:
        st.error("⚠️ Você precisa colar sua API Key no campo acima primeiro!")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
        all_rows = []
        
        with st.spinner("🧠 Lendo as imagens... Aguarde."):
            for index, file in enumerate(all_uploaded_files):
                image = Image.open(file)
                
                prompt = """
                Analise a imagem deste print de entrega e extraia as informações de endereço logístico.
                Você deve retornar a resposta estritamente no formato JSON, contendo uma lista de objetos.
                Cada objeto deve ter exatamente estas 4 chaves textuais: "Address", "Complement", "Packages", "Notes".
                
                Regras de preenchimento rígidas:
                1. "Address": Deve conter Nome da Rua, Número, Bairro, a cidade "Sao Bernardo do Campo - SP" e o CEP contendo apenas números (sem traço). Se o CEP do print for da Rua Castro, use obrigatoriamente 09850018. Exemplo: Rua Castro 25, Dos Casa, Sao Bernardo do Campo - SP, 09850018
                2. "Complement": Se houver informação de condomínio, bloco ou ponto de referência comercial, coloque TEXTO EM CAIXA ALTA. Caso contrário, deixe vazio ""
                3. "Packages": Coloque apenas o número isolado da quantidade de pacotes daquele endereço. Exemplo: 1
                4. "Notes": Deve conter estritamente a frase neste padrão e em CAIXA ALTA: ETIQUETA: XX - QTD: X (Substitua XX pelos dois últimos dígitos da etiqueta do pacote e X pela quantidade).
                
                Retorne apenas o JSON puro, sem marcações markdown de código.
                """
                
                try:
                    response = model.generate_content([prompt, image])
                    raw_text = response.text.strip()
                    
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                    elif raw_text.startswith("```"):
                        raw_text = raw_text.replace("```", "").strip()
                        
                    data_json = json.loads(raw_text)
                    if isinstance(data_json, list):
                        all_rows.extend(data_json)
                    else:
                        all_rows.append(data_json)
                except Exception as e:
                    st.error(f"Erro ao ler o print {index+1}: {e}")
        
        if all_rows:
            df = pd.DataFrame(all_rows)
            st.success("✅ Todos os arquivos processados com sucesso!")
            st.dataframe(df)
            
            csv_data = df.to_csv(index=False, sep=',').encode('utf-8')
            st.download_button(
                label="📥 BAIXAR ARQUIVO PARA O CIRCUIT",
                data=csv_data,
                file_name="lista_etiqueta_no_endereco.csv",
                mime="text/csv"
            )
