import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse
import unicodedata
import requests
import os

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL (DARK MODE / CORPORATIVO)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Dashboard de Visitas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .stApp {
            background-color: #0F172A;
            color: #F8FAFC;
        }
        .metric-card {
            background: linear-gradient(135deg, #1E293B, #0F172A);
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px 20px;
            text-align: left;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.25);
            margin-bottom: 10px;
        }
        .metric-title {
            color: #94A3B8;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }
        .metric-value {
            color: #38BDF8;
            font-size: 1.8rem;
            font-weight: 700;
        }
        .metric-sub {
            color: #64748B;
            font-size: 0.75rem;
            margin-top: 4px;
        }
        .insight-card {
            background-color: #1E293B;
            border-left: 4px solid #38BDF8;
            border-radius: 4px 8px 8px 4px;
            padding: 14px 18px;
            margin-bottom: 20px;
            color: #E2E8F0;
        }
        .delete-box {
            background-color: #1E293B;
            border: 1px solid #EF4444;
            border-radius: 8px;
            padding: 18px;
            margin-top: 15px;
        }
        .block-header {
            font-size: 1.2rem;
            font-weight: 600;
            color: #F8FAFC;
            margin-top: 15px;
            margin-bottom: 12px;
            border-bottom: 1px solid #334155;
            padding-bottom: 6px;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. CONEXÃO COM A PLANILHA GOOGLE (ABA "Visitas")
# -------------------------------------------------------------
SPREADSHEET_ID = "1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU"

# URL DO SEU APPS SCRIPT
WEBHOOK_URL = "COLE_AQUI_A_URL_DO_APP_DA_WEB_DO_APPS_SCRIPT"

def normalizar_coluna(col):
    if not isinstance(col, str):
        col = str(col)
    texto = unicodedata.normalize('NFKD', col).encode('ASCII', 'ignore').decode('ASCII')
    return texto.strip().lower()

@st.cache_data(ttl=30)
def carregar_dados_visitas():
    nome_aba = urllib.parse.quote("Visitas")
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={nome_aba}"

    try:
        df = pd.read_csv(
            url,
            engine="python",
            on_bad_lines="skip",
            dtype=str
        )
        
        mapa_colunas = {}
        for c in df.columns:
            norm = normalizar_coluna(c)
            if "checkin" in norm and "data" in norm:
                mapa_colunas[c] = "data_checkin"
            elif "checkout" in norm and "data" in norm:
                mapa_colunas[c] = "data_checkout"
            elif "abastecedor" in norm:
                mapa_colunas[c] = "abastecedor"
            elif "equipamento" in norm:
                mapa_colunas[c] = "equipamento"
            elif "cliente" in norm:
                mapa_colunas[c] = "cliente"
            elif "produto" in norm:
                mapa_colunas[c] = "produto"
            elif "endereco" in norm:
                mapa_colunas[c] = "endereco"
            elif "checkin" in norm and "gps" in norm:
                mapa_colunas[c] = "geo_checkin"
            elif "checkout" in norm and "gps" in norm:
                mapa_colunas[c] = "geo_checkout"
            elif "responsavel" in norm:
                mapa_colunas[c] = "responsavel"

        df = df.rename(columns=mapa_colunas)

    except Exception:
        df = pd.DataFrame()

    if df.empty or "data_checkin" not in df.columns or len(df) == 0:
        base_exemplo = [
            {"data_checkin": "21/09/2026 08:30:00", "data_checkout": "21/09/2026 09:05:00", "abastecedor": "Thiago Napoleão", "equipamento": "02020383", "cliente": "JBT FOOD TECH", "produto": "KREA ES4S-R/BR", "endereco": "AV CAMILO DINUCCI, 4605", "geo_checkin": "-21.7946, -48.1766", "geo_checkout": "-21.7947, -48.1765", "responsavel": "Marcos"},
            {"data_checkin": "21/09/2026 09:40:00", "data_checkout": "21/09/2026 10:10:00", "abastecedor": "Thiago Napoleão", "equipamento": "102885", "cliente": "CAFETERIA KAFFE", "produto": "FIORENZATO", "endereco": "AV PRES KENNEDY, 1500", "geo_checkin": "-21.1767, -47.8208", "geo_checkout": "-21.1768, -47.8207", "responsavel": "Ana Paula"},
            {"data_checkin": "21/09/2026 10:45:00", "data_checkout": "21/09/2026 11:35:00", "abastecedor": "Mariana Operações", "equipamento": "1712942", "cliente": "GELATO BORELLI", "produto": "FAEMA E98", "endereco": "AV JUSCELINO KUBITSCHEK, 5000", "geo_checkin": "-20.8113, -49.3758", "geo_checkout": "-20.8115, -49.3757", "responsavel": "Lucas"},
            {"data_checkin": "20/09/2026 14:15:00", "data_checkout": "20/09/2026 14:40:00", "abastecedor": "Carla Silva", "equipamento": "1727812", "cliente": "NAPOLEAO CAFE", "produto": "MOINHO FAEMA", "endereco": "RUA NAPOLEAO SELMI-DEI, 756", "geo_checkin": "-21.7821, -48.1812", "geo_checkout": "-21.7822, -48.1811", "responsavel": "Cláudia"}
        ]
        df = pd.DataFrame(base_exemplo)

    # Tratamento de datas e durações
    df["dt_checkin"] = pd.to_datetime(df["data_checkin"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    df["dt_checkout"] = pd.to_datetime(df["data_checkout"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    
    df["duracao_minutos"] = (df["dt_checkout"] - df["dt_checkin"]).dt.total_seconds() / 60.0
    df["duracao_minutos"] = df["duracao_minutos"].apply(lambda x: round(max(x, 1.0), 1) if pd.notnull(x) else 0.0)

    df["data_dia"] = df["dt_checkin"].dt.strftime("%d/%m/%Y")
    df["mes_ano"] = df["dt_checkin"].dt.strftime("%m/%Y")
    df["hora_checkin"] = df["dt_checkin"].dt.strftime("%H:%M")
    df["hora_checkout"] = df["dt_checkout"].dt.strftime("%H:%M")

    return df

def excluir_visita(payload):
    """Exclui da planilha online via Apps Script e do CSV local se existir."""
    payload["action"] = "delete"
    sucesso_online = False

    if WEBHOOK_URL.startswith("http"):
        try:
            resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if resp.status_code == 200:
                sucesso_online = True
        except Exception as e:
            st.error(f"Erro ao conectar com Google Sheets para excluir: {e}")

    # Exclusão no CSV local de backup
    if os.path.exists("visitas_realizadas.csv"):
        try:
            df_local = pd.read_csv("visitas_realizadas.csv", dtype=str)
            mask = ~(
                (df_local["data_checkin"] == payload["data_checkin"]) &
                (df_local["abastecedor"] == payload["abastecedor"]) &
                (df_local["equipamento"] == payload["equipamento"])
            )
            df_local[mask].to_csv("visitas_realizadas.csv", index=False)
        except Exception:
            pass

    return sucesso_online

# -------------------------------------------------------------
# 3. INTERFACE E ABAS PRINCIPAIS DO PAINEL
# -------------------------------------------------------------
st.title("☕ Master Café — Cockpit de Operações e Visitas")
st.caption("Acompanhamento gerencial em tempo real de abastecimentos, produtividade e tempos de ciclo.")

df_raw = carregar_dados_visitas()

# ABAS PRINCIPAIS: VISÃO ANALÍTICA VS GESTÃO/EXCLUSÃO
aba_cockpit, aba_exclusao = st.tabs(["📊 Visão Analítica & Indicadores", "🗑️ Gestão e Exclusão de Registros"])

# -------------------------------------------------------------
# ABA 1: VISÃO ANALÍTICA
# -------------------------------------------------------------
with aba_cockpit:
    with st.sidebar:
        st.header("🔍 Filtros de Operação")
        
        abastecedores = sorted([x for x in df_raw["abastecedor"].dropna().unique().tolist() if str(x).strip() != ""])
        abast_selecionados = st.multiselect("Abastecedor(a):", options=abastecedores, default=abastecedores)

        min_date = df_raw["dt_checkin"].min()
        max_date = df_raw["dt_checkin"].max()
        if pd.isna(min_date):
            min_date = datetime.now() - timedelta(days=30)
        if pd.isna(max_date):
            max_date = datetime.now()

        intervalo_data = st.date_input("Período de Análise:", value=(min_date.date(), max_date.date()))

        clientes_lista = sorted([x for x in df_raw["cliente"].dropna().unique().tolist() if str(x).strip() != ""])
        clientes_selecionados = st.multiselect("Cliente / Ponto:", options=clientes_lista, default=[])

        st.markdown("---")
        if st.button("🔄 Atualizar Indicadores"):
            st.cache_data.clear()
            st.rerun()

    # Aplicação dos Filtros
    df = df_raw.copy()
    if abast_selecionados:
        df = df[df["abastecedor"].isin(abast_selecionados)]
    if isinstance(intervalo_data, tuple) and len(intervalo_data) == 2:
        d_inicio, d_fim = intervalo_data
        df = df[(df["dt_checkin"].dt.date >= d_inicio) & (df["dt_checkin"].dt.date <= d_fim)]
    if clientes_selecionados:
        df = df[df["cliente"].isin(clientes_selecionados)]

    # Cards de KPIs
    total_visitas = len(df)
    total_clientes = df["cliente"].nunique() if total_visitas > 0 else 0
    total_maquinas = df["equipamento"].nunique() if total_visitas > 0 else 0
    tempo_medio_geral = round(df["duracao_minutos"].mean(), 1) if total_visitas > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total de Visitas</div><div class="metric-value">{total_visitas}</div><div class="metric-sub">Atendimentos concluídos</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Clientes Atendidos</div><div class="metric-value">{total_clientes}</div><div class="metric-sub">Empresas e pontos distintos</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Máquinas Abastecidas</div><div class="metric-value">{total_maquinas}</div><div class="metric-sub">Equipamentos únicos</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Tempo Médio Geral</div><div class="metric-value">{tempo_medio_geral} min</div><div class="metric-sub">Média por máquina em campo</div></div>', unsafe_allow_html=True)

    # Insights Automáticos
    if total_visitas > 0:
        maior_abast = df["abastecedor"].value_counts().index[0]
        qtd_maior = df["abastecedor"].value_counts().iloc[0]
        cliente_mais_visitado = df["cliente"].value_counts().index[0]
        tempo_max = df["duracao_minutos"].max()
        cli_tempo_max = df.loc[df["duracao_minutos"].idxmax()]["cliente"]
        
        st.markdown(f"""
            <div class="insight-card">
                <b>💡 Destaques da Operação Master Café:</b><br>
                • <b>Produtividade:</b> O(A) colaborador(a) <b>{maior_abast}</b> lidera com <b>{qtd_maior}</b> visitas realizadas.<br>
                • <b>Frequência:</b> O cliente com maior volume de atendimentos foi <b>{cliente_mais_visitado}</b>.<br>
                • <b>Atenção de Eficiência:</b> O atendimento mais longo demorou <b>{tempo_max} minutos</b> em <b>{cli_tempo_max}</b>.
            </div>
        """, unsafe_allow_html=True)

    # Gráficos
    st.markdown('<div class="block-header">📊 Indicadores de Eficiência e Tempo de Ciclo</div>', unsafe_allow_html=True)
    c_graf1, c_graf2 = st.columns(2)

    with c_graf1:
        df_tempo_cliente = df.groupby("cliente")["duracao_minutos"].mean().reset_index().sort_values("duracao_minutos", ascending=True)
        df_tempo_cliente["duracao_minutos"] = df_tempo_cliente["duracao_minutos"].round(1)
        fig_cli = px.bar(df_tempo_cliente, x="duracao_minutos", y="cliente", orientation="h", title="Tempo Médio por Cliente (minutos)", text="duracao_minutos", color="duracao_minutos", color_continuous_scale=["#0D6EFD", "#38BDF8"])
        fig_cli.update_layout(template="plotly_dark", plot_bgcolor="#1E293B", paper_bgcolor="#1E293B", xaxis_title="Minutos", yaxis_title="", coloraxis_showscale=False, height=360)
        st.plotly_chart(fig_cli, use_container_width=True)

    with c_graf2:
        df_tempo_abast = df.groupby("abastecedor")["duracao_minutos"].mean().reset_index().sort_values("duracao_minutos", ascending=False)
        df_tempo_abast["duracao_minutos"] = df_tempo_abast["duracao_minutos"].round(1)
        fig_abast = px.bar(df_tempo_abast, x="abastecedor", y="duracao_minutos", title="Tempo Médio por Abastecedor (minutos)", text="duracao_minutos", color="duracao_minutos", color_continuous_scale=["#1E3A8A", "#0D6EFD"])
        fig_abast.update_layout(template="plotly_dark", plot_bgcolor="#1E293B", paper_bgcolor="#1E293B", xaxis_title="", yaxis_title="Minutos", coloraxis_showscale=False, height=360)
        st.plotly_chart(fig_abast, use_container_width=True)

    c_graf3, c_graf4 = st.columns(2)
    with c_graf3:
        df_prod = df["produto"].value_counts().reset_index()
        df_prod.columns = ["produto", "total"]
        fig_prod = px.pie(df_prod, names="produto", values="total", title="Distribuição por Modelo de Máquina", hole=0.45, color_discrete_sequence=["#0D6EFD", "#38BDF8", "#0284C7", "#60A5FA"])
        fig_prod.update_layout(template="plotly_dark", plot_bgcolor="#1E293B", paper_bgcolor="#1E293B", height=350)
        st.plotly_chart(fig_prod, use_container_width=True)

    with c_graf4:
        df_timeline = df.groupby("data_dia").size().reset_index(name="visitas")
        fig_line = px.line(df_timeline, x="data_dia", y="visitas", markers=True, title="Volume de Visitas por Dia", line_shape="spline")
        fig_line.update_traces(line_color="#38BDF8", marker=dict(size=8, color="#0D6EFD"))
        fig_line.update_layout(template="plotly_dark", plot_bgcolor="#1E293B", paper_bgcolor="#1E293B", xaxis_title="Data", yaxis_title="Total de Visitas", height=350)
        st.plotly_chart(fig_line, use_container_width=True)

    # Tabelas Consolidadas
    st.markdown('<div class="block-header">📈 Produção Consolidada por Abastecedor</div>', unsafe_allow_html=True)
    tab_mes, tab_dia = st.tabs(["📅 Consolidado por Mês", "🗓️ Consolidado por Dia"])
    
    with tab_mes:
        df_mes = df.groupby(["mes_ano", "abastecedor"]).agg(total_visitas=("equipamento", "count"), clientes_unicos=("cliente", "nunique"), maquinas_unicas=("equipamento", "nunique"), tempo_medio=("duracao_minutos", "mean")).reset_index()
        df_mes["tempo_medio"] = df_mes["tempo_medio"].round(1)
        st.dataframe(df_mes.rename(columns={"mes_ano": "Mês/Ano", "abastecedor": "Abastecedor", "total_visitas": "Total Atendimentos", "clientes_unicos": "Clientes Distintos", "maquinas_unicas": "Máquinas Distintas", "tempo_medio": "Tempo Médio (min)"}), use_container_width=True, hide_index=True)

    with tab_dia:
        df_dia = df.groupby(["data_dia", "abastecedor"]).agg(total_visitas=("equipamento", "count"), clientes_unicos=("cliente", "nunique"), maquinas_unicas=("equipamento", "nunique"), tempo_medio=("duracao_minutos", "mean")).reset_index()
        df_dia["tempo_medio"] = df_dia["tempo_medio"].round(1)
        st.dataframe(df_dia.rename(columns={"data_dia": "Data", "abastecedor": "Abastecedor", "total_visitas": "Total Atendimentos", "clientes_unicos": "Clientes Distintos", "maquinas_unicas": "Máquinas Distintas", "tempo_medio": "Tempo Médio (min)"}), use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# ABA 2: GESTÃO E EXCLUSÃO DE DADOS LANÇADOS
# -------------------------------------------------------------
with aba_exclusao:
    st.subheader("🗑️ Exclusão de Atendimentos Lançados")
    st.caption("Esta ferramenta permite a exclusão pontual de registros lançados por engano ou duplicados.")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_abast_del = st.selectbox(
            "Filtrar por Abastecedor:",
            options=["Todos"] + sorted(df_raw["abastecedor"].dropna().unique().tolist())
        )
    with col_f2:
        filtro_cli_del = st.selectbox(
            "Filtrar por Cliente:",
            options=["Todos"] + sorted(df_raw["cliente"].dropna().unique().tolist())
        )

    df_del = df_raw.copy()
    if filtro_abast_del != "Todos":
        df_del = df_del[df_del["abastecedor"] == filtro_abast_del]
    if filtro_cli_del != "Todos":
        df_del = df_del[df_del["cliente"] == filtro_cli_del]

    if df_del.empty:
        st.info("Nenhum lançamento encontrado com os filtros selecionados.")
    else:
        # Monta um identificador amigável para seleção da visita a excluir
        df_del["label_exclusao"] = df_del.apply(
            lambda r: f"Data: {r['data_checkin']} | {r['abastecedor']} | Cliente: {r['cliente']} | Máq: {r['equipamento']}",
            axis=1
        )

        registro_selecionado = st.selectbox(
            "Selecione o registro que deseja excluir:",
            options=df_del["label_exclusao"].tolist()
        )

        linha_sel = df_del[df_del["label_exclusao"] == registro_selecionado].iloc[0]

        st.markdown(f"""
            <div class="delete-box">
                <h4 style="color: #EF4444; margin-top:0;">⚠️ Detalhes do Registro Selecionado</h4>
                <b>Abastecedor:</b> {linha_sel['abastecedor']}<br>
                <b>Cliente:</b> {linha_sel['cliente']}<br>
                <b>Equipamento:</b> {linha_sel['produto']} (Nº {linha_sel['equipamento']})<br>
                <b>Endereço:</b> {linha_sel['endereco']}<br>
                <b>Check-in:</b> {linha_sel['data_checkin']} | <b>Check-out:</b> {linha_sel['data_checkout']}<br>
                <b>Responsável no local:</b> {linha_sel['responsavel']}
            </div>
        """, unsafe_allow_html=True)

        confirmacao = st.checkbox("Tenho certeza de que desejo remover este atendimento permanentemente.")

        if st.button("🚨 Confirmar e Excluir Registro", type="primary"):
            if not confirmacao:
                st.error("Por favor, marque a caixa de confirmação acima para prosseguir.")
            else:
                payload_exclusao = {
                    "data_checkin": linha_sel["data_checkin"],
                    "abastecedor": linha_sel["abastecedor"],
                    "equipamento": linha_sel["equipamento"]
                }
                
                sucesso = excluir_visita(payload_exclusao)
                
                st.success("✅ Registro excluído com sucesso da base de dados!")
                st.cache_data.clear()
                st.rerun()