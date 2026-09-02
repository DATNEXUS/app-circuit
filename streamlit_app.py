import streamlit as st
import pandas as pd
import re
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import numpy as np
import easyocr

st.set_page_config(
    page_title="Leitor de Rotas",
    layout="centered",
    page_icon="📱"
)

st.title("📱 Leitor de Prints para Roteiros")
st.write("Envie os prints da rota. O sistema tenta identificar endereço, bairro, CEP, quantidade e final da etiqueta.")

# ============================================================
# CONFIGURAÇÃO DO LEITOR OCR
# ============================================================

@st.cache_resource
def iniciar_leitor():
    return easyocr.Reader(["pt"], gpu=False)

try:
    reader = iniciar_leitor()
except Exception as e:
    st.error(f"Erro ao inicializar o motor de leitura: {e}")
    st.stop()


# ============================================================
# ESTADO
# ============================================================

if "lista_paradas" not in st.session_state:
    st.session_state.lista_paradas = []

if "resultado_ocr" not in st.session_state:
    st.session_state.resultado_ocr = []


# ============================================================
# FUNÇÕES DE LIMPEZA E NORMALIZAÇÃO
# ============================================================

def limpar_texto(texto):
    """Remove espaços duplicados e caracteres invisíveis."""
    texto = str(texto or "")
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_ocr(texto):
    """
    Corrige alguns erros comuns do OCR sem alterar excessivamente
    nomes de ruas ou bairros.
    """
    texto = limpar_texto(texto)

    # Correções somente quando aparecem como palavras isoladas.
    substituicoes = {
        r"\bRUA\b": "Rua",
        r"\bR\b": "Rua",
        r"\bAV\b": "Av",
        r"\bAVENIDA\b": "Avenida",
        r"\bALAMEDA\b": "Alameda",
        r"\bTRAVESSA\b": "Travessa",
    }

    for padrao, substituicao in substituicoes.items():
        texto = re.sub(padrao, substituicao, texto, flags=re.IGNORECASE)

    return texto.strip()


def somente_digitos(texto):
    return re.sub(r"\D", "", str(texto or ""))


# ============================================================
# PREPARAÇÃO DA IMAGEM
# ============================================================

def preparar_imagem(imagem):
    """
    Prepara o print para o OCR:
    - converte para RGB;
    - aumenta a resolução;
    - melhora contraste e nitidez.
    """
    imagem = imagem.convert("RGB")

    # Aumenta a imagem para ajudar o OCR em textos pequenos.
    largura, altura = imagem.size
    escala = 2.0

    imagem = imagem.resize(
        (int(largura * escala), int(altura * escala)),
        Image.Resampling.LANCZOS
    )

    imagem = ImageOps.autocontrast(imagem)
    imagem = ImageEnhance.Contrast(imagem).enhance(1.15)
    imagem = ImageEnhance.Sharpness(imagem).enhance(1.25)
    imagem = imagem.filter(ImageFilter.SHARPEN)

    return np.array(imagem)


# ============================================================
# EXTRAÇÃO DE CEP
# ============================================================

def extrair_cep(texto):
    """
    Aceita CEP no formato 00000-000, 00000 000 ou 00000000.
    """
    texto = str(texto or "")

    padroes = [
        r"\b(\d{5})[-\s]?(\d{3})\b",
    ]

    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            cep = f"{match.group(1)}{match.group(2)}"
            return cep

    return ""


# ============================================================
# EXTRAÇÃO DE QUANTIDADE
# ============================================================

def extrair_quantidade(texto):
    """
    Procura quantidade somente quando há indicação de volume/unidade/
    pacote/quantidade. Isso evita confundir número de endereço com qtd.
    """
    texto_lower = str(texto or "").lower()

    palavras_qtd = [
        "unidade",
        "unidades",
        "volume",
        "volumes",
        "vol",
        "pacote",
        "pacotes",
        "qtd",
        "quantidade",
    ]

    if not any(palavra in texto_lower for palavra in palavras_qtd):
        return ""

    # Exemplos: Qtd: 3, 3 volumes, 3 vol, 3 pacotes.
    padroes = [
        r"(?:qtd|quantidade)\s*[:\-]?\s*(\d+)",
        r"(\d+)\s*(?:unidades?|volumes?|vol|pacotes?)\b",
        r"(?:unidades?|volumes?|vol|pacotes?)\s*[:\-]?\s*(\d+)",
    ]

    for padrao in padroes:
        match = re.search(padrao, texto_lower)
        if match:
            return match.group(1)

    return ""


