import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO (DARK MODE / CORPORATIVO)
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
# 2. CONEXÃO COM A PLANILHA GOOGLE
# -------------------------------------------------------------
# ATENÇÃO: Substitua pelo ID real da sua planilha App_Abastecimento
# Exemplo de ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
SPREADSHEET_ID = "COLE_O_ID_DA_SUA_PLANILHA_AQUI"

@st.cache_data(ttl=60)
def carregar_dados_planilha():
    """
    Lê as abas 'Clientes' e 'Usuarios' com motor Python resiliente a vírgulas
    internas e quebras de linha que causam erro de tokenização.
    """
    try:
        url_clientes = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Clientes"
        url_usuarios = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Usuarios"
        
        # Parâmetros que eliminam o erro 'esperados X campos, vi Y'
        params_leitura = {
            "engine": "python",
            "on_bad_lines": "skip",
            "dtype": str
        }

        df_clientes = pd.read_csv(url_clientes, **params_leitura)
        df_usuarios = pd.read_csv(url_usuarios, **params_leitura)
        
        # Limpa espaços em branco acidentais nos nomes dos cabeçalhos
        df_clientes.columns = [str(col).strip() for col in df_clientes.columns]
        df_usuarios.columns = [str(col).strip().lower() for col in df_usuarios.columns]

        # Padroniza os campos de login se a aba de usuários existir
        if "usuario" in df_usuarios.columns and "senha" in df_usuarios.columns:
            df_usuarios["usuario"] = df_usuarios["usuario"].fillna("").astype(str).str.strip().str.lower()
            df_usuarios["senha"] = df_usuarios["senha"].fillna("").astype(str).str.strip()

        return df_clientes, df_usuarios

    except Exception as e:
        st.error(f"Erro ao acessar a planilha Google: {e}")
        return pd.DataFrame(), pd.DataFrame()

# -------------------------------------------------------------
# 3. TELA DE LOGIN DAS ABASTECEDORAS
# -------------------------------------------------------------
def tela_login(df_usuarios):
    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Portal de Abastecimento e Visitas</p></div>', unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.subheader("Login da Abastecedora")
        usuario_input = st.text_input("Usuário").strip().lower()
        senha_input = st.text_input("Senha", type="password").strip()
        btn_entrar = st.form_submit_button("Entrar no Sistema")
        
        if btn_entrar:
            if df_usuarios.empty:
                st.error("Não foi possível carregar os usuários da planilha. Verifique o compartilhamento da planilha (Leitor).")
                return

            if "usuario" not in df_usuarios.columns or "senha" not in df_usuarios.columns:
                st.error("A aba 'Usuarios' precisa ter as colunas com os nomes exatos: 'usuario' e 'senha'.")
                return

            # Validação do login na base da planilha
            valido = df_usuarios[(df_usuarios["usuario"] == usuario_input) & (df_usuarios["senha"] == senha_input)]
            
            if not valido.empty:
                nome_col = valido.iloc[0]["nome"] if "nome" in valido.columns else usuario_input
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario_input
                st.session_state["nome_usuario"] = str(nome_col).strip()
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos. Confira na aba 'Usuarios' da planilha.")

