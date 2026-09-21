import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse
import unicodedata

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL (DARK MODE / CORPORATIVO)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Dashboard de Visitas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS em tons de azul escuro e cinzento corporativo
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

def normalizar_coluna(col):
    if not isinstance(col, str):
        col = str(col)
    texto = unicodedata.normalize('NFKD', col).encode('ASCII', 'ignore').decode('ASCII')
    return texto.strip().lower()

@st.cache_data(ttl=30)
def carregar_dados_visitas():
    """
    Carrega os dados registados na aba 'Visitas' da folha de cálculo Google.
    Gera dados demonstrativos se a folha ainda estiver vazia.
    """
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

    # Estrutura base de contingência com registos de exemplo caso a folha esteja vazia
    if df.empty or "data_checkin" not in df.columns or len(df) == 0:
        base_exemplo = [
            {"data_checkin": "21/09/2026 08:30:00", "data_checkout": "21/09/2026 09:05:00", "abastecedor": "Thiago Napoleão", "equipamento": "02020383", "cliente": "JBT FOOD TECH", "produto": "KREA ES4S-R/BR", "endereco": "AV CAMILO DINUCCI, 4605", "geo_checkin": "-21.7946, -48.1766", "geo_checkout": "-21.7947, -48.1765", "responsavel": "Marcos"},
            {"data_checkin": "21/09/2026 09:40:00", "data_checkout": "21/09/2026 10:10:00", "abastecedor": "Thiago Napoleão", "equipamento": "102885", "cliente": "CAFETERIA KAFFE", "produto": "FIORENZATO", "endereco": "AV PRES KENNEDY, 1500", "geo_checkin": "-21.1767, -47.8208", "geo_checkout": "-21.1768, -47.8207", "responsavel": "Ana Paula"},
            {"data_checkin": "21/09/2026 10:45:00", "data_checkout": "21/09/2026 11:35:00", "abastecedor": "Mariana Operações", "equipamento": "1712942", "cliente": "GELATO BORELLI", "produto": "FAEMA E98", "endereco": "AV JUSCELINO KUBITSCHEK, 5000", "geo_checkin": "-20.8113, -49.3758", "geo_checkout": "-20.8115, -49.3757", "responsavel": "Lucas"},
            {"data_checkin": "20/09/2026 14:15:00", "data_checkout": "20/09/2026 14:40:00", "abastecedor": "Carla Silva", "equipamento": "1727812", "cliente": "NAPOLEAO CAFE", "produto": "MOINHO FAEMA", "endereco": "RUA NAPOLEAO SELMI-DEI, 756", "geo_checkin": "-21.7821, -48.1812", "geo_checkout": "-21.7822, -48.1811", "responsavel": "Cláudia"},
            {"data_checkin": "20/09/2026 15:20:00", "data_checkout": "20/09/2026 16:15:00", "abastecedor": "Thiago Napoleão", "equipamento": "1789218", "cliente": "SABORES DA LAINE", "produto": "LA CIMBALI 2GR", "endereco": "AV PROF JORGE CORREA, 1118", "geo_checkin": "-21.7915, -48.1722", "geo_checkout": "-21.7916, -48.1721", "responsavel": "Renata"},
            {"data_checkin": "19/09/2026 11:00:00", "data_checkout": "19/09/2026 11:30:00", "abastecedor": "Carla Silva", "equipamento": "7660", "cliente": "MULTIBRAS WHIRLPOOL", "produto": "AULIKA 220V", "endereco": "AVENIDA 80-A, 777", "geo_checkin": "-22.4132, -47.5611", "geo_checkout": "-22.4131, -47.5612", "responsavel": "Pedro"}
        ]
        df = pd.DataFrame(base_exemplo)

    # Tratamento de datas e durações
    df["dt_checkin"] = pd.to_datetime(df["data_checkin"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    df["dt_checkout"] = pd.to_datetime(df["data_checkout"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    
    # Cálculo do tempo de atendimento em minutos
    df["duracao_minutos"] = (df["dt_checkout"] - df["dt_checkin"]).dt.total_seconds() / 60.0
    df["duracao_minutos"] = df["duracao_minutos"].apply(lambda x: round(max(x, 1.0), 1) if pd.notnull(x) else 0.0)

    # Extração de dia e mês/ano
    df["data_dia"] = df["dt_checkin"].dt.strftime("%d/%m/%Y")
    df["mes_ano"] = df["dt_checkin"].dt.strftime("%m/%Y")
    df["hora_checkin"] = df["dt_checkin"].dt.strftime("%H:%M")
    df["hora_checkout"] = df["dt_checkout"].dt.strftime("%H:%M")

    return df

# -------------------------------------------------------------
# 3. INTERFACE E BARRA LATERAL COM FILTROS DINÂMICOS
# -------------------------------------------------------------
st.title("☕ Master Café — Cockpit de Operações e Visitas")
st.caption("Acompanhamento gerencial em tempo real de abastecimentos, produtividade e tempos de ciclo.")

df_raw = carregar_dados_visitas()

with st.sidebar:
    st.header("🔍 Filtros de Operação")
    
    # Filtro por Abastecedor
    abastecedores = sorted([x for x in df_raw["abastecedor"].dropna().unique().tolist() if str(x).strip() != ""])
    abast_selecionados = st.multiselect("Abastecedor(a):", options=abastecedores, default=abastecedores)

    # Filtro por Intervalo de Datas
    min_date = df_raw["dt_checkin"].min()
    max_date = df_raw["dt_checkin"].max()
    
    if pd.isna(min_date):
        min_date = datetime.now() - timedelta(days=30)
    if pd.isna(max_date):
        max_date = datetime.now()

    intervalo_data = st.date_input(
        "Período de Análise:",
        value=(min_date.date(), max_date.date())
    )

    # Filtro por Cliente
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

# -------------------------------------------------------------
# 4. CARDS DE KPIS (INDICADORES PRINCIPAIS)
# -------------------------------------------------------------
total_visitas = len(df)
total_clientes = df["cliente"].nunique() if total_visitas > 0 else 0
total_maquinas = df["equipamento"].nunique() if total_visitas > 0 else 0
tempo_medio_geral = round(df["duracao_minutos"].mean(), 1) if total_visitas > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total de Visitas</div>
            <div class="metric-value">{total_visitas}</div>
            <div class="metric-sub">Atendimentos concluídos</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Clientes Atendidos</div>
            <div class="metric-value">{total_clientes}</div>
            <div class="metric-sub">Empresas e pontos distintos</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Máquinas Abastecidas</div>
            <div class="metric-value">{total_maquinas}</div>
            <div class="metric-sub">Equipamentos únicos</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Tempo Médio Geral</div>
            <div class="metric-value">{tempo_medio_geral} min</div>
            <div class="metric-sub">Média por máquina em campo</div>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# 5. SEÇÃO DE INSIGHTS AUTOMÁTICOS
# -------------------------------------------------------------
if total_visitas > 0:
    maior_abast = df["abastecedor"].value_counts().index[0]
    qtd_maior = df["abastecedor"].value_counts().iloc[0]
    cliente_mais_visitado = df["cliente"].value_counts().index[0]
    tempo_max = df["duracao_minutos"].max()
    cli_tempo_max = df.loc[df["duracao_minutos"].idxmax()]["cliente"]
    
    st.markdown(f"""
        <div class="insight-card">
            <b>💡 Destaques da Operação Master Café:</b><br>
            • <b>Produtividade:</b> O(A) colaborador(a) <b>{maior_abast}</b> lidera o período com <b>{qtd_maior}</b> visitas realizadas.<br>
            • <b>Frequência:</b> O cliente com maior volume de atendimentos registados foi <b>{cliente_mais_visitado}</b>.<br>
            • <b>Atenção de Eficiência:</b> O atendimento mais longo demorou <b>{tempo_max} minutos</b> em <b>{cli_tempo_max}</b>.
        </div>
    """, unsafe_allow_html=True)
else:
    st.warning("Nenhum registo encontrado para os filtros selecionados.")

# -------------------------------------------------------------
# 6. GRÁFICOS VISUAIS E ANÁLISE DE TEMPO MÉDIO
# -------------------------------------------------------------
st.markdown('<div class="block-header">📊 Indicadores de Eficiência e Tempo de Ciclo</div>', unsafe_allow_html=True)

c_graf1, c_graf2 = st.columns(2)

with c_graf1:
    # 6.1 Tempo médio por Cliente
    df_tempo_cliente = df.groupby("cliente")["duracao_minutos"].mean().reset_index().sort_values("duracao_minutos", ascending=True)
    df_tempo_cliente["duracao_minutos"] = df_tempo_cliente["duracao_minutos"].round(1)

    fig_cli = px.bar(
        df_tempo_cliente,
        x="duracao_minutos",
        y="cliente",
        orientation="h",
        title="Tempo Médio de Atendimento por Cliente (minutos)",
        text="duracao_minutos",
        color="duracao_minutos",
        color_continuous_scale=["#0D6EFD", "#38BDF8"]
    )
    fig_cli.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E293B",
        paper_bgcolor="#1E293B",
        xaxis_title="Minutos",
        yaxis_title="",
        coloraxis_showscale=False,
        height=360
    )
    st.plotly_chart(fig_cli, use_container_width=True)

with c_graf2:
    # 6.2 Tempo médio por Abastecedor
    df_tempo_abast = df.groupby("abastecedor")["duracao_minutos"].mean().reset_index().sort_values("duracao_minutos", ascending=False)
    df_tempo_abast["duracao_minutos"] = df_tempo_abast["duracao_minutos"].round(1)

    fig_abast = px.bar(
        df_tempo_abast,
        x="abastecedor",
        y="duracao_minutos",
        title="Tempo Médio de Atendimento por Abastecedor (minutos)",
        text="duracao_minutos",
        color="duracao_minutos",
        color_continuous_scale=["#1E3A8A", "#0D6EFD"]
    )
    fig_abast.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E293B",
        paper_bgcolor="#1E293B",
        xaxis_title="",
        yaxis_title="Minutos",
        coloraxis_showscale=False,
        height=360
    )
    st.plotly_chart(fig_abast, use_container_width=True)

c_graf3, c_graf4 = st.columns(2)

with c_graf3:
    # 6.3 Volume de Atendimentos por Modelo / Produto
    df_prod = df["produto"].value_counts().reset_index()
    df_prod.columns = ["produto", "total"]

    fig_prod = px.pie(
        df_prod,
        names="produto",
        values="total",
        title="Distribuição de Visitas por Modelo de Máquina",
        hole=0.45,
        color_discrete_sequence=["#0D6EFD", "#38BDF8", "#0284C7", "#60A5FA", "#93C5FD"]
    )
    fig_prod.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E293B",
        paper_bgcolor="#1E293B",
        height=350
    )
    st.plotly_chart(fig_prod, use_container_width=True)

with c_graf4:
    # 6.4 Histograma/Tendência de Atendimentos ao Longo dos Dias
    df_timeline = df.groupby("data_dia").size().reset_index(name="visitas")
    fig_line = px.line(
        df_timeline,
        x="data_dia",
        y="visitas",
        markers=True,
        title="Volume de Visitas por Dia",
        line_shape="spline"
    )
    fig_line.update_traces(line_color="#38BDF8", marker=dict(size=8, color="#0D6EFD"))
    fig_line.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E293B",
        paper_bgcolor="#1E293B",
        xaxis_title="Data",
        yaxis_title="Total de Visitas",
        height=350
    )
    st.plotly_chart(fig_line, use_container_width=True)