# ============================================================
# EXTRAÇÃO DO FINAL DA ETIQUETA
# ============================================================

def extrair_final_etiqueta(texto):
    """
    Procura códigos longos ou códigos separados por "_" e retorna
    somente os 2 últimos dígitos, conforme o padrão usado no projeto.
    """
    texto = str(texto or "")

    # Prioridade para códigos que tenham "_".
    if "_" in texto:
        grupos = re.findall(r"\d+", texto)
        if grupos:
            numero = grupos[-1]
            if len(numero) >= 2:
                return numero[-2:]
            return numero

    # Procura sequências de pelo menos 6 dígitos.
    numeros = re.findall(r"\d{6,}", texto)

    if numeros:
        numero = max(numeros, key=len)
        return numero[-2:]

    return ""


# ============================================================
# IDENTIFICAÇÃO DE ENDEREÇO
# ============================================================

PREFIXOS_RUA = (
    "rua ",
    "r. ",
    "r ",
    "avenida ",
    "av. ",
    "av ",
    "alameda ",
    "travessa ",
    "tv. ",
    "estrada ",
    "rodovia ",
    "praça ",
    "praca ",
    "largo ",
    "beco ",
)

def parece_endereco(texto):
    """
    Identifica uma linha que provavelmente representa logradouro.
    Não considera 'casa' como endereço, pois isso gerava falsos positivos.
    """
    texto_lower = limpar_texto(texto).lower()

    if not texto_lower:
        return False

    if any(texto_lower.startswith(prefixo) for prefixo in PREFIXOS_RUA):
        return True

    # Também aceita logradouros em que o OCR não capturou corretamente
    # o prefixo, desde que exista número de endereço.
    tem_numero = bool(re.search(r"\b\d{1,6}[A-Za-z]?\b", texto_lower))
    palavras_logradouro = [
        "rua", "avenida", "alameda", "travessa", "estrada",
        "rodovia", "praça", "praca", "largo", "beco"
    ]

    return tem_numero and any(p in texto_lower for p in palavras_logradouro)


# ============================================================
# LIMPEZA DO LOGRADOURO
# ============================================================

def limpar_endereco(texto):
    texto = normalizar_ocr(texto)

    # Remove CEP se ele estiver na mesma linha.
    texto = re.sub(
        r",?\s*(?:cep\s*)?\d{5}[-\s]?\d{3}\b",
        "",
        texto,
        flags=re.IGNORECASE
    )

    texto = re.sub(r"\s*,\s*", ", ", texto)
    texto = re.sub(r",\s*,+", ", ", texto)
    texto = texto.strip(" ,;-")

    return texto


# ============================================================
# PROCESSAMENTO DO OCR
# ============================================================

def ler_print(imagem):
    imagem_np = preparar_imagem(imagem)

    # detail=1 permite receber coordenadas e confiança.
    resultado = reader.readtext(
        imagem_np,
        detail=1,
        paragraph=False,
        text_threshold=0.45,
        low_text=0.25,
        link_threshold=0.25,
        mag_ratio=1.0
    )

    linhas = []

    for item in resultado:
        if len(item) != 3:
            continue

        caixa, texto, confianca = item

        texto = normalizar_ocr(texto)

        if not texto:
            continue

        try:
            confianca = float(confianca)
        except Exception:
            confianca = 0.0

        linhas.append({
            "texto": texto,
            "confianca": confianca,
            "caixa": caixa
        })

    # Ordena por posição vertical e depois horizontal.
    linhas.sort(
        key=lambda item: (
            min(p[1] for p in item["caixa"]),
            min(p[0] for p in item["caixa"])
        )
    )

    return linhas


# ============================================================
# MONTA AS PARADAS
# ============================================================

