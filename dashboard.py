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
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbz29P22qs_RBA6halAkFlnwh8phr76zVsq7giCAwXfPIPBafgkhLUiPSLkSbEwBukEJAg/exec"

# -------------------------------------------------------------
# 3. CARREGAMENTO DOS DADOS COM PARÂMETRO ANTI-CACHE
# -------------------------------------------------------------
def carregar_dados_visitas():
    """Carrega os dados da aba Visitas da planilha Google sem cache estático."""
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

    # 1. Envio primário via POST
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

    # 2. Fallback via GET se o POST tiver sofrido bloqueio de redirect
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

    # 3. Exclusão também do backup local em CSV
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
# 4. NAVEGAÇÃO E INTERFACE PRINCIPAL
# -------------------------------------------------------------
def main():
    # Mensagem flutuante persistente pós-exclusão
    if st.session_state.get("sucesso_exclusao", False):
        st.success("Registro excluído com sucesso!")
        st.session_state["sucesso_exclusao"] = False

    # Menu Lateral de Navegação
    with st.sidebar:
        st.title("☕ Menu Master Café")
        pagina = st.radio(
            "Selecione o Módulo:",
            ["📊 Dashboard Geral", "🗑️ Central de Exclusão de Registros"],
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

    # =========================================================
    # PÁGINA 1: DASHBOARD GERAL
    # =========================================================
    if pagina == "📊 Dashboard Geral":
        st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Painel de Monitoramento de Visitas e Manutenções</p></div>', unsafe_allow_html=True)

        df = df_raw.copy()

        with st.sidebar:
            st.subheader("🔍 Filtros de Consulta")
            hoje = date.today()
            inicio_padrao = hoje - timedelta(days=30)
            
            filtro_data = st.date_input(
                "Período das Visitas:",
                value=(inicio_padrao, hoje),
                format="DD/MM/YYYY"
            )

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
                df = df[df["dt_checkin"].notna() & (df["dt_checkin"] >= t_inicio) & (df["dt_checkin"] <= t_fim)]

            lista_abast = ["Todos"] + sorted(df["Abastecedor"].dropna().unique().tolist()) if "Abastecedor" in df.columns else ["Todos"]
            sel_abast = st.selectbox("Técnico / Abastecedor:", lista_abast)
            if sel_abast != "Todos":
                df = df[df["Abastecedor"] == sel_abast]

            if "Equipamento" in df.columns:
                lista_equip = ["Todos"] + sorted(df["Equipamento"].dropna().unique().tolist())
                sel_equip = st.selectbox("Número do Equipamento:", lista_equip)
                if sel_equip != "Todos":
                    df = df[df["Equipamento"] == sel_equip]

            st.caption(f"Registros exibidos: **{len(df)}**")

        # KPIs
        total_visitas = len(df)
        maquinas_atendidas = df["Equipamento"].nunique() if "Equipamento" in df.columns else 0
        clientes_atendidos = df["Cliente"].nunique() if "Cliente" in df.columns else 0
        tecnicos_ativos = df["Abastecedor"].nunique() if "Abastecedor" in df.columns else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="metric-card"><h3>{total_visitas}</h3><p>Total de Visitas</p></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="metric-card"><h3>{maquinas_atendidas}</h3><p>Máquinas Atendidas</p></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="metric-card"><h3>{clientes_atendidos}</h3><p>Clientes Distintos</p></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="metric-card"><h3>{tecnicos_ativos}</h3><p>Técnicos em Ação</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Gráficos
        if not df.empty:
            cg1, cg2 = st.columns(2)
            with cg1:
                st.subheader("📊 Atendimentos por Técnico")
                if "Abastecedor" in df.columns and not df["Abastecedor"].dropna().empty:
                    df_tec = df["Abastecedor"].value_counts().reset_index()
                    df_tec.columns = ["Técnico", "Atendimentos"]
                    fig_tec = px.bar(df_tec, x="Atendimentos", y="Técnico", orientation="h", color="Atendimentos", color_continuous_scale="Blues", text="Atendimentos")
                    fig_tec.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#F8FAFC", yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_tec, use_container_width=True)
            with cg2:
                st.subheader("☕ Top 10 Clientes Atendidos")
                if "Cliente" in df.columns and not df["Cliente"].dropna().empty:
                    df_cli = df["Cliente"].value_counts().head(10).reset_index()
                    df_cli.columns = ["Cliente", "Visitas"]
                    fig_cli = px.bar(df_cli, x="Visitas", y="Cliente", orientation="h", color="Visitas", color_continuous_scale="Teal", text="Visitas")
                    fig_cli.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#F8FAFC", yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_cli, use_container_width=True)

        # Tabela Geral
        st.subheader("📋 Detalhes dos Atendimentos Realizados")
        cols_tab = [c for c in ["Data Checkin", "Data Checkout", "Abastecedor", "Equipamento", "Cliente", "Produto", "Responsável"] if c in df.columns]
        st.dataframe(df[cols_tab], use_container_width=True)

    # =========================================================
    # PÁGINA 2: CENTRAL DE EXCLUSÃO DE REGISTROS
    # =========================================================
    elif pagina == "🗑️ Central de Exclusão de Registros":
        st.markdown('<div class="main-header"><h2>Master Café ☕</h2><p>Central de Exclusão de Registros de Visita</p></div>', unsafe_allow_html=True)

        st.info("ℹ️ Selecione o registro abaixo para auditar os detalhes, fotos e realizar a exclusão direta na planilha Google.")

        df_del = df_raw.copy()

        # Busca rápida
        busca = st.text_input("🔍 Filtrar lista por Equipamento, Cliente ou Técnico:", placeholder="Ex: 6509, Thiago, Senac...").strip().lower()
        if busca:
            df_del = df_del[
                df_del["Equipamento"].astype(str).str.lower().str.contains(busca, na=False) |
                df_del["Cliente"].astype(str).str.lower().str.contains(busca, na=False) |
                df_del["Abastecedor"].astype(str).str.lower().str.contains(busca, na=False) |
                df_del["Data Checkin"].astype(str).str.lower().str.contains(busca, na=False)
            ]

        st.markdown(f"**Registros carregados:** `{len(df_del)}`")

        colunas_exibicao = [c for c in ["Linha_Planilha", "Data Checkin", "Equipamento", "Cliente", "Abastecedor", "Produto", "Responsável"] if c in df_del.columns]
        st.dataframe(df_del[colunas_exibicao], use_container_width=True)

        st.markdown("---")
        st.subheader("Confirmar Exclusão de um Registro")

        if not df_del.empty:
            df_del_reset = df_del.reset_index(drop=True)
            opcoes_del = []
            for idx, r in df_del_reset.iterrows():
                linha_plan = r.get("Linha_Planilha", idx + 2)
                d_ch = r.get("Data Checkin", "")
                eq = r.get("Equipamento", "")
                cli = r.get("Cliente", "")
                ab = r.get("Abastecedor", "")
                opcoes_del.append(f"Linha {linha_plan} | Eq: {eq} | {d_ch} | {cli} ({ab})")

            item_selecionado = st.selectbox("Selecione o registro para exclusão:", opcoes_del)
            idx_escolhido = opcoes_del.index(item_selecionado)
            registro_alvo = df_del_reset.iloc[idx_escolhido]

            # Inspecionar fotos
            with st.expander("📷 Conferir Fotos e Assinatura deste Registro"):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    st.caption("📷 **Foto Abastecida**")
                    u_ab = str(registro_alvo.get("Foto Abastecida", "")).strip()
                    if u_ab.startswith("http"):
                        st.image(u_ab, use_container_width=True)
                    else:
                        st.write("Sem imagem.")
                with col_f2:
                    st.caption("✨ **Foto Limpa**")
                    u_li = str(registro_alvo.get("Foto Limpa", "")).strip()
                    if u_li.startswith("http"):
                        st.image(u_li, use_container_width=True)
                    else:
                        st.write("Sem imagem.")
                with col_f3:
                    st.caption("✍️ **Assinatura**")
                    u_as = str(registro_alvo.get("Assinatura", "")).strip()
                    if u_as.startswith("http"):
                        st.image(u_as, use_container_width=True)
                    else:
                        st.write("Sem imagem.")

            st.markdown(f"""
                <div class="danger-box">
                    <b>Confirmação de Exclusão Permanente:</b><br>
                    • <b>Linha da Planilha:</b> {registro_alvo.get('Linha_Planilha')}<br>
                    • <b>Cliente:</b> {registro_alvo.get('Cliente')}<br>
                    • <b>Equipamento:</b> {registro_alvo.get('Equipamento')} | <b>Check-in:</b> {registro_alvo.get('Data Checkin')}
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
                    time.sleep(1.0)
                    st.rerun()
                else:
                    st.error("Não foi possível excluir o registro. Verifique a implantação do Apps Script.")
        else:
            st.warning("Nenhum registro encontrado com o filtro aplicado.")

if __name__ == "__main__":
    main()