# -------------------------------------------------------------
# 7. REGISTO DETALHADO: DATA, HORÁRIOS E LOCALIZAÇÃO (CHECKIN/CHECKOUT)
# -------------------------------------------------------------
st.markdown('<div class="block-header">📍 Auditoria de Visitas: Data, Horários e Localização por Abastecedor</div>', unsafe_allow_html=True)

colunas_auditoria = [
    "abastecedor", "cliente", "equipamento", "endereco", 
    "data_dia", "hora_checkin", "hora_checkout", "duracao_minutos", 
    "geo_checkin", "geo_checkout", "responsavel"
]
colunas_exibicao = [c for c in colunas_auditoria if c in df.columns]

df_auditoria = df[colunas_exibicao].rename(columns={
    "abastecedor": "Abastecedor",
    "cliente": "Cliente",
    "equipamento": "Nº Máquina",
    "endereco": "Endereço",
    "data_dia": "Data",
    "hora_checkin": "Hora Início",
    "hora_checkout": "Hora Fim",
    "duracao_minutos": "Duração (min)",
    "geo_checkin": "GPS Check-in",
    "geo_checkout": "GPS Check-out",
    "responsavel": "Assinado Por"
})

st.dataframe(
    df_auditoria,
    use_container_width=True,
    hide_index=True
)