def montar_paradas(linhas):
    """
    Percorre o OCR e cria uma parada por logradouro identificado.

    Importante:
    - bairro, CEP, quantidade e etiqueta ficam associados à parada atual;
    - não mistura informações de uma parada com outra;
    - números isolados não são tratados automaticamente como rua.
    """

    paradas = []

    atual = None

    def nova_parada(endereco):
        return {
            "Street Address": limpar_endereco(endereco),
            "First Name": "",
            "Notes": "",
            "_bairro": "",
            "_cep": "",
            "_qtd": "",
            "_final": "",
        }

    def finalizar_parada(parada):
        if not parada:
            return

        endereco = parada["Street Address"]

        bairro = limpar_texto(parada.get("_bairro", ""))
        cep = somente_digitos(parada.get("_cep", ""))
        qtd = parada.get("_qtd", "")
        final = parada.get("_final", "")

        partes_endereco = [endereco]

        if bairro:
            # Evita repetir o bairro caso o OCR já o tenha colocado no endereço.
            if bairro.lower() not in endereco.lower():
                partes_endereco.append(bairro)

        endereco_final = ", ".join([p for p in partes_endereco if p])

        if cep:
            endereco_final += f" - CEP: {cep}"

        parada_final = {
            "Street Address": endereco_final.strip(" ,"),
            "First Name": f"FINAL: {final}" if final else "",
            "Notes": f"Qtd: {qtd} vol" if qtd else "",
        }

        # Não salva endereço vazio.
        if parada_final["Street Address"]:
            paradas.append(parada_final)

    for item in linhas:
        texto = item["texto"]
        texto_lower = texto.lower()

        # --------------------------------------------------------
        # 1. Detecta novo endereço
        # --------------------------------------------------------
        if parece_endereco(texto):
            if atual is not None:
                finalizar_parada(atual)

            atual = nova_parada(texto)

            # Se CEP estiver na própria linha, já captura.
            cep = extrair_cep(texto)
            if cep:
                atual["_cep"] = cep

            qtd = extrair_quantidade(texto)
            if qtd:
                atual["_qtd"] = qtd

            final = extrair_final_etiqueta(texto)
            if final:
                atual["_final"] = final

            continue

        # Ignora informações antes de existir um endereço.
        if atual is None:
            continue

        # --------------------------------------------------------
        # 2. CEP
        # --------------------------------------------------------
        cep = extrair_cep(texto)
        if cep:
            atual["_cep"] = cep

            # Se houver texto útil além do CEP, pode ser bairro.
            sem_cep = re.sub(
                r"\b\d{5}[-\s]?\d{3}\b",
                "",
                texto,
                flags=re.IGNORECASE
            ).strip(" ,-")

            if sem_cep and not atual["_bairro"]:
                # Evita guardar "CEP" como bairro.
                if sem_cep.lower() not in ("cep", "c e p"):
                    atual["_bairro"] = sem_cep

            continue

        # --------------------------------------------------------
        # 3. Quantidade
        # --------------------------------------------------------
        qtd = extrair_quantidade(texto)
        if qtd:
            atual["_qtd"] = qtd
            continue

        # --------------------------------------------------------
        # 4. Final da etiqueta
        # --------------------------------------------------------
        final = extrair_final_etiqueta(texto)
        if final:
            atual["_final"] = final
            continue

        # --------------------------------------------------------
        # 5. Bairro
        # --------------------------------------------------------
        # Só considera como bairro linhas textuais, evitando capturar
        # números isolados como bairro.
        if not atual["_bairro"]:
            candidato = limpar_texto(texto)

            palavras_bairro = [
                "bairro", "jardim", "jd.", "vila", "parque",
                "assunção", "assuncao", "centro"
            ]

            if any(p in texto_lower for p in palavras_bairro):
                candidato = re.sub(
                    r"^\s*bairro\s*[:\-]?\s*",
                    "",
                    candidato,
                    flags=re.IGNORECASE
                )
                atual["_bairro"] = candidato.strip(" ,-")

    # Finaliza a última parada.
    if atual is not None:
        finalizar_parada(atual)

    return paradas


# ============================================================
# REMOÇÃO DE DUPLICADOS
# ============================================================

