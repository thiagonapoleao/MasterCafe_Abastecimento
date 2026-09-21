import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import unicodedata
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
# ATENÇÃO: Coloque aqui o ID da sua planilha App_Abastecimento
SPREADSHEET_ID = "1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU/edit?gid=1642053143#gid=1642053143"

def normalizar_texto(texto):
    """Remove acentos, espaços extras e coloca em minúsculo."""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.strip().lower()

@st.cache_data(ttl=60)
def carregar_dados_planilha():
    if SPREADSHEET_ID == "1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU/edit?gid=1642053143#gid=1642053143" or len(SPREADSHEET_ID) < 15:
        st.error("⚠️ Configure o SPREADSHEET_ID no código com o ID real da sua planilha.")
        return pd.DataFrame(), pd.DataFrame()

    def ler_aba(nome_aba):
        nome_codificado = urllib.parse.quote(nome_aba)
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={nome_codificado}"
        return pd.read_csv(
            url,
            engine="python",
            on_bad_lines="skip",
            dtype=str
        )

    # 1. Carregar Clientes
    df_clientes = pd.DataFrame()
    try:
        df_clientes = ler_aba("Clientes")
    except Exception:
        try:
            df_clientes = ler_aba("clientes")
        except Exception as e:
            st.error(f"Erro ao ler aba 'Clientes': {e}")

    # 2. Carregar Usuários (tenta variações de nome de aba: Usuarios, Usuários, Login, Operadoras)
    df_usuarios = pd.DataFrame()
    abas_possiveis = ["Usuarios", "Usuários", "usuarios", "usuários", "Login", "login", "Operadoras"]
    
    for aba in abas_possiveis:
        try:
            df_temp = ler_aba(aba)
            if not df_temp.empty:
                df_usuarios = df_temp
                break
        except Exception:
            continue

    # Mapeamento flexível de cabeçalhos na aba de usuários
    if not df_usuarios.empty:
        # Se a primeira linha veio como título mesclado e os cabeçalhos reais estão na linha 2:
        colunas_norm = [normalizar_texto(c) for c in df_usuarios.columns]
        
        # Procura coluna de Usuário
        col_user = next((c for c, norm in zip(df_usuarios.columns, colunas_norm) if norm in ["usuario", "user", "login", "email", "abastecedora", "operadora"]), None)
        # Procura coluna de Senha
        col_pass = next((c for c, norm in zip(df_usuarios.columns, colunas_norm) if norm in ["senha", "password", "pass", "pin", "codigo"]), None)
        # Procura coluna de Nome (opcional)
        col_nome = next((c for c, norm in zip(df_usuarios.columns, colunas_norm) if norm in ["nome", "name", "abastecedora", "funcionario"]), None)

        if col_user and col_pass:
            df_usuarios["usuario"] = df_usuarios[col_user].fillna("").astype(str).str.strip().str.lower()
            df_usuarios["senha"] = df_usuarios[col_pass].fillna("").astype(str).str.strip()
            df_usuarios["nome"] = df_usuarios[col_nome].fillna(df_usuarios["usuario"]).astype(str).str.strip() if col_nome else df_usuarios["usuario"]
        else:
            # Não encontrou os nomes padrão — guarda os nomes originais para exibir diagnóstico amigável
            st.session_state["colunas_detectadas"] = list(df_usuarios.columns)

    return df_clientes, df_usuarios