# -------------------------------------------------------------
# 4. APLICAÇÃO PRINCIPAL E FLUXO DE VISITAS
# -------------------------------------------------------------
def main():
    df_clientes, df_usuarios = carregar_dados_planilha()

    # Bloqueia se não estiver autenticado
    if not st.session_state.get("autenticado", False):
        tela_login(df_usuarios)
        return

    # Inicialização do estado da visita
    if "visita_ativa" not in st.session_state:
        st.session_state["visita_ativa"] = False
        st.session_state["dados_visita"] = {}

    # Menu lateral com perfil e botão de deslogar
    with st.sidebar:
        st.write(f"👤 **Abastecedora:** {st.session_state['nome_usuario']}")
        if st.button("Sair da Conta"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="main-header"><h3>Master Café ☕</h3><p>Registro de Atendimento em Campo</p></div>', unsafe_allow_html=True)

    # ---------------------------------------------------------
    # ETAPA 1: CHECK-IN
    # ---------------------------------------------------------
    if not st.session_state["visita_ativa"]:
        st.subheader("1. Iniciar Atendimento (Check-in)")
        
        # Obtém os clientes da coluna "Nome fantasia"
        lista_clientes = []
        if not df_clientes.empty:
            coluna_encontrada = next((c for c in df_clientes.columns if c.strip().lower() == "nome fantasia"), None)
            if coluna_encontrada:
                lista_clientes = df_clientes[coluna_encontrada].dropna().unique().tolist()
        
        if not lista_clientes:
            st.warning("Coluna 'Nome fantasia' não encontrada ou sem dados na aba 'Clientes'.")
            lista_clientes = ["Nenhum cliente disponível"]

        cliente_escolhido = st.selectbox("Selecione o Cliente / Ponto:", lista_clientes)
        
        st.caption("ℹ️ A geolocalização será capturada no momento do check-in.")
        loc_checkin = get_geolocation()

        if st.button("📍 Confirmar Check-in"):
            coords = loc_checkin["coords"] if loc_checkin else None
            lat = coords["latitude"] if coords else "GPS não detectado"
            lon = coords["longitude"] if coords else "GPS não detectado"

            st.session_state["visita_ativa"] = True
            st.session_state["dados_visita"] = {
                "cliente": cliente_escolhido,
                "abastecedora": st.session_state["nome_usuario"],
                "data_checkin": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "geo_checkin": f"{lat}, {lon}"
            }
            st.rerun()

    # ---------------------------------------------------------
    # ETAPA 2: CHECK-OUT E FORMULÁRIO DE COMPROVAÇÃO
    # ---------------------------------------------------------
    else:
        dados = st.session_state["dados_visita"]
        
        st.markdown(f"""
            <div class="status-box">
                <b>Cliente em Atendimento:</b> {dados['cliente']}<br>
                <b>Check-in realizado em:</b> {dados['data_checkin']}<br>
                <b>GPS Entrada:</b> {dados['geo_checkin']}
            </div>
        """, unsafe_allow_html=True)

        st.subheader("Fotos de Comprovação")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("1. Máquina Abastecida:")
            foto_abastecida = st.camera_input("Foto Abastecimento", key="foto_abast")
        with col2:
            st.caption("2. Máquina Limpa:")
            foto_limpa = st.camera_input("Foto Limpeza", key="foto_limp")

        st.subheader("Assinatura do Cliente Responsável")
        responsavel = st.text_input("Nome do responsável no local:")
        
        st.caption("Assine abaixo:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#0D6EFD",
            background_color="#FFFFFF",
            height=130,
            width=340,
            drawing_mode="freedraw",
            key="assinatura_canvas"
        )

        st.subheader("Finalizar Visita")
        loc_checkout = get_geolocation()

        if st.button("🏁 Realizar Check-out e Concluir"):
            if not foto_abastecida or not foto_limpa:
                st.error("Por favor, tire ambas as fotos (máquina abastecida e limpa).")
            elif not responsavel.strip():
                st.error("Informe o nome do responsável do cliente.")
            elif canvas_result.image_data is None:
                st.error("Colha a assinatura do cliente no campo acima.")
            else:
                coords = loc_checkout["coords"] if loc_checkout else None
                lat_out = coords["latitude"] if coords else "GPS não detectado"
                lon_out = coords["longitude"] if coords else "GPS não detectado"

                dados["data_checkout"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados["geo_checkout"] = f"{lat_out}, {lon_out}"
                dados["responsavel"] = responsavel

                # Salva o registro em arquivo CSV de histórico
                arquivo_historico = "visitas_realizadas.csv"
                df_registro = pd.DataFrame([dados])
                df_registro.to_csv(
                    arquivo_historico,
                    mode="a",
                    header=not os.path.exists(arquivo_historico),
                    index=False
                )

                st.success("✅ Atendimento concluído e registrado com sucesso!")
                st.balloons()

                # Limpa o atendimento ativo
                st.session_state["visita_ativa"] = False
                st.session_state["dados_visita"] = {}

                if st.button("Iniciar Novo Atendimento"):
                    st.rerun()

if __name__ == "__main__":
    main()