def normalizar_chave_endereco(endereco):
    texto = limpar_texto(endereco).lower()
    texto = re.sub(r"[^a-z0-9áàâãéêíóôõúç\s,.-]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def remover_duplicados(paradas):
    """
    Não duplica o mesmo endereço.
    Se o mesmo endereço aparecer mais de uma vez, tenta somar
    quantidades quando ambas forem numéricas.
    """
    mapa = {}

    for parada in paradas:
        chave = normalizar_chave_endereco(parada["Street Address"])

        if not chave:
            continue

        if chave not in mapa:
            mapa[chave] = parada.copy()
            continue

        existente = mapa[chave]

        # Soma quantidade somente se ambas estiverem claramente em formato numérico.
        qtd1 = re.search(r"Qtd:\s*(\d+)", existente.get("Notes", ""))
        qtd2 = re.search(r"Qtd:\s*(\d+)", parada.get("Notes", ""))

        if qtd1 and qtd2:
            total = int(qtd1.group(1)) + int(qtd2.group(1))
            existente["Notes"] = f"Qtd: {total} vol"
        elif not existente.get("Notes") and parada.get("Notes"):
            existente["Notes"] = parada["Notes"]

        # Se o primeiro não tiver final de etiqueta, usa o segundo.
        if not existente.get("First Name") and parada.get("First Name"):
            existente["First Name"] = parada["First Name"]

    return list(mapa.values())


# ============================================================
# UPLOAD
# ============================================================

arquivos_prints = st.file_uploader(
    "Toque abaixo para abrir sua Galeria:",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)


# ============================================================
# PROCESSAR
# ============================================================

if st.button("🚀 Processar Lote e Gerar CSV", use_container_width=True):

    if not arquivos_prints:
        st.warning("Selecione pelo menos um print.")
        st.stop()

    st.session_state.lista_paradas = []
    st.session_state.resultado_ocr = []

    progresso = st.progress(0)
    total = len(arquivos_prints)

    todas_paradas = []

    for i, arquivo in enumerate(arquivos_prints):

        try:
            imagem = Image.open(arquivo)

            linhas = ler_print(imagem)

            st.session_state.resultado_ocr.append({
                "arquivo": arquivo.name,
                "linhas": linhas
            })

            paradas = montar_paradas(linhas)
            todas_paradas.extend(paradas)

        except Exception as e:
            st.warning(
                f"Não foi possível processar '{arquivo.name}': {e}"
            )

        progresso.progress((i + 1) / total)

    # Remove duplicidades.
    st.session_state.lista_paradas = remover_duplicados(todas_paradas)

    if st.session_state.lista_paradas:
        st.success(
            f"✓ {len(st.session_state.lista_paradas)} endereços identificados."
        )
    else:
        st.error(
            "Nenhum endereço foi identificado. "
            "Confira a qualidade dos prints e tente novamente."
        )


# ============================================================
# EXIBIÇÃO
# ============================================================

if st.session_state.lista_paradas:

    st.write("---")
    st.subheader("📋 Conferência antes do CSV")

    df_final = pd.DataFrame(st.session_state.lista_paradas)

    # Garante a ordem esperada pelo arquivo.
    colunas = ["Street Address", "First Name", "Notes"]
    df_final = df_final[[c for c in colunas if c in df_final.columns]]

    st.dataframe(
        df_final,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    csv_text = df_final.to_csv(
        index=False,
        encoding="utf-8"
    )

    csv_bytes = csv_text.encode("utf-8")

    st.download_button(
        label="📥 Baixar Arquivo CSV",
        data=csv_bytes,
        file_name="roteiro_diario_circuit.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.write("---")

    # --------------------------------------------------------
    # PLANO B
    # --------------------------------------------------------

    st.subheader("💡 Plano B")

    st.write(
        "Se o botão de download não funcionar no celular, "
        "copie o conteúdo abaixo."
    )

    st.text_area(
        "Conteúdo do CSV:",
        csv_text,
        height=300
    )

    # --------------------------------------------------------
    # DIAGNÓSTICO DO OCR
    # --------------------------------------------------------

    with st.expander("🔎 Ver leitura original dos prints"):

        st.write(
            "Use esta área para conferir o que o OCR realmente enxergou. "
            "Ela é importante quando algum endereço sair errado."
        )

        for resultado in st.session_state.resultado_ocr:
            st.markdown(f"**{resultado['arquivo']}**")

            for item in resultado["linhas"]:
                st.write(
                    f"- {item['texto']} "
                    f"(confiança: {item['confianca']:.2f})"
                )

else:
    st.info(
        "Envie os prints e toque em 'Processar Lote e Gerar CSV'."
    )
