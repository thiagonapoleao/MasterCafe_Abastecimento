import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import unicodedata
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN (DARK MODE / CORPORATIVO)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Gestão de Visitas",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        .stApp {
            background-color: #0F172A;
            color: #F8FAFC;
        }
        .main-header {
            text-align: center;
            padding: 14px;
            border-radius: 10px;
            background: linear-gradient(135deg, #1E3A8A, #0D6EFD);
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        .status-box {
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 14px;
            border-radius: 8px;
            margin-bottom: 1.2rem;
            color: #F8FAFC;
        }
        div.stButton > button:first-child {
            width: 100%;
            border-radius: 8px;
            height: 48px;
            font-weight: bold;
            background-color: #0D6EFD;
            color: white;
            border: none;
        }
        div.stButton > button:first-child:hover {
            background-color: #0b5ed7;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. CONEXÃO COM A PLANILHA MASTER CAFÉ
# -------------------------------------------------------------
SPREADSHEET_ID = "1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU"

def normalizar_texto(texto):
    """Remove acentuações e espaços extras para busca de colunas."""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.strip().lower()

@st.cache_data(ttl=60)
def carregar_clientes():
    """
    Carrega os clientes da aba 'Clientes' filtrando a coluna 'Nome Fantasia'.
    """
    nome_aba = urllib.parse.quote("Clientes")
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={nome_aba}"

    try:
        df = pd.read_csv(
            url,
            engine="python",
            on_bad_lines="skip",
            dtype=str
        )

        coluna_cliente = None
        for col in df.columns:
            if normalizar_texto(col) == "nome fantasia":
                coluna_cliente = col
                break

        if coluna_cliente:
            lista = df[coluna_cliente].dropna().astype(str).str.strip()
            lista_filtrada = [item for item in lista.unique().tolist() if item != "" and item.lower() != "nan"]
            lista_filtrada.sort()
            return lista_filtrada
        else:
            return df.iloc[:, 0].dropna().unique().tolist()

    except Exception as e:
        st.error(f"Erro ao conectar com a planilha Google: {e}")
        return []

# -------------------------------------------------------------
# 3. FLUXO PRINCIPAL DO APLICATIVO
# -------------------------------------------------------------
def main():
    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Controle de Visitas e Abastecimento</p></div>', unsafe_allow_html=True)

    if "visita_ativa" not in st.session_state:
        st.session_state["visita_ativa"] = False
        st.session_state["dados_visita"] = {}

    # ---------------------------------------------------------
    # ETAPA 1: CHECK-IN
    # ---------------------------------------------------------
    if not st.session_state["visita_ativa"]:
        st.subheader("1. Iniciar Atendimento (Check-in)")

        lista_clientes = carregar_clientes()

        nome_abastecedora = st.text_input("Nome da Abastecedora:", placeholder="Ex: Maria Souza").strip()
        cliente_escolhido = st.selectbox(
            "Selecione o Cliente / Máquina:", 
            lista_clientes if lista_clientes else ["Carregando clientes..."]
        )

        st.caption("ℹ️ A geolocalização do aparelho será registrada automaticamente ao fazer o check-in.")
        loc_checkin = get_geolocation()

        if st.button("📍 Iniciar Visita (Check-in)"):
            if not nome_abastecedora:
                st.error("Informe o nome da abastecedora para iniciar.")
            elif not lista_clientes:
                st.error("Aguarde o carregamento da lista de clientes da planilha.")
            else:
                coords = loc_checkin["coords"] if loc_checkin else None
                lat = coords["latitude"] if coords else "GPS não detectado"
                lon = coords["longitude"] if coords else "GPS não detectado"

                st.session_state["visita_ativa"] = True
                st.session_state["dados_visita"] = {
                    "abastecedora": nome_abastecedora,
                    "cliente": cliente_escolhido,
                    "data_checkin": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "geo_checkin": f"{lat}, {lon}"
                }
                st.rerun()

    # ---------------------------------------------------------
    # ETAPA 2: CHECK-OUT E COMPROVAÇÕES
    # ---------------------------------------------------------
    else:
        dados = st.session_state["dados_visita"]

        st.markdown(f"""
            <div class="status-box">
                <b>Abastecedora:</b> {dados['abastecedora']}<br>
                <b>Cliente:</b> {dados['cliente']}<br>
                <b>Check-in:</b> {dados['data_checkin']}<br>
                <b>GPS Entrada:</b> {dados['geo_checkin']}
            </div>
        """, unsafe_allow_html=True)

        st.subheader("Fotos de Comprovação")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("1. Máquina Abastecida:")
            foto_abastecida = st.camera_input("Foto Abastecida", key="foto_abast")
        with col2:
            st.caption("2. Máquina Limpa:")
            foto_limpa = st.camera_input("Foto Limpa", key="foto_limp")

        st.subheader("Assinatura do Responsável")
        responsavel = st.text_input("Nome do responsável no local:").strip()

        st.caption("Assine no quadro abaixo:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#0D6EFD",
            background_color="#FFFFFF",
            height=130,
            width=340,
            drawing_mode="freedraw",
            key="canvas_assinatura"
        )

        st.subheader("Finalizar Visita")
        loc_checkout = get_geolocation()

        if st.button("🏁 Realizar Check-out e Concluir"):
            # Verificação segura da assinatura sem disparar RuntimeError
            tem_assinatura = False
            try:
                if canvas_result is not None and canvas_result.json_data is not None:
                    objetos = canvas_result.json_data.get("objects", [])
                    tem_assinatura = len(objetos) > 0
            except Exception:
                tem_assinatura = False

            # Validações dos campos
            if not foto_abastecida or not foto_limpa:
                st.error("Tire as duas fotos (abastecimento e limpeza) antes de finalizar.")
            elif not responsavel:
                st.error("Preencha o nome do responsável no cliente.")
            elif not tem_assinatura:
                st.error("Por favor, colha a assinatura do cliente desenhando no quadro antes de concluir.")
            else:
                coords = loc_checkout["coords"] if loc_checkout else None
                lat_out = coords["latitude"] if coords else "GPS não detectado"
                lon_out = coords["longitude"] if coords else "GPS não detectado"

                dados["data_checkout"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados["geo_checkout"] = f"{lat_out}, {lon_out}"
                dados["responsavel"] = responsavel

                # Salva localmente em arquivo de histórico
                arquivo_historico = "visitas_realizadas.csv"
                df_reg = pd.DataFrame([dados])
                df_reg.to_csv(
                    arquivo_historico,
                    mode="a",
                    header=not os.path.exists(arquivo_historico),
                    index=False
                )

                st.success("✅ Atendimento concluído e registrado com sucesso!")
                st.balloons()

                st.session_state["visita_ativa"] = False
                st.session_state["dados_visita"] = {}

                if st.button("Iniciar Próximo Atendimento"):
                    st.rerun()

if __name__ == "__main__":
    main()