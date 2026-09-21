import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_drawable_canvas import st_canvas
from streamlit_js_eval import get_geolocation

# -------------------------------------------------------------
# CONFIGURAÇÃO GERAL E DESIGN
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Gestão de Visitas",
    page_icon="☕",
    layout="centered"
)

# Estilo Escuro / Corporativo
st.markdown("""
    <style>
        .stApp {
            background-color: #0F172A;
            color: #F8FAFC;
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
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 14px;
            border-radius: 8px;
            margin-bottom: 1rem;
            color: #F8FAFC;
        }
        div.stButton > button:first-child {
            width: 100%;
            border-radius: 8px;
            height: 48px;
            font-weight: bold;
            background-color: #0D6EFD;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# CONEXÃO COM A PLANILHA GOOGLE
# -------------------------------------------------------------
# Cole aqui o ID da sua planilha (o código longo que fica entre /d/ e /edit no link)
# Exemplo de URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
SPREADSHEET_ID = "COLE_O_ID_DA_SUA_PLANILHA_AQUI"

@st.cache_data(ttl=60)  # Atualiza os dados a cada 60 segundos
def carregar_dados_planilha():
    """
    Lê as abas 'Clientes' e 'Usuarios' direto da planilha pública/leitor.
    """
    try:
        url_clientes = "https://docs.google.com/spreadsheets/d/1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU/edit?gid=0#gid=0"
        url_usuarios = "https://docs.google.com/spreadsheets/d/1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU/edit?gid=1642053143#gid=1642053143"
        
        df_clientes = pd.read_csv(url_clientes)
        df_usuarios = pd.read_csv(url_usuarios)
        
        # Limpar espaços e converter para string
        df_usuarios['usuario'] = df_usuarios['usuario'].astype(str).str.strip().str.lower()
        df_usuarios['senha'] = df_usuarios['senha'].astype(str).str.strip()
        
        return df_clientes, df_usuarios
    except Exception as e:
        st.error(f"Erro ao acessar a planilha Google: {e}")
        return pd.DataFrame(), pd.DataFrame()

# -------------------------------------------------------------
# TELA DE LOGIN DINÂMICA
# -------------------------------------------------------------
def tela_login(df_usuarios):
    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Portal de Abastecimento</p></div>', unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.subheader("Acesso da Abastecedora")
        usuario_input = st.text_input("Usuário").strip().lower()
        senha_input = st.text_input("Senha", type="password").strip()
        btn_entrar = st.form_submit_button("Entrar no Sistema")
        
        if btn_entrar:
            if df_usuarios.empty:
                st.error("Não foi possível carregar a lista de usuários da planilha.")
                return

            # Procura usuário e senha correspondentes na aba 'Usuarios'
            valido = df_usuarios[(df_usuarios['usuario'] == usuario_input) & (df_usuarios['senha'] == senha_input)]
            
            if not valido.empty:
                nome_col = valido.iloc[0]['nome'] if 'nome' in valido.columns else usuario_input
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario_input
                st.session_state["nome_usuario"] = nome_col
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos. Verifique a planilha.")

# -------------------------------------------------------------
# FLUXO PRINCIPAL DE VISITAS
# -------------------------------------------------------------
def main():
    df_clientes, df_usuarios = carregar_dados_planilha()

    # Se não autenticado, mostra o formulário de login
    if not st.session_state.get("autenticado", False):
        tela_login(df_usuarios)
        return

    # Inicializa variáveis da visita
    if "visita_ativa" not in st.session_state:
        st.session_state["visita_ativa"] = False
        st.session_state["dados_visita"] = {}

    # Menu lateral
    with st.sidebar:
        st.write(f"👤 **Abastecedora:** {st.session_state['nome_usuario']}")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="main-header"><h3>Master Café ☕</h3><p>Registro de Visita</p></div>', unsafe_allow_html=True)

    # 1. CHECK-IN
    if not st.session_state["visita_ativa"]:
        st.subheader("1. Iniciar Atendimento (Check-in)")
        
        if not df_clientes.empty and "Nome fantasia" in df_clientes.columns:
            lista_clientes = df_clientes["Nome fantasia"].dropna().unique().tolist()
        else:
            lista_clientes = ["Nenhum cliente encontrado na coluna 'Nome fantasia'"]

        cliente_escolhido = st.selectbox("Selecione o Cliente / Máquina:", lista_clientes)
        
        st.caption("Aguarde a leitura do GPS do aparelho antes de clicar.")
        loc_checkin = get_geolocation()

        if st.button("📍 Confirmar Check-in"):
            coords = loc_checkin["coords"] if loc_checkin else None
            lat = coords["latitude"] if coords else "Sem GPS"
            lon = coords["longitude"] if coords else "Sem GPS"

            st.session_state["visita_ativa"] = True
            st.session_state["dados_visita"] = {
                "cliente": cliente_escolhido,
                "operadora": st.session_state["nome_usuario"],
                "checkin_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "checkin_geo": f"{lat}, {lon}"
            }
            st.rerun()

    # 2. CHECK-OUT E FORMULÁRIO DE VISITA
    else:
        dados = st.session_state["dados_visita"]
        st.markdown(f"""
            <div class="status-box">
                <b>Cliente:</b> {dados['cliente']}<br>
                <b>Entrada:</b> {dados['checkin_hora']}<br>
                <b>GPS Entrada:</b> {dados['checkin_geo']}
            </div>
        """, unsafe_allow_html=True)

        st.subheader("Fotos de Comprovação")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("1. Máquina Abastecida:")
            foto_abastecida = st.camera_input("Foto Abastecimento", key="foto1")
        with col2:
            st.caption("2. Máquina Limpa:")
            foto_limpa = st.camera_input("Foto Limpeza", key="foto2")

        st.subheader("Validação do Responsável")
        responsavel = st.text_input("Nome de quem acompanhou no cliente:")
        
        st.caption("Assine no quadro abaixo:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#0D6EFD",
            background_color="#FFFFFF",
            height=130,
            width=340,
            drawing_mode="freedraw",
            key="assinatura"
        )

        loc_checkout = get_geolocation()

        if st.button("🏁 Concluir Visita (Check-out)"):
            if not foto_abastecida or not foto_limpa:
                st.error("É obrigatório tirar as duas fotos (abastecimento e limpeza).")
            elif not responsavel.strip():
                st.error("Informe o nome do responsável no local.")
            else:
                coords = loc_checkout["coords"] if loc_checkout else None
                dados["checkout_hora"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados["checkout_geo"] = f"{coords['latitude']}, {coords['longitude']}" if coords else "Sem GPS"
                dados["responsavel"] = responsavel

                # Salva o histórico localmente
                df_final = pd.DataFrame([dados])
                df_final.to_csv("visitas_realizadas.csv", mode="a", header=not os.path.exists("visitas_realizadas.csv"), index=False)

                st.success("✅ Atendimento concluído com sucesso!")
                st.balloons()

                st.session_state["visita_ativa"] = False
                st.session_state["dados_visita"] = {}
                if st.button("Próximo Atendimento"):
                    st.rerun()

if __name__ == "__main__":
    main()