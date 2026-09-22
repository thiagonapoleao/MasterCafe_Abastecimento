import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import unicodedata
import requests
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
            line-height: 1.6;
        }
        .info-card {
            background-color: #1E293B;
            border-left: 4px solid #0D6EFD;
            padding: 12px 14px;
            border-radius: 4px 8px 8px 4px;
            margin: 12px 0;
            color: #E2E8F0;
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
GID_USUARIOS = "1642053143"

# COLE AQUI A URL GERADA NA IMPLANTAÇÃO DO APPS SCRIPT (COMEÇA COM https://script.google.com/macros/s/...)
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwQJfe1H2OHTAYGOPZhoOGRl8zazwK4SXf-RvKRMMkQhqJHbmyg4mHBT7AVRLubKOWzbQ/exec"

def normalizar_texto(texto):
    """Remove acentuações, caracteres especiais e coloca em minúsculo."""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.strip().lower()

@st.cache_data(ttl=60)
def carregar_usuarios():
    """Carrega os dados de login da aba de usuários usando o GID 1642053143."""
    url = "https://docs.google.com/spreadsheets/d/1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU/edit?pli=1&gid=1642053143#gid=1642053143"
    try:
        df = pd.read_csv(
            url,
            engine="python",
            on_bad_lines="skip",
            dtype=str
        )
        df.columns = [normalizar_texto(c) for c in df.columns]

        if "usuario" in df.columns and "senha" in df.columns:
            df["usuario"] = df["usuario"].fillna("").astype(str).str.strip().str.lower()
            df["senha"] = df["senha"].fillna("").astype(str).str.strip()
            if "nome" not in df.columns:
                df["nome"] = df["usuario"]
            else:
                df["nome"] = df["nome"].fillna(df["usuario"]).astype(str).str.strip()
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar usuários da planilha: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def carregar_base_equipamentos():
    """Carrega a aba 'Clientes' mapeando Equipamento, Nome Fantasia, Produto e Endereço."""
    nome_aba = urllib.parse.quote("Clientes")
    url = f"https://docs.google.com/spreadsheets/d/1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU/edit?pli=1&gid=0#gid=0"

    try:
        df = pd.read_csv(
            url,
            engine="python",
            on_bad_lines="skip",
            dtype=str
        )
        
        mapa_colunas = {}
        for col in df.columns:
            norm = normalizar_texto(col)
            if norm == "equipamento":
                mapa_colunas["equipamento"] = col
            elif norm == "nome fantasia":
                mapa_colunas["nome_fantasia"] = col
            elif norm == "produto":
                mapa_colunas["produto"] = col
            elif norm == "endereco":
                mapa_colunas["endereco"] = col
            elif norm == "numero endereco":
                mapa_colunas["numero"] = col
            elif norm == "bairro":
                mapa_colunas["bairro"] = col
            elif norm == "municipio":
                mapa_colunas["municipio"] = col

        col_eq = mapa_colunas.get("equipamento", "Equipamento")
        col_cli = mapa_colunas.get("nome_fantasia", "Nome Fantasia")
        col_prod = mapa_colunas.get("produto", "Produto")
        col_end = mapa_colunas.get("endereco", "Endereço")
        col_num = mapa_colunas.get("numero", "Numero Endereço")
        col_bairro = mapa_colunas.get("bairro", "Bairro")
        col_cidade = mapa_colunas.get("municipio", "Município")

        df = df[df[col_eq].notna()].copy()
        df["equipamento_limpo"] = df[col_eq].astype(str).str.replace("*", "", regex=False).str.strip()

        def formatar_endereco(row):
            partes = []
            rua = str(row.get(col_end, "")).strip()
            num = str(row.get(col_num, "")).strip()
            bairro = str(row.get(col_bairro, "")).strip()
            cidade = str(row.get(col_cidade, "")).strip()
            
            if rua and rua.lower() != "nan":
                partes.append(rua)
            if num and num.lower() != "nan" and num != "0":
                partes.append(f"nº {num}")
            if bairro and bairro.lower() != "nan":
                partes.append(bairro)
            if cidade and cidade.lower() != "nan":
                partes.append(cidade)
                
            return " - ".join(partes) if partes else "Endereço não informado"

        df["endereco_completo"] = df.apply(formatar_endereco, axis=1)
        df["cliente_formatado"] = df[col_cli].fillna("Cliente não identificado").astype(str).str.strip()
        df["produto_formatado"] = df[col_prod].fillna("Máquina não especificada").astype(str).str.strip()

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha Google: {e}")
        return pd.DataFrame()

def salvar_visita_na_planilha(dados):
    """Envia a visita para a aba 'Visitas' da planilha via Google Apps Script Webhook com suporte a redirects."""
    if not WEBHOOK_URL.startswith("http") or "COLE_AQUI" in WEBHOOK_URL:
        st.warning("⚠️ O WEBHOOK_URL não foi configurado. O atendimento foi gravado apenas no backup local CSV.")
        return False

    try:
        # allow_redirects=True é mandatório para o endpoint do Google Apps Script
        resposta = requests.post(
            WEBHOOK_URL, 
            json=dados, 
            timeout=15, 
            allow_redirects=True
        )
        if resposta.status_code == 200:
            return True
        else:
            st.error(f"Erro ao gravar na planilha (Status HTTP {resposta.status_code}): {resposta.text}")
            return False
    except Exception as e:
        st.error(f"Falha na comunicação com o Webhook da planilha: {e}")
        return False

# -------------------------------------------------------------
# 3. TELA DE LOGIN
# -------------------------------------------------------------
def tela_login(df_usuarios):
    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Portal de Abastecimento</p></div>', unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.subheader("Identificação do Abastecedor")
        usuario_digitado = st.text_input("Usuário:").strip().lower()
        senha_digitada = st.text_input("Senha:", type="password").strip()
        btn_login = st.form_submit_button("Entrar no Sistema")
        
        if btn_login:
            if df_usuarios.empty:
                st.error("Não foi possível carregar a lista de usuários da planilha.")
                return

            usuario_valido = df_usuarios[
                (df_usuarios["usuario"] == usuario_digitado) & 
                (df_usuarios["senha"] == senha_digitada)
            ]

            if not usuario_valido.empty:
                nome_colaborador = usuario_valido.iloc[0]["nome"]
                st.session_state["autenticado"] = True
                st.session_state["usuario_logado"] = usuario_digitado
                st.session_state["nome_abastecedor"] = nome_colaborador
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# -------------------------------------------------------------
# 4. FLUXO PRINCIPAL DO APLICATIVO
# -------------------------------------------------------------
def main():
    df_usuarios = carregar_usuarios()

    if not st.session_state.get("autenticado", False):
        tela_login(df_usuarios)
        return

    with st.sidebar:
        st.write(f"👤 **Abastecedor(a):**\n### {st.session_state.get('nome_abastecedor')}")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.clear()
            st.rerun()

    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Controle de Visitas e Abastecimento</p></div>', unsafe_allow_html=True)

    if "visita_ativa" not in st.session_state:
        st.session_state["visita_ativa"] = False
        st.session_state["dados_visita"] = {}

    df_base = carregar_base_equipamentos()

    # ---------------------------------------------------------
    # ETAPA 1: CHECK-IN
    # ---------------------------------------------------------
    if not st.session_state["visita_ativa"]:
        st.subheader("1. Iniciar Atendimento (Check-in)")

        st.info(f"Operador ativo: **{st.session_state['nome_abastecedor']}**")

        num_equipamento_digitado = st.text_input(
            "Digite o Número do Equipamento:", 
            placeholder="Ex: 02020383, 102885, 3113..."
        ).strip().replace("*", "")

        dados_maquina = None

        if num_equipamento_digitado and not df_base.empty:
            resultado = df_base[
                (df_base["equipamento_limpo"].str.lower() == num_equipamento_digitado.lower()) |
                (df_base["equipamento_limpo"].str.lstrip("0") == num_equipamento_digitado.lstrip("0"))
            ]

            if not resultado.empty:
                linha = resultado.iloc[0]
                dados_maquina = {
                    "equipamento": linha["equipamento_limpo"],
                    "cliente": linha["cliente_formatado"],
                    "produto": linha["produto_formatado"],
                    "endereco": linha["endereco_completo"]
                }
                
                st.markdown(f"""
                    <div class="info-card">
                        <b>📍 Cliente:</b> {dados_maquina['cliente']}<br>
                        <b>☕ Equipamento:</b> {dados_maquina['produto']} (Nº {dados_maquina['equipamento']})<br>
                        <b>🏢 Endereço:</b> {dados_maquina['endereco']}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Equipamento não encontrado na base. Confira o número digitado.")

        st.caption("ℹ️ A geolocalização do aparelho será registrada automaticamente ao confirmar.")
        loc_checkin = get_geolocation()

        if st.button("📍 Confirmar Check-in"):
            if not num_equipamento_digitado:
                st.error("Digite o número do equipamento.")
            elif not dados_maquina:
                st.error("Não é possível iniciar: equipamento não localizado na planilha.")
            else:
                coords = loc_checkin["coords"] if loc_checkin else None
                lat = coords["latitude"] if coords else "GPS não detectado"
                lon = coords["longitude"] if coords else "GPS não detectado"

                st.session_state["visita_ativa"] = True
                st.session_state["dados_visita"] = {
                    "abastecedor": st.session_state["nome_abastecedor"],
                    "equipamento": dados_maquina["equipamento"],
                    "cliente": dados_maquina["cliente"],
                    "produto": dados_maquina["produto"],
                    "endereco": dados_maquina["endereco"],
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
                <b>Abastecedor:</b> {dados['abastecedor']}<br>
                <b>Cliente:</b> {dados['cliente']}<br>
                <b>Máquina:</b> {dados['produto']} (Nº {dados['equipamento']})<br>
                <b>Endereço:</b> {dados['endereco']}<br>
                <b>Check-in:</b> {dados['data_checkin']} | <b>GPS:</b> {dados['geo_checkin']}
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
            tem_assinatura = False
            try:
                if canvas_result is not None and canvas_result.json_data is not None:
                    objetos = canvas_result.json_data.get("objects", [])
                    tem_assinatura = len(objetos) > 0
            except Exception:
                tem_assinatura = False

            if not foto_abastecida or not foto_limpa:
                st.error("Tire ambas as fotos (abastecimento e limpeza) antes de finalizar.")
            elif not responsavel:
                st.error("Preencha o nome do responsável no cliente.")
            elif not tem_assinatura:
                st.error("Por favor, colha a assinatura do responsável no quadro.")
            else:
                coords = loc_checkout["coords"] if loc_checkout else None
                lat_out = coords["latitude"] if coords else "GPS não detectado"
                lon_out = coords["longitude"] if coords else "GPS não detectado"

                dados["data_checkout"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                dados["geo_checkout"] = f"{lat_out}, {lon_out}"
                dados["responsavel"] = responsavel

                # 1. Envio para a aba 'Visitas' da planilha Google
                sucesso_planilha = salvar_visita_na_planilha(dados)

                # 2. Gravação de backup local
                arquivo_historico = "visitas_realizadas.csv"
                df_reg = pd.DataFrame([dados])
                df_reg.to_csv(
                    arquivo_historico,
                    mode="a",
                    header=not os.path.exists(arquivo_historico),
                    index=False
                )

                if sucesso_planilha:
                    st.success("✅ Atendimento registrado e salvo na aba 'Visitas' da planilha Google!")
                else:
                    st.success("✅ Atendimento registrado localmente com sucesso!")
                st.balloons()

                st.session_state["visita_ativa"] = False
                st.session_state["dados_visita"] = {}

                if st.button("Iniciar Próximo Atendimento"):
                    st.rerun()

if __name__ == "__main__":
    main()