# -------------------------------------------------------------
# 3. TELA DE LOGIN
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
                st.error("Não foi possível carregar a aba de usuários. Verifique se a planilha possui uma aba chamada 'Usuarios' e está compartilhada como 'Qualquer pessoa com o link pode ler'.")
                return

            if "usuario" not in df_usuarios.columns or "senha" not in df_usuarios.columns:
                cols = st.session_state.get("colunas_detectadas", list(df_usuarios.columns))
                st.error(f"Não localizamos as colunas de login. O sistema encontrou estas colunas na primeira linha da aba: {cols}")
                st.info("💡 **Como resolver:** Certifique-se de que na linha 1 da sua aba existam colunas com os nomes: `usuario` e `senha`.")
                return

            valido = df_usuarios[(df_usuarios["usuario"] == usuario_input) & (df_usuarios["senha"] == senha_input)]
            
            if not valido.empty:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = usuario_input
                st.session_state["nome_usuario"] = valido.iloc[0]["nome"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# -------------------------------------------------------------
# 4. FLUXO PRINCIPAL DE VISITAS
# -------------------------------------------------------------
def main():
    df_clientes, df_usuarios = carregar_dados_planilha()

    if not st.session_state.get("autenticado", False):
        tela_login(df_usuarios)
        return

    if "visita_ativa" not in st.session_state:
        st.session_state["visita_ativa"] = False
        st.session_state["dados_visita"] = {}

    with st.sidebar:
        st.write(f"👤 **Abastecedora:** {st.session_state['nome_usuario']}")
        if st.button("Sair da Conta"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="main-header"><h3>Master Café ☕</h3><p>Registro de Atendimento em Campo</p></div>', unsafe_allow_html=True)

    # 1. CHECK-IN
    if not st.session_state["visita_ativa"]:
        st.subheader("1. Iniciar Atendimento (Check-in)")
        
        lista_clientes = []
        if not df_clientes.empty:
            # Procura de forma inteligente a coluna "Nome fantasia"
            col_cliente = next((c for c in df_clientes.columns if normalizar_texto(c) == "nome fantasia"), None)
            if col_cliente:
                lista_clientes = df_clientes[col_cliente].dropna().unique().tolist()
            else:
                # Se não encontrar com nome exato, pega a primeira coluna de texto
                lista_clientes = df_clientes.iloc[:, 0].dropna().unique().tolist()
        
        if not lista_clientes:
            lista_clientes = ["Nenhum cliente disponível"]

        cliente_escolhido = st.selectbox("Selecione o Cliente / Máquina:", lista_clientes)
        
        st.caption("Aguarde o sinal de GPS ser lido antes de confirmar:")
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

    # 2. CHECK-OUT E COMPROVAÇÕES
    else:
        dados = st.session_state["dados_visita"]
        st.markdown(f"""
            <div class="status-box">
                <b>Cliente:</b> {dados['cliente']}<br>
                <b>Check-in:</b> {dados['data_checkin']}<br>
                <b>GPS Entrada:</b> {dados['geo_checkin']}
            </div>
        """, unsafe_allow_html=True)

        st.subheader("Fotos de Comprovação")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("1. Máquina Abastecida:")
            foto_abastecida = st.camera_input("Foto Abastecida", key="foto1")
        with col2:
            st.caption("2. Máquina Limpa:")
            foto_limpa = st.camera_input("Foto Limpa", key="foto2")

        st.subheader("Assinatura do Cliente Responsável")
        responsavel = st.text_input("Nome do responsável no cliente:")
        
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
            if not foto_abastecida or not foto_limpa:
                st.error("É necessário capturar ambas as fotos antes de concluir.")
            elif not responsavel.strip():
                st.error("Preencha o nome do responsável no cliente.")
            elif canvas_result.image_data is None:
                st.error("Colha a assinatura do cliente na tela.")
            else:
                coords = loc_checkout["coords"] if loc_checkout else None
                lat_out = coords["latitude"] if coords else "GPS não detectado"
                lon_out = coords["longitude"] if coords else "GPS não detectado"

                dados["data_checkout"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados["geo_checkout"] = f"{lat_out}, {lon_out}"
                dados["responsavel"] = responsavel

                # Salva localmente em histórico CSV
                arquivo_historico = "visitas_realizadas.csv"
                df_reg = pd.DataFrame([dados])
                df_reg.to_csv(
                    arquivo_historico,
                    mode="a",
                    header=not os.path.exists(arquivo_historico),
                    index=False
                )

                st.success("✅ Atendimento concluído e registrado!")
                st.balloons()

                st.session_state["visita_ativa"] = False
                st.session_state["dados_visita"] = {}

                if st.button("Iniciar Próximo Atendimento"):
                    st.rerun()

if __name__ == "__main__":
    main()