# -------------------------------------------------------------
# 8. TABELAS AGREGADAS: DESEMPENHO NO MÊS E NO DIA
# -------------------------------------------------------------
st.markdown('<div class="block-header">📈 Produção Consolidada por Abastecedor (Mês e Dia)</div>', unsafe_allow_html=True)

tab_mes, tab_dia = st.tabs(["📅 Consolidado por Mês", "🗓️ Consolidado por Dia"])

with tab_mes:
    # Agregação por Mês, Abastecedor
    df_mes = df.groupby(["mes_ano", "abastecedor"]).agg(
        total_visitas=("equipamento", "count"),
        clientes_unicos=("cliente", "nunique"),
        maquinas_unicas=("equipamento", "nunique"),
        tempo_medio_minutos=("duracao_minutos", "mean")
    ).reset_index()

    df_mes["tempo_medio_minutos"] = df_mes["tempo_medio_minutos"].round(1)
    df_mes = df_mes.rename(columns={
        "mes_ano": "Mês/Ano",
        "abastecedor": "Abastecedor",
        "total_visitas": "Total de Atendimentos",
        "clientes_unicos": "Clientes Distintos",
        "maquinas_unicas": "Máquinas Distintas",
        "tempo_medio_minutos": "Tempo Médio (min)"
    }).sort_values(by=["Mês/Ano", "Total de Atendimentos"], ascending=[False, False])

    st.dataframe(df_mes, use_container_width=True, hide_index=True)

with tab_dia:
    # Agregação por Dia, Abastecedor
    df_dia = df.groupby(["data_dia", "abastecedor"]).agg(
        total_visitas=("equipamento", "count"),
        clientes_unicos=("cliente", "nunique"),
        maquinas_unicas=("equipamento", "nunique"),
        tempo_medio_minutos=("duracao_minutos", "mean")
    ).reset_index()

    df_dia["tempo_medio_minutos"] = df_dia["tempo_medio_minutos"].round(1)
    df_dia = df_dia.rename(columns={
        "data_dia": "Data (Dia)",
        "abastecedor": "Abastecedor",
        "total_visitas": "Total de Atendimentos",
        "clientes_unicos": "Clientes Distintos",
        "maquinas_unicas": "Máquinas Distintas",
        "tempo_medio_minutos": "Tempo Médio (min)"
    }).sort_values(by=["Data (Dia)", "Total de Atendimentos"], ascending=[False, False])

    st.dataframe(df_dia, use_container_width=True, hide_index=True)