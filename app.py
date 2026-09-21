import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import os

# Componentes de Canvas (Assinatura) e JS (Geolocalização)
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Gestão de Visitas",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Customização CSS para layout corporativo moderno e botões destacados
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 650px;
        }
        .main-header {
            text-align: center;
            padding: 12px;
            border-radius: 10px;
            background: linear-gradient(135deg, #1E3A8A, #0D6EFD);
            color: white;
            margin-bottom: 1.5rem;
        }
        .status-box {
            background-color: rgba(30, 41, 59, 0.7);
            border: 1px solid #334155;
            padding: 14px;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        div.stButton > button:first-child {
            width: 100%;
            border-radius: 8px;
            height: 48px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. AUTENTICAÇÃO DAS ABASTECEDORAS
# -------------------------------------------------------------
USUARIOS = {
    "abastecedora1": {"senha": "123", "nome": "Carla Abastecedora"},
    "abastecedora2": {"senha": "123", "nome": "Mariana Operações"},
    "admin": {"senha": "admin", "nome": "Supervisão Master Café"}
}

def tela_login():
    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Portal de Abastecimento e Visitas</p></div>', unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.subheader("Login da Operadora")
        usuario = st.text_input("Usuário").strip().lower()
        senha = st.text_input("Senha", type="password")
        btn_entrar = st.form_submit_button("Entrar no Sistema")
        
        if btn_entrar:
            if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario
                st.session_state["nome_usuario"] = USUARIOS[usuario]["nome"]
                st.rerun()
            else:
                st.error("Credenciais inválidas. Tente novamente.")

# -------------------------------------------------------------
# 3. CARREGAMENTO DA PLANILHA GOOGLE
# -------------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_clientes():
    """
    Carrega a lista da planilha 'App_Abastecimento - Google Planilhas', aba 'Clientes'.
    Caso as credenciais de API do Google não estejam ativas, utiliza um arquivo local de fallback.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Procura por credenciais do Google na raiz ou nos segredos do Streamlit
        if os.path.exists("google_credentials.json"):
            escopos = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = Credentials.from_service_account_file("google_credentials.json", scopes=escopos)
            gc = gspread.authorize(creds)
            planilha = gc.open("App_Abastecimento")
            aba = planilha.worksheet("Clientes")
            df = pd.DataFrame(aba.get_all_records())
        else:
            # Fallback simulado ou arquivo local caso a chave da API ainda não esteja configurada
            df = pd.DataFrame({
                "Nome fantasia": [
                    "Empresa Alfa - Centro",
                    "Hospital São Lucas - Térreo",
                    "Tech Solutions - Sala VIP",
                    "Academia Iron - Recepção",
                    "Advocacia Ribeiro & Associados"
                ]
            })
        return df["Nome fantasia"].dropna().unique().tolist()
    except Exception as e:
        st.warning(f"Aviso de sincronização: {e}. Usando dados de contingência.")
        return [
            "Empresa Alfa - Centro",
            "Hospital São Lucas - Térreo",
            "Tech Solutions - Sala VIP",
            "Academia Iron - Recepção"
        ]

# -------------------------------------------------------------
# 4. APLICAÇÃO PRINCIPAL E FLUXO DE VISITA
# -------------------------------------------------------------
def main():
    if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
        tela_login()
        return

    # Inicialização do estado de visita
    if "visita_ativa" not in st.session_state:
        st.session_state["visita_ativa"] = False
        st.session_state["dados_visita"] = {}

    # Barra lateral de controle
    with st.sidebar:
        st.write(f"👤 **Operadora:** {st.session_state['nome_usuario']}")
        if st.button("Sair da Conta"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="main-header"><h3>Master Café ☕</h3><p>Controle de Visitas e Abastecimento</p></div>', unsafe_allow_html=True)
    
    lista_clientes = carregar_clientes()

    # Fluxo 1: Iniciar Visita (Check-in)
    if not st.session_state["visita_ativa"]:
        st.subheader("Iniciar Atendimento")
        
        cliente_escolhido = st.selectbox("Selecione o Cliente / Ponto:", lista_clientes)
        
        st.info("A geolocalização do dispositivo será associada ao registro de entrada.")
        loc_checkin = get_geolocation()

        if st.button("📍 Realizar Check-in"):
            coords = loc_checkin["coords"] if loc_checkin else None
            lat = coords["latitude"] if coords else "Não identificada"
            lon = coords["longitude"] if coords else "Não identificada"

            st.session_state["visita_ativa"] = True
            st.session_state["dados_visita"] = {
                "cliente": cliente_escolhido,
                "operadora": st.session_state["nome_usuario"],
                "data_checkin": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "geo_checkin": f"{lat}, {lon}"
            }
            st.success(f"Check-in efetuado em: {cliente_escolhido}")
            st.rerun()

    # Fluxo 2: Durante a Visita e Finalização (Check-out)
    else:
        dados = st.session_state["dados_visita"]
        
        st.markdown(f"""
            <div class="status-box">
                <b>Cliente em Atendimento:</b> {dados['cliente']}<br>
                <b>Início da Visita:</b> {dados['data_checkin']}<br>
                <b>Coordenadas Entrada:</b> {dados['geo_checkin']}
            </div>
        """, unsafe_allow_html=True)

        st.subheader("1. Evidências do Serviço")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Foto da Máquina Abastecida:")
            foto_abastecimento = st.camera_input("Foto Abastecimento", key="foto_abast")
        with col2:
            st.caption("Foto da Máquina Limpa:")
            foto_limpeza = st.camera_input("Foto Limpeza", key="foto_limp")

        st.subheader("2. Confirmação do Responsável")
        nome_responsavel = st.text_input("Nome do responsável no local:")
        
        st.caption("Assinatura do cliente na tela:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#0D6EFD",
            background_color="#FFFFFF",
            height=140,
            width=360,
            drawing_mode="freedraw",
            key="canvas_assinatura"
        )

        st.subheader("3. Finalizar Atendimento")
        loc_checkout = get_geolocation()

        if st.button("🏁 Realizar Check-out e Salvar"):
            # Validações obrigatórias
            if not foto_abastecimento or not foto_limpeza:
                st.error("Por favor, tire ambas as fotos (abastecimento e limpeza) antes de encerrar.")
            elif not nome_responsavel.strip():
                st.error("Informe o nome do responsável que acompanhou o serviço.")
            elif canvas_result.image_data is None:
                st.error("Colha a assinatura do cliente no campo acima.")
            else:
                coords = loc_checkout["coords"] if loc_checkout else None
                lat_out = coords["latitude"] if coords else "Não identificada"
                lon_out = coords["longitude"] if coords else "Não identificada"

                dados["data_checkout"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados["geo_checkout"] = f"{lat_out}, {lon_out}"
                dados["responsavel"] = nome_responsavel
                
                # Exemplo de salvamento de log / exportação
                registro_final = pd.DataFrame([dados])
                registro_final.to_csv("historico_visitas.csv", mode="a", header=not os.path.exists("historico_visitas.csv"), index=False)

                st.success("✅ Atendimento concluído com sucesso e dados arquivados!")
                st.balloons()
                
                # Reset para próxima visita
                st.session_state["visita_ativa"] = False
                st.session_state["dados_visita"] = {}
                
                if st.button("Iniciar Próxima Visita"):
                    st.rerun()

if __name__ == "__main__":
    main()