import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import requests
import json
import plotly.express as px

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL (DARK MODE)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Dashboard de Visitas",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .stApp {
            background-color: #0F172A;
            color: #F8FAFC;
        }
        .main-header {
            text-align: center;
            padding: 16px;
            border-radius: 10px;
            background: linear-gradient(135deg, #1E3A8A, #0D6EFD);
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        .metric-card {
            background-color: #1E293B;
            border: 1px solid #334155;
            padding: 18px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-card h3 {
            margin: 0;
            font-size: 1.8rem;
            color: #38BDF8;
        }
        .metric-card p {
            margin: 5px 0 0 0;
            color: #94A3B8;
            font-weight: 500;
        }
        .status-badge {
            background-color: #1E293B;
            border-left: 4px solid #0D6EFD;
            padding: 10px 14px;
            border-radius: 4px 8px 8px 4px;
            margin: 8px 0;
            color: #E2E8F0;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. CONSTANTES E INTEGRAÇÃO GOOGLE SHEETS / DRIVE
# -------------------------------------------------------------
SPREADSHEET_ID = "1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwQJfe1H2OHTAYGOPZhoOGRl8zazwK4SXf-RvKRMMkQhqJHbmyg4mHBT7AVRLubKOWzbQ/exec"

# -------------------------------------------------------------
# 3. CARREGAMENTO DOS DADOS DE VISITAS
# -------------------------------------------------------------
@st.cache_data(ttl=30)
def carregar_dados_visitas():
    """Carrega os dados da aba Visitas diretamente da planilha Google ou do backup local."""
    urls = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Visitas",
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet=Visitas"
    ]
    
    df = None
    for url in urls:
        try:
            df_temp = pd.read_csv(url, engine="python", on_bad_lines="skip", dtype=str)
            if not df_temp.empty and len(df_temp.columns) >= 4:
                df = df_temp
                break
        except Exception:
            continue

    # Fallback para o arquivo local se a planilha online não responder
    if df is None or df.empty:
        if os.path.exists("visitas_realizadas.csv"):
            try:
                df = pd.read_csv("visitas_realizadas.csv", dtype=str)
            except Exception:
                df = pd.DataFrame()
        else:
            df = pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # Padroniza nomes de colunas
    col_map = {}
    for col in df.columns:
        c_clean = col.strip().lower()
        if "data checkin" in c_clean or "checkin" in c_clean and "data" in c_clean:
            col_map[col] = "Data Checkin"
        elif "data checkout" in c_clean or "checkout" in c_clean and "data" in c_clean:
            col_map[col] = "Data Checkout"
        elif "abastecedor" in c_clean:
            col_map[col] = "Abastecedor"
        elif "equipamento" in c_clean:
            col_map[col] = "Equipamento"
        elif "cliente" in c_clean:
            col_map[col] = "Cliente"
        elif "produto" in c_clean:
            col_map[col] = "Produto"
        elif "endereço" in c_clean or "endereco" in c_clean:
            col_map[col] = "Endereço"
        elif "gps checkin" in c_clean:
            col_map[col] = "GPS Checkin"
        elif "gps checkout" in c_clean:
            col_map[col] = "GPS Checkout"
        elif "responsável" in c_clean or "responsavel" in c_clean:
            col_map[col] = "Responsável"
        elif "foto abastecida" in c_clean:
            col_map[col] = "Foto Abastecida"
        elif "foto limpa" in c_clean:
            col_map[col] = "Foto Limpa"
        elif "assinatura" in c_clean:
            col_map[col] = "Assinatura"

    df = df.rename(columns=col_map)
    return df

def excluir_registro_planilha(data_checkin, abastecedor, equipamento):
    """Envia requisição para exclusão de registro via Webhook Apps Script."""
    try:
        payload = {
            "action": "delete",
            "data_checkin": str(data_checkin).strip(),
            "abastecedor": str(abastecedor).strip(),
            "equipamento": str(equipamento).strip()
        }
        headers = {"Content-Type": "text/plain;charset=utf-8"}
        res = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers, timeout=20)
        return res.status_code == 200
    except Exception:
        return False

# -------------------------------------------------------------
# 4. INTERFACE PRINCIPAL DO DASHBOARD
# -------------------------------------------------------------
def main():
    st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Painel de Monitoramento de Visitas e Manutenções</p></div>', unsafe_allow_html=True)

    df_raw = carregar_dados_visitas()

    if df_raw.empty or "Data Checkin" not in df_raw.columns:
        st.warning("⚠️ Nenhum registro de visita encontrado na planilha ou no histórico local.")
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()
        return

    df = df_raw.copy()

    # ---------------------------------------------------------
    # BARRA LATERAL: FILTROS
    # ---------------------------------------------------------
    with st.sidebar:
        st.header("🔍 Filtros de Consulta")

        if st.button("🔄 Atualizar Painel"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # Configuração padrão do intervalo de datas (últimos 30 dias até hoje)
        hoje = date.today()
        inicio_padrao = hoje - timedelta(days=30)
        
        filtro_data = st.date_input(
            "Período das Visitas:",
            value=(inicio_padrao, hoje),
            format="DD/MM/YYYY"
        )

        # ---------------------------------------------------------
        # FILTRO DE DATAS BLINDADO CONTRA ERRO DE COMPARAÇÃO
        # ---------------------------------------------------------
        df["dt_checkin"] = pd.to_datetime(df["Data Checkin"], errors="coerce", dayfirst=True, format="mixed")

        d_inicio, d_fim = None, None
        if isinstance(filtro_data, (list, tuple)):
            if len(filtro_data) == 2:
                d_inicio, d_fim = filtro_data[0], filtro_data[1]
            elif len(filtro_data) == 1:
                d_inicio = d_fim = filtro_data[0]
        elif filtro_data:
            d_inicio = d_fim = filtro_data

        if d_inicio and d_fim:
            t_inicio = pd.Timestamp(d_inicio).replace(hour=0, minute=0, second=0, microsecond=0)
            t_fim = pd.Timestamp(d_fim).replace(hour=23, minute=59, second=59, microsecond=999999)
            
            df = df[
                df["dt_checkin"].notna() & 
                (df["dt_checkin"] >= t_inicio) & 
                (df["dt_checkin"] <= t_fim)
            ]

        # Filtro de Abastecedor / Técnico
        lista_abast = ["Todos"] + sorted(df["Abastecedor"].dropna().unique().tolist()) if "Abastecedor" in df.columns else ["Todos"]
        sel_abast = st.selectbox("Técnico / Abastecedor:", lista_abast)
        if sel_abast != "Todos":
            df = df[df["Abastecedor"] == sel_abast]

        # Filtro de Equipamento
        if "Equipamento" in df.columns:
            lista_equip = ["Todos"] + sorted(df["Equipamento"].dropna().unique().tolist())
            sel_equip = st.selectbox("Número do Equipamento:", lista_equip)
            if sel_equip != "Todos":
                df = df[df["Equipamento"] == sel_equip]

        st.caption(f"Registros exibidos: **{len(df)}**")

    # ---------------------------------------------------------
    # 5. CARTOES DE MÉTRICAS (KPIs)
    # ---------------------------------------------------------
    total_visitas = len(df)
    maquinas_atendidas = df["Equipamento"].nunique() if "Equipamento" in df.columns else 0
    clientes_atendidos = df["Cliente"].nunique() if "Cliente" in df.columns else 0
    tecnicos_ativos = df["Abastecedor"].nunique() if "Abastecedor" in df.columns else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div class="metric-card"><h3>{total_visitas}</h3><p>Total de Visitas</p></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div class="metric-card"><h3>{maquinas_atendidas}</h3><p>Máquinas Atendidas</p></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div class="metric-card"><h3>{clientes_atendidos}</h3><p>Clientes Distintos</p></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div class="metric-card"><h3>{tecnicos_ativos}</h3><p>Técnicos em Ação</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 6. GRÁFICOS VISUAIS
    # ---------------------------------------------------------
    if not df.empty:
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("📊 Atendimentos por Técnico")
            if "Abastecedor" in df.columns and not df["Abastecedor"].dropna().empty:
                df_tec = df["Abastecedor"].value_counts().reset_index()
                df_tec.columns = ["Técnico", "Atendimentos"]
                fig_tec = px.bar(
                    df_tec, 
                    x="Atendimentos", 
                    y="Técnico", 
                    orientation="h",
                    color="Atendimentos",
                    color_continuous_scale="Blues",
                    text="Atendimentos"
                )
                fig_tec.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#F8FAFC",
                    yaxis=dict(autorange="reversed")
                )
                st.plotly_chart(fig_tec, use_container_width=True)
            else:
                st.info("Sem dados de técnicos no período.")

        with col_g2:
            st.subheader("☕ Top 10 Clientes Atendidos")
            if "Cliente" in df.columns and not df["Cliente"].dropna().empty:
                df_cli = df["Cliente"].value_counts().head(10).reset_index()
                df_cli.columns = ["Cliente", "Visitas"]
                fig_cli = px.bar(
                    df_cli,
                    x="Visitas",
                    y="Cliente",
                    orientation="h",
                    color="Visitas",
                    color_continuous_scale="Teal",
                    text="Visitas"
                )
                fig_cli.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#F8FAFC",
                    yaxis=dict(autorange="reversed")
                )
                st.plotly_chart(fig_cli, use_container_width=True)
            else:
                st.info("Sem dados de clientes no período.")

    # ---------------------------------------------------------
    # 7. TABELA DETALHADA E EVIDÊNCIAS (FOTOS / ASSINATURA)
    # ---------------------------------------------------------
    st.subheader("📋 Detalhes dos Atendimentos Realizados")

    colunas_visiveis = [
        c for c in ["Data Checkin", "Data Checkout", "Abastecedor", "Equipamento", "Cliente", "Produto", "Responsável"]
        if c in df.columns
    ]

    st.dataframe(df[colunas_visiveis], use_container_width=True)

    # ---------------------------------------------------------
    # 8. INSPEÇÃO DE EVIDÊNCIAS DE UMA VISITA ESPECÍFICA
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("🔎 Inspecionar Fotos e Assinatura de um Atendimento")

    if not df.empty:
        opcoes_visitas = []
        for idx, row in df.iterrows():
            d_ch = row.get("Data Checkin", "")
            eq = row.get("Equipamento", "")
            cli = row.get("Cliente", "")
            opcoes_visitas.append(f"{idx} - {d_ch} | Eq: {eq} | {cli}")

        sel_idx_str = st.selectbox("Selecione o registro para visualizar as fotos:", opcoes_visitas)
        idx_selecionado = int(sel_idx_str.split(" - ")[0])
        registro = df.loc[idx_selecionado]

        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            st.caption("📷 **Máquina Abastecida**")
            url_abast = str(registro.get("Foto Abastecida", "")).strip()
            if url_abast and url_abast.startswith("http"):
                st.image(url_abast, use_container_width=True)
            else:
                st.info("Sem foto registrada.")

        with col_f2:
            st.caption("✨ **Máquina Limpa**")
            url_limpa = str(registro.get("Foto Limpa", "")).strip()
            if url_limpa and url_limpa.startswith("http"):
                st.image(url_limpa, use_container_width=True)
            else:
                st.info("Sem foto registrada.")

        with col_f3:
            st.caption("✍️ **Assinatura do Responsável**")
            url_ass = str(registro.get("Assinatura", "")).strip()
            if url_ass and url_ass.startswith("http"):
                st.image(url_ass, use_container_width=True)
            else:
                st.info("Sem assinatura registrada.")

        # Opção de exclusão do registro inspecionado
        with st.expander("🗑️ Excluir este registro da planilha"):
            st.warning("Esta ação removerá a linha correspondente na aba 'Visitas' da planilha Google.")
            if st.button("Confirmar Exclusão do Registro", key=f"del_{idx_selecionado}"):
                sucesso = excluir_registro_planilha(
                    registro.get("Data Checkin", ""),
                    registro.get("Abastecedor", ""),
                    registro.get("Equipamento", "")
                )
                if sucesso:
                    st.success("Registro removido com sucesso!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Não foi possível excluir o registro. Verifique a conexão com o Webhook.")

    # ---------------------------------------------------------
    # 9. MAPA DE LOCALIZAÇÃO DOS ATENDIMENTOS
    # ---------------------------------------------------------
    if "GPS Checkin" in df.columns:
        st.markdown("---")
        st.subheader("📍 Mapa dos Locais de Check-in")
        
        pontos_gps = []
        for _, row in df.iterrows():
            raw_gps = str(row.get("GPS Checkin", "")).strip()
            if "," in raw_gps and "não" not in raw_gps.lower():
                try:
                    parts = raw_gps.split(",")
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    pontos_gps.append({"latitude": lat, "longitude": lon})
                except Exception:
                    continue

        if pontos_gps:
            df_mapa = pd.DataFrame(pontos_gps)
            st.map(df_mapa)
        else:
            st.caption("Nenhuma coordenada GPS válida registrada nos atendimentos filtrados.")

if __name__ == "__main__":
    main()