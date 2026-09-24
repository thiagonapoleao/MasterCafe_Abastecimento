import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import requests
import json
import os
import plotly.express as px
import time

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL (DARK MODE)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Master Café - Dashboard e Gestão de Visitas",
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
        .card-detalhe {
            background-color: #1E293B;
            border: 1px solid #334155;
            border-left: 5px solid #0D6EFD;
            padding: 14px 18px;
            border-radius: 8px;
            margin-bottom: 16px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
        }
        .danger-box {
            background-color: #450a0a;
            border: 1px solid #991b1b;
            padding: 16px;
            border-radius: 8px;
            color: #fecaca;
            margin: 12px 0;
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. CONSTANTES E INTEGRAÇÃO GOOGLE SHEETS / DRIVE
# -------------------------------------------------------------
SPREADSHEET_ID = "1hGmvoW7c5u5IFESk_GU0nioTiy5sCUvYdqpVycWcVbU"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwQJfe1H2OHTAYGOPZhoOGRl8zazwK4SXf-RvKRMMkQhqJHbmyg4mHBT7AVRLubKOWzbQ/exec"

# -------------------------------------------------------------
# 3. FUNÇÕES AUXILIARES DE CÁLCULO E DADOS
# -------------------------------------------------------------
def formatar_duracao(inicio_str, fim_str):
    """Calcula o tempo de permanência da visita."""
    try:
        if not inicio_str or not fim_str:
            return "Em andamento"
        dt_in = pd.to_datetime(inicio_str, errors="coerce", dayfirst=True, format="mixed")
        dt_out = pd.to_datetime(fim_str, errors="coerce", dayfirst=True, format="mixed")
        if pd.isna(dt_in) or pd.isna(dt_out):
            return "Não registrado"
        delta = dt_out - dt_in
        total_segundos = int(delta.total_seconds())
        if total_segundos < 0:
            return "Inválido"
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        segundos = total_segundos % 60
        if horas > 0:
            return f"{horas}h {minutos}m {segundos}s"
        return f"{minutos}m {segundos}s"
    except Exception:
        return "Não registrado"

def carregar_dados_visitas():
    """Carrega os dados da aba Visitas da planilha Google garantindo ordenação cronológica."""
    ts_nocache = int(datetime.now().timestamp())
    urls = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Visitas&nocache={ts_nocache}",
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet=Visitas&nocache={ts_nocache}"
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

    col_map = {}
    for col in df.columns:
        c_clean = col.strip().lower()
        if "data checkin" in c_clean or ("checkin" in c_clean and "data" in c_clean):
            col_map[col] = "Data Checkin"
        elif "data checkout" in c_clean or ("checkout" in c_clean and "data" in c_clean):
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
    df["Linha_Planilha"] = [i + 2 for i in range(len(df))]

    df["dt_ordem"] = pd.to_datetime(df["Data Checkin"], errors="coerce", dayfirst=True, format="mixed")
    df = df.sort_values(by="dt_ordem", ascending=False).reset_index(drop=True)

    df["Tempo de Visita"] = df.apply(
        lambda r: formatar_duracao(r.get("Data Checkin"), r.get("Data Checkout")), axis=1
    )

    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    df["Mês"] = df["dt_ordem"].apply(lambda d: meses_pt.get(d.month, "Outro") if pd.notna(d) else "Não informado")
    df["Data_Dia"] = df["dt_ordem"].apply(lambda d: d.date() if pd.notna(d) else None)
    df["Data_Formatada"] = df["dt_ordem"].apply(lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "")

    return df

def excluir_registro_completo(data_checkin, abastecedor, equipamento, row_number=None):
    """Envia requisição para exclusão da linha no Google Apps Script."""
    payload = {
        "action": "delete",
        "data_checkin": str(data_checkin).strip(),
        "abastecedor": str(abastecedor).strip(),
        "equipamento": str(equipamento).strip(),
        "row_number": int(row_number) if row_number is not None else None
    }

    sucesso = False
    try:
        headers = {"Content-Type": "text/plain;charset=utf-8"}
        res = requests.post(
            WEBHOOK_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=25,
            allow_redirects=True
        )
        if res.status_code == 200 and ("deleted" in res.text.lower() or "sucesso" in res.text.lower()):
            sucesso = True
    except Exception:
        sucesso = False

    if not sucesso:
        try:
            params = {
                "action": "delete",
                "data_checkin": str(data_checkin).strip(),
                "abastecedor": str(abastecedor).strip(),
                "equipamento": str(equipamento).strip(),
                "row_number": str(row_number) if row_number is not None else ""
            }
            res_get = requests.get(WEBHOOK_URL, params=params, timeout=25, allow_redirects=True)
            if res_get.status_code == 200 and ("deleted" in res_get.text.lower() or "sucesso" in res_get.text.lower()):
                sucesso = True
        except Exception:
            pass

    if os.path.exists("visitas_realizadas.csv"):
        try:
            df_local = pd.read_csv("visitas_realizadas.csv", dtype=str)
            if not df_local.empty:
                col_ch = "data_checkin" if "data_checkin" in df_local.columns else "Data Checkin"
                col_eq = "equipamento" if "equipamento" in df_local.columns else "Equipamento"

                if col_ch in df_local.columns and col_eq in df_local.columns:
                    mask = (
                        (df_local[col_ch].astype(str).str.strip() == str(data_checkin).strip()) &
                        (df_local[col_eq].astype(str).str.strip() == str(equipamento).strip())
                    )
                    df_novo = df_local[~mask]
                    df_novo.to_csv("visitas_realizadas.csv", index=False)
                    sucesso = True
        except Exception:
            pass

    return sucesso

# -------------------------------------------------------------
# 4. APLICAÇÃO PRINCIPAL
# -------------------------------------------------------------
def main():
    if st.session_state.get("sucesso_exclusao", False):
        st.success("✅ Registro excluído com sucesso!")
        st.session_state["sucesso_exclusao"] = False

    with st.sidebar:
        st.title("☕ Menu Master Café")
        pagina = st.radio(
            "Selecione o Módulo:",
            [
                "📊 Dashboard Geral", 
                "👤 Visitas por Abastecedora", 
                "🗑️ Central de Exclusão de Registros"
            ],
            index=0
        )
        st.markdown("---")
        if st.button("🔄 Atualizar Todos os Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df_raw = carregar_dados_visitas()

    if df_raw.empty or "Data Checkin" not in df_raw.columns:
        st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Controle de Visitas e Abastecimento</p></div>', unsafe_allow_html=True)
        st.warning("⚠️ Nenhum registro de visita encontrado na planilha ou no arquivo local.")
        if st.button("🔄 Atualizar"):
            st.cache_data.clear()
            st.rerun()
        return

    hoje_atual = date.today()
    meses_lista_nome = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    mes_atual_nome = meses_lista_nome[hoje_atual.month - 1]

    # =========================================================
    # PÁGINA 1: DASHBOARD GERAL
    # =========================================================
    if pagina == "📊 Dashboard Geral":
        st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Painel de Monitoramento Geral de Visitas</p></div>', unsafe_allow_html=True)

        # Filtros Superiores do Dashboard Geral
        st.markdown("### 🔍 Filtros de Visualização")
        col_fg1, col_fg2, col_fg3 = st.columns(3)

        with col_fg1:
            lista_abast_g = ["Todos"] + sorted([x for x in df_raw["Abastecedor"].dropna().unique().tolist() if str(x).strip()])
            sel_abast_g = st.selectbox("👤 Abastecedor(a):", lista_abast_g, index=0, key="fg_abast")

        with col_fg2:
            opcoes_meses_g = ["Todos"] + meses_lista_nome
            idx_mes_g = opcoes_meses_g.index(mes_atual_nome) if mes_atual_nome in opcoes_meses_g else 0
            sel_mes_g = st.selectbox("📅 Mês:", opcoes_meses_g, index=idx_mes_g, key="fg_mes")

        with col_fg3:
            sel_data_g = st.date_input("📆 Data Específica:", value=hoje_atual, format="DD/MM/YYYY", key="fg_data")

        ver_mes_todo_g = st.checkbox("Exibir todos os dias do mês selecionado nos gráficos (ignorar data única)", value=True, key="fg_chk_mes")

        # Aplicação dos filtros na base
        df_g = df_raw.copy()
        if sel_abast_g != "Todos":
            df_g = df_g[df_g["Abastecedor"] == sel_abast_g]
        if sel_mes_g != "Todos":
            df_g = df_g[df_g["Mês"] == sel_mes_g]
        if not ver_mes_todo_g and sel_data_g is not None:
            df_g = df_g[df_g["Data_Dia"] == sel_data_g]

        st.markdown("---")

        # KPIs
        total_visitas = len(df_g)
        maquinas_atendidas = df_g["Equipamento"].nunique() if "Equipamento" in df_g.columns else 0
        clientes_atendidos = df_g["Cliente"].nunique() if "Cliente" in df_g.columns else 0
        tecnicos_ativos = df_g["Abastecedor"].nunique() if "Abastecedor" in df_g.columns else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="metric-card"><h3>{total_visitas}</h3><p>Total de Visitas</p></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="metric-card"><h3>{maquinas_atendidas}</h3><p>Máquinas Atendidas</p></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="metric-card"><h3>{clientes_atendidos}</h3><p>Clientes Distintos</p></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="metric-card"><h3>{tecnicos_ativos}</h3><p>Abastecedores em Ação</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # -------------------------------------------------------------
        # GRÁFICOS EM BARRAS SOLICITADOS: POR MÊS E POR DIA DE ABASTECEDORA
        # -------------------------------------------------------------
        st.subheader("📈 Evolução de Atendimentos por Mês e por Dia de Abastecedora")
        col_bar_mes, col_bar_dia = st.columns(2)

        with col_bar_mes:
            # Gráfico de Atendimentos por Mês
            df_mes_base = df_raw.copy()
            if sel_abast_g != "Todos":
                df_mes_base = df_mes_base[df_mes_base["Abastecedor"] == sel_abast_g]

            df_mes_agrup = (
                df_mes_base.groupby("Mês")
                .size()
                .reindex(meses_lista_nome)
                .fillna(0)
                .reset_index(name="Atendimentos")
            )

            fig_bar_m = px.bar(
                df_mes_agrup,
                x="Mês",
                y="Atendimentos",
                text="Atendimentos",
                color="Atendimentos",
                color_continuous_scale="Blues",
                title=f"Atendimentos por Mês ({sel_abast_g})"
            )
            fig_bar_m.update_traces(marker=dict(line=dict(width=0)), textposition="outside")
            fig_bar_m.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#F8FAFC",
                height=340,
                xaxis=dict(tickangle=-45)
            )
            st.plotly_chart(fig_bar_m, use_container_width=True)

        with col_bar_dia:
            # Gráfico de Atendimentos por Dia e Abastecedora
            df_dia_base = df_raw[df_raw["dt_ordem"].notna()].copy()
            if sel_mes_g != "Todos":
                df_dia_base = df_dia_base[df_dia_base["Mês"] == sel_mes_g]
            if sel_abast_g != "Todos":
                df_dia_base = df_dia_base[df_dia_base["Abastecedor"] == sel_abast_g]

            if not df_dia_base.empty:
                df_dia_agrup = (
                    df_dia_base.groupby(["Data_Dia", "Data_Formatada", "Abastecedor"])
                    .size()
                    .reset_index(name="Atendimentos")
                    .sort_values(by="Data_Dia", ascending=True)
                )

                ordem_dias = df_dia_agrup["Data_Formatada"].drop_duplicates().tolist()

                fig_bar_d = px.bar(
                    df_dia_agrup,
                    x="Data_Formatada",
                    y="Atendimentos",
                    color="Abastecedor",
                    text="Atendimentos",
                    barmode="group",
                    title=f"Atendimentos por Dia de Abastecedora — {sel_mes_g}",
                    category_orders={"Data_Formatada": ordem_dias}
                )
                fig_bar_d.update_traces(textposition="outside")
                fig_bar_d.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#F8FAFC",
                    height=340,
                    xaxis=dict(type="category", categoryorder="array", categoryarray=ordem_dias, tickangle=-45)
                )
                st.plotly_chart(fig_bar_d, use_container_width=True)
            else:
                st.info(f"Sem dados de atendimentos para o mês de {sel_mes_g}.")

        st.markdown("---")

        # -------------------------------------------------------------
        # RELATÓRIO DETALHADO DE ATENDIMENTOS (COM FOTOS E ASSINATURA)
        # -------------------------------------------------------------
        st.subheader("📋 Relatório Detalhado de Atendimentos (com Fotos e Assinatura)")
        st.caption("Visão completa de cada atendimento realizado, incluindo comprovações visuais e tempo de permanência.")

        if not df_g.empty:
            for idx, r in df_g.iterrows():
                with st.expander(
                    f"☕ {r.get('Data Checkin', '')} — Cliente: {r.get('Cliente', '')} | Máquina: {r.get('Produto', '')} (Nº {r.get('Equipamento', '')}) | Abastecedora: {r.get('Abastecedor', '')}",
                    expanded=(idx < 2)
                ):
                    c_info1, c_info2 = st.columns([1.5, 1])
                    with c_info1:
                        st.markdown(f"""
                            <div class="card-detalhe">
                                <b>🏢 Cliente:</b> {r.get('Cliente')}<br>
                                <b>📍 Endereço:</b> {r.get('Endereço')}<br>
                                <b>☕ Equipamento:</b> {r.get('Produto')} (Nº {r.get('Equipamento')})<br>
                                <b>👤 Abastecedor(a):</b> {r.get('Abastecedor')}<br>
                                <b>✍️ Responsável no Local:</b> {r.get('Responsável')}
                            </div>
                        """, unsafe_allow_html=True)
                    with c_info2:
                        st.markdown(f"""
                            <div class="card-detalhe">
                                <b>⏱️ Horário Check-in:</b> {r.get('Data Checkin')}<br>
                                <b>🏁 Horário Check-out:</b> {r.get('Data Checkout')}<br>
                                <b>⌛ Tempo de Visita:</b> <span style="color:#38bdf8; font-weight:bold;">{r.get('Tempo de Visita')}</span><br>
                                <b>📍 GPS Check-in:</b> {r.get('GPS Checkin')}<br>
                                <b>📍 GPS Check-out:</b> {r.get('GPS Checkout')}
                            </div>
                        """, unsafe_allow_html=True)

                    # Fotos e Assinatura
                    cf1, cf2, cf3 = st.columns(3)
                    with cf1:
                        st.caption("📷 **Máquina Abastecida**")
                        u_ab = str(r.get("Foto Abastecida", "")).strip()
                        if u_ab.startswith("http"):
                            st.image(u_ab, use_container_width=True)
                        else:
                            st.info("Sem foto abastecida.")

                    with cf2:
                        st.caption("✨ **Máquina Limpa**")
                        u_li = str(r.get("Foto Limpa", "")).strip()
                        if u_li.startswith("http"):
                            st.image(u_li, use_container_width=True)
                        else:
                            st.info("Sem foto de limpeza.")

                    with cf3:
                        st.caption("✍️ **Assinatura do Responsável**")
                        u_as = str(r.get("Assinatura", "")).strip()
                        if u_as.startswith("http"):
                            st.image(u_as, use_container_width=True)
                        else:
                            st.info("Sem assinatura.")
        else:
            st.warning("Nenhum atendimento localizado com os filtros selecionados.")

        # -------------------------------------------------------------
        # INSPEÇÃO ESPECÍFICA DINÂMICA
        # -------------------------------------------------------------
        st.markdown("---")
        opcoes_insp = [
            f"{r.get('Data Checkin', '')} | Eq: {r.get('Equipamento', '')} | {r.get('Cliente', '')} | Operador: {r.get('Abastecedor', 'Não informado')}"
            for _, r in df_g.iterrows()
        ]
        
        sel_insp = st.selectbox(
            "Selecione um atendimento para inspecionar individualmente:",
            options=opcoes_insp,
            index=None,
            placeholder="Clique aqui para selecionar uma visita..."
        )

        if sel_insp:
            idx_insp = opcoes_insp.index(sel_insp)
            reg_insp = df_g.iloc[idx_insp]
            nome_abast_inspecionado = reg_insp.get('Abastecedor', 'Não informado')

            st.subheader(f"🔎 Inspeção de um Atendimento da Abastecedora ({nome_abast_inspecionado})")

            st.markdown(f"""
                <div class="metric-card" style="text-align: left; margin-bottom: 15px;">
                    <b>📍 Cliente:</b> {reg_insp.get('Cliente')}<br>
                    <b>☕ Equipamento:</b> {reg_insp.get('Produto')} (Nº {reg_insp.get('Equipamento')})<br>
                    <b>⏱️ Horário:</b> {reg_insp.get('Data Checkin')} até {reg_insp.get('Data Checkout')} (<b>Duração:</b> {reg_insp.get('Tempo de Visita')})<br>
                    <b>👤 Responsável no Local:</b> {reg_insp.get('Responsável')}
                </div>
            """, unsafe_allow_html=True)

            ci1, ci2, ci3 = st.columns(3)
            with ci1:
                st.caption("📷 **Foto Abastecida**")
                u_ab = str(reg_insp.get("Foto Abastecida", "")).strip()
                if u_ab.startswith("http"):
                    st.image(u_ab, use_container_width=True)
                else:
                    st.info("Sem foto registrada.")
            with ci2:
                st.caption("✨ **Foto Limpa**")
                u_li = str(reg_insp.get("Foto Limpa", "")).strip()
                if u_li.startswith("http"):
                    st.image(u_li, use_container_width=True)
                else:
                    st.info("Sem foto registrada.")
            with ci3:
                st.caption("✍️ **Assinatura**")
                u_as = str(reg_insp.get("Assinatura", "")).strip()
                if u_as.startswith("http"):
                    st.image(u_as, use_container_width=True)
                else:
                    st.info("Sem assinatura registrada.")

    # =========================================================
    # PÁGINA 2: VISITAS POR ABASTECEDORA COM FILTROS E MAPA
    # =========================================================
    elif pagina == "👤 Visitas por Abastecedora":
        st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Controle Individual por Abastecedora com Mapa e Tempo</p></div>', unsafe_allow_html=True)

        lista_abastecedoras = ["Todos"] + sorted([x for x in df_raw["Abastecedor"].dropna().unique().tolist() if str(x).strip()])

        st.markdown("### 🔍 Filtros de Consulta Dinâmica")
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            sel_abast = st.selectbox("👤 Escolha o(a) Abastecedor(a):", options=lista_abastecedoras, index=0)

        with col_f2:
            opcoes_meses = ["Todos"] + meses_lista_nome
            idx_mes_padrao = opcoes_meses.index(mes_atual_nome) if mes_atual_nome in opcoes_meses else 0
            sel_mes = st.selectbox("📅 Escolha o Mês:", options=opcoes_meses, index=idx_mes_padrao)

        with col_f3:
            sel_data = st.date_input("📆 Escolha a Data Específica:", value=hoje_atual, format="DD/MM/YYYY")

        ver_mes_todo = st.checkbox("Exibir todos os dias do mês selecionado (ignorar filtro de data única)", value=False)

        df_filtrado = df_raw.copy()

        if sel_abast != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Abastecedor"] == sel_abast]

        if sel_mes != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Mês"] == sel_mes]

        if not ver_mes_todo and sel_data is not None:
            df_filtrado = df_filtrado[df_filtrado["Data_Dia"] == sel_data]

        st.markdown("---")

        total_atendimentos = len(df_filtrado)
        total_clientes = df_filtrado["Cliente"].nunique() if "Cliente" in df_filtrado.columns else 0
        total_equipamentos = df_filtrado["Equipamento"].nunique() if "Equipamento" in df_filtrado.columns else 0

        km1, km2, km3 = st.columns(3)
        with km1:
            st.metric("Total de Atendimentos", total_atendimentos)
        with km2:
            st.metric("Clientes Atendidos", total_clientes)
        with km3:
            st.metric("Máquinas Atendidas", total_equipamentos)

        st.markdown("<br>", unsafe_allow_html=True)

        titulo_operador = f"de **{sel_abast}**" if sel_abast != "Todos" else "de **Todos os Abastecedores**"
        st.markdown(f"#### 📋 Relatório Detalhado de Atendimentos {titulo_operador} (com Fotos e Assinaturas)")

        if not df_filtrado.empty:
            for idx_f, rf in df_filtrado.iterrows():
                with st.expander(
                    f"📍 {rf.get('Data Checkin', '')} — Cliente: {rf.get('Cliente', '')} | Máquina: {rf.get('Produto', '')} (Nº {rf.get('Equipamento', '')})",
                    expanded=(idx_f < 1)
                ):
                    ci_a, ci_b = st.columns([1.5, 1])
                    with ci_a:
                        st.markdown(f"""
                            <div class="card-detalhe">
                                <b>🏢 Cliente:</b> {rf.get('Cliente')}<br>
                                <b>📍 Endereço:</b> {rf.get('Endereço')}<br>
                                <b>☕ Equipamento:</b> {rf.get('Produto')} (Nº {rf.get('Equipamento')})<br>
                                <b>👤 Abastecedor(a):</b> {rf.get('Abastecedor')}<br>
                                <b>✍️ Responsável:</b> {rf.get('Responsável')}
                            </div>
                        """, unsafe_allow_html=True)
                    with ci_b:
                        st.markdown(f"""
                            <div class="card-detalhe">
                                <b>⏱️ Horário Check-in:</b> {rf.get('Data Checkin')}<br>
                                <b>🏁 Horário Check-out:</b> {rf.get('Data Checkout')}<br>
                                <b>⌛ Tempo de Visita:</b> <span style="color:#38bdf8; font-weight:bold;">{rf.get('Tempo de Visita')}</span><br>
                                <b>📍 GPS Check-in:</b> {rf.get('GPS Checkin')}<br>
                                <b>📍 GPS Check-out:</b> {rf.get('GPS Checkout')}
                            </div>
                        """, unsafe_allow_html=True)

                    cfa, cfb, cfc = st.columns(3)
                    with cfa:
                        st.caption("📷 **Foto Abastecida**")
                        u1 = str(rf.get("Foto Abastecida", "")).strip()
                        if u1.startswith("http"):
                            st.image(u1, use_container_width=True)
                        else:
                            st.info("Sem foto abastecida.")
                    with cfb:
                        st.caption("✨ **Foto Limpa**")
                        u2 = str(rf.get("Foto Limpa", "")).strip()
                        if u2.startswith("http"):
                            st.image(u2, use_container_width=True)
                        else:
                            st.info("Sem foto de limpeza.")
                    with cfc:
                        st.caption("✍️ **Assinatura**")
                        u3 = str(rf.get("Assinatura", "")).strip()
                        if u3.startswith("http"):
                            st.image(u3, use_container_width=True)
                        else:
                            st.info("Sem assinatura.")

            # Mapa de Roteiro
            st.markdown(f"#### 📍 Mapa de Roteiro e Locais Atendidos {titulo_operador}")
            pontos_mapa = []
            for _, row_g in df_filtrado.iterrows():
                gps_in = str(row_g.get("GPS Checkin", "")).strip()
                if "," in gps_in and "não" not in gps_in.lower():
                    try:
                        pt = gps_in.split(",")
                        pontos_mapa.append({
                            "latitude": float(pt[0].strip()),
                            "longitude": float(pt[1].strip()),
                            "tipo": "Check-in",
                            "cliente": row_g.get("Cliente", "")
                        })
                    except Exception:
                        pass
                
                gps_out = str(row_g.get("GPS Checkout", "")).strip()
                if "," in gps_out and "não" not in gps_out.lower():
                    try:
                        pt2 = gps_out.split(",")
                        pontos_mapa.append({
                            "latitude": float(pt2[0].strip()),
                            "longitude": float(pt2[1].strip()),
                            "tipo": "Check-out",
                            "cliente": row_g.get("Cliente", "")
                        })
                    except Exception:
                        pass

            if pontos_mapa:
                df_mapa_geo = pd.DataFrame(pontos_mapa)
                st.map(df_mapa_geo, latitude="latitude", longitude="longitude", size=25, color="#0D6EFD")
            else:
                st.caption("ℹ️ Nenhuma coordenada GPS válida registrada para os filtros selecionados.")
        else:
            st.warning("Nenhum atendimento localizado com a combinação de filtros selecionada.")

    # =========================================================
    # PÁGINA 3: CENTRAL DE EXCLUSÃO DE REGISTROS
    # =========================================================
    elif pagina == "🗑️ Central de Exclusão de Registros":
        st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Central de Exclusão de Registros de Visita</p></div>', unsafe_allow_html=True)

        st.info("ℹ️ Selecione um registro no campo abaixo para auditar os dados e fotos antes de confirmar a exclusão.")

        df_del = df_raw.copy()

        busca = st.text_input("🔍 Filtrar registros por Equipamento, Cliente ou Técnico:", placeholder="Ex: 6509, Thiago, Senac...").strip().lower()
        if busca:
            df_del = df_del[
                df_del["Equipamento"].astype(str).str.lower().str.contains(busca, na=False) |
                df_del["Cliente"].astype(str).str.lower().str.contains(busca, na=False) |
                df_del["Abastecedor"].astype(str).str.lower().str.contains(busca, na=False) |
                df_del["Data Checkin"].astype(str).str.lower().str.contains(busca, na=False)
            ]

        st.markdown(f"**Registros encontrados (ordenados por data de registro):** `{len(df_del)}`")

        colunas_exibicao = [c for c in ["Linha_Planilha", "Data Checkin", "Tempo de Visita", "Equipamento", "Cliente", "Abastecedor", "Produto", "Responsável"] if c in df_del.columns]
        st.dataframe(df_del[colunas_exibicao], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("Excluir Registro da Planilha")

        if not df_del.empty:
            df_del_reset = df_del.reset_index(drop=True)
            opcoes_del = [
                f"{r.get('Data Checkin', '')} | Eq: {r.get('Equipamento', '')} | {r.get('Cliente', '')} ({r.get('Abastecedor', '')}) [Linha {r.get('Linha_Planilha')}]"
                for _, r in df_del_reset.iterrows()
            ]

            item_selecionado = st.selectbox(
                "Escolha o registro que deseja excluir:",
                options=opcoes_del,
                index=None,
                placeholder="Selecione um registro da lista..."
            )

            if item_selecionado is not None:
                idx_escolhido = opcoes_del.index(item_selecionado)
                registro_alvo = df_del_reset.iloc[idx_escolhido]

                with st.expander("📷 Conferir Fotos e Assinatura deste Registro", expanded=True):
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        st.caption("📷 **Foto Abastecida**")
                        u_ab = str(registro_alvo.get("Foto Abastecida", "")).strip()
                        if u_ab.startswith("http"):
                            st.image(u_ab, use_container_width=True)
                        else:
                            st.write("Sem foto.")
                    with col_f2:
                        st.caption("✨ **Foto Limpa**")
                        u_li = str(registro_alvo.get("Foto Limpa", "")).strip()
                        if u_li.startswith("http"):
                            st.image(u_li, use_container_width=True)
                        else:
                            st.write("Sem foto.")
                    with col_f3:
                        st.caption("✍️ **Assinatura**")
                        u_as = str(registro_alvo.get("Assinatura", "")).strip()
                        if u_as.startswith("http"):
                            st.image(u_as, use_container_width=True)
                        else:
                            st.write("Sem assinatura.")

                st.markdown(f"""
                    <div class="danger-box">
                        <b>Confirmação de Exclusão:</b><br>
                        • <b>Data Check-in:</b> {registro_alvo.get('Data Checkin')}<br>
                        • <b>Duração da Visita:</b> {registro_alvo.get('Tempo de Visita')}<br>
                        • <b>Equipamento:</b> {registro_alvo.get('Equipamento')}<br>
                        • <b>Cliente:</b> {registro_alvo.get('Cliente')}<br>
                        • <b>Linha na Planilha:</b> {registro_alvo.get('Linha_Planilha')}
                    </div>
                """, unsafe_allow_html=True)

                if st.button("🗑️ Confirmar Exclusão Definitiva", type="primary", use_container_width=True):
                    with st.spinner("Excluindo linha da planilha..."):
                        sucesso = excluir_registro_completo(
                            data_checkin=registro_alvo.get("Data Checkin", ""),
                            abastecedor=registro_alvo.get("Abastecedor", ""),
                            equipamento=registro_alvo.get("Equipamento", ""),
                            row_number=registro_alvo.get("Linha_Planilha")
                        )

                    if sucesso:
                        st.session_state["sucesso_exclusao"] = True
                        st.cache_data.clear()
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível excluir o registro. Verifique a conexão com o Webhook.")
            else:
                st.caption("👈 Selecione um registro no campo acima para habilitar a confirmação de exclusão.")
        else:
            st.warning("Nenhum registro encontrado com o termo pesquisado.")

if __name__ == "__main__":
    main()