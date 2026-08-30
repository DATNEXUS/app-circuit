
import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json

st.set_page_config(page_title="Leitor de Rotas - Circuit", page_icon="🚚", layout="centered")

st.title("🚚 Meu Leitor de Etiquetas")
st.write("Transforme prints de entrega no arquivo correto para o Circuit instantaneamente.")

api_key = st.text_input("Cole sua Gemini API Key aqui:", type="password")
uploaded_files = st.file_uploader("Selecione ou tire foto dos prints:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if uploaded_files:
    if not api_key:
        st.error("⚠️ Você precisa colar sua API Key no campo acima primeiro!")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
        all_rows = []
        
        with st.spinner("🧠 Lendo os prints... Aguarde."):
            for index, file in enumerate(uploaded_files):
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
            st.success("✅ Processado com sucesso!")
            st.dataframe(df)
            
            csv_data = df.to_csv(index=False, sep=',').encode('utf-8')
            st.download_button(
                label="📥 BAIXAR ARQUIVO PARA O CIRCUIT",
                data=csv_data,
                file_name="lista_etiqueta_no_endereco.csv",
                mime="text/csv"
            )
