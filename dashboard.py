"""
Meta Ads Dashboard — Streamlit
Relatório interativo com chat IA (Claude) para análise de campanhas.
"""
import json, os, datetime
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from report_generator import fetch_report, load_report

# ─── Configuração da página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Meta Ads Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp { background: #080c14; color: #e2e8f0; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0d1220 0%, #111827 100%);
  border-right: 1px solid #1e293b;
}

/* ── KPI Card ── */
.kpi-card {
  background: linear-gradient(135deg, #111827 0%, #1a2236 100%);
  border: 1px solid #1e293b;
  border-radius: 16px;
  padding: 18px 16px 14px;
  text-align: center;
  position: relative;
  overflow: hidden;
  transition: all .25s ease;
  margin-bottom: 12px;
}
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}
.kpi-card.blue::before   { background: linear-gradient(90deg,#3b82f6,#60a5fa); }
.kpi-card.purple::before { background: linear-gradient(90deg,#8b5cf6,#a78bfa); }
.kpi-card.green::before  { background: linear-gradient(90deg,#10b981,#34d399); }
.kpi-card.orange::before { background: linear-gradient(90deg,#f59e0b,#fbbf24); }
.kpi-card.pink::before   { background: linear-gradient(90deg,#ec4899,#f472b6); }
.kpi-card.teal::before   { background: linear-gradient(90deg,#14b8a6,#2dd4bf); }
.kpi-card.red::before    { background: linear-gradient(90deg,#ef4444,#f87171); }
.kpi-card.indigo::before { background: linear-gradient(90deg,#6366f1,#818cf8); }

.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.4);
  border-color: #334155;
}
.kpi-icon  { font-size: 22px; margin-bottom: 6px; display: block; }
.kpi-label {
  font-size: 10px; color: #64748b; letter-spacing: 1.2px;
  text-transform: uppercase; margin-bottom: 8px; font-weight: 600;
}
.kpi-value { font-size: 24px; font-weight: 700; color: #f1f5f9; line-height: 1.1; }
.kpi-sub   { font-size: 11px; color: #475569; margin-top: 6px; }

/* ── Section Title ── */
.section-title {
  font-size: 16px; font-weight: 700; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 2px;
  margin: 32px 0 16px; padding-bottom: 8px;
  border-bottom: 1px solid #1e293b;
}

/* ── Status Badge ── */
.badge {
  display: inline-block;
  padding: 2px 10px; border-radius: 20px;
  font-size: 11px; font-weight: 600;
}
.badge-green  { background: #064e3b; color: #34d399; }
.badge-yellow { background: #451a03; color: #fbbf24; }
.badge-red    { background: #450a0a; color: #f87171; }
.badge-gray   { background: #1e293b; color: #94a3b8; }

/* ── Alert Insight ── */
.insight-card {
  border-radius: 10px; padding: 12px 16px; margin: 6px 0;
  border-left: 4px solid; font-size: 13px; line-height: 1.6;
}
.insight-green  { background: #022c22; border-color: #10b981; }
.insight-red    { background: #1c0a0a; border-color: #ef4444; }
.insight-yellow { background: #1c1505; border-color: #f59e0b; }

/* ── Chat ── */
.chat-user {
  background: #1e3a5f; border-radius: 16px 16px 4px 16px;
  padding: 10px 16px; margin: 8px 0 8px auto; max-width: 78%;
  color: #e2e8f0; font-size: 14px; width: fit-content;
}
.chat-ai {
  background: #111827; border: 1px solid #1e293b;
  border-radius: 16px 16px 16px 4px;
  padding: 14px 18px; margin: 8px 0; max-width: 88%;
  color: #cbd5e1; font-size: 14px; line-height: 1.7;
}
.chat-ai-header {
  font-size: 10px; color: #6366f1; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px;
}

/* ── Botões ── */
.stButton > button {
  background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
  color: white !important; border: none !important;
  border-radius: 10px !important; font-weight: 600 !important;
  transition: all .2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: transparent; gap: 4px; }
.stTabs [data-baseweb="tab"] {
  background: #111827; border-radius: 8px; color: #64748b;
  font-size: 13px; font-weight: 600; padding: 8px 16px;
}
.stTabs [aria-selected="true"] {
  background: #1e3a5f !important; color: #60a5fa !important;
}

/* ── Header conta ── */
.conta-header {
  background: linear-gradient(135deg, #111827, #1a2236);
  border: 1px solid #1e293b; border-radius: 16px;
  padding: 20px 28px; margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)

# ─── Helpers ────────────────────────────────────────────────────────────────
BRL = lambda v: f"R$ {v:,.2f}"
NUM = lambda v: f"{int(v):,}"
PCT = lambda v: f"{v:.1f}%"

PRESETS = {
    "Hoje":           "today",
    "Ontem":          "yesterday",
    "Últimos 7 dias": "last_7d",
    "Últimos 14 dias":"last_14d",
    "Últimos 30 dias":"last_30d",
    "Este mês":       "this_month",
    "Mês passado":    "last_month",
    "Todo o período": "maximum",
}

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8"),
    margin=dict(t=40, b=40, l=20, r=20),
)


def kpi(icon, label, value, color="blue", sub=""):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card {color}">
      <span class="kpi-icon">{icon}</span>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {sub_html}
    </div>"""


def roas_badge(v):
    if v >= 3:   return '<span class="badge badge-green">Ótimo</span>'
    if v >= 1:   return '<span class="badge badge-yellow">Regular</span>'
    return '<span class="badge badge-red">Negativo</span>'


def build_context(report, idx):
    if not report or not report.get("contas"):
        return "Sem dados."
    c = report["contas"][idx]
    t = c["totais"]
    lines = [
        f"Conta: {c['nome']}",
        f"Período: {report.get('date_preset','?')}",
        f"Alcance: {NUM(t.get('alcance',0))}",
        f"Impressoes: {NUM(t.get('impressoes',0))}",
        f"Cliques no link: {NUM(t.get('cliques_link',0))}",
        f"Visitas Instagram: {NUM(t.get('visitas_instagram',0))}",
        f"Conversas iniciadas: {NUM(t.get('conv_mensagens',0))}",
        f"Custo por mensagem: {BRL(t.get('custo_por_mensagem',0))}",
        f"Compras: {NUM(t.get('compras',0))}",
        f"Custo por compra: {BRL(t.get('custo_por_compra',0))}",
        f"Valor de conversao: {BRL(t.get('receita',0))}",
        f"Valor investido: {BRL(t.get('gasto',0))}",
        f"ROAS: {t.get('roas',0):.2f}x",
        "", "Top campanhas:",
    ]
    for cp in sorted(c.get("campanhas",[]), key=lambda x: x.get("gasto",0), reverse=True)[:8]:
        lines.append(
            f"  [{cp.get('status','')}] {cp.get('campaign_name','')} | "
            f"Gasto={BRL(cp['gasto'])} Compras={cp['compras']} ROAS={cp['roas']:.2f}x "
            f"Freq={cp['frequencia']:.1f} CPP={BRL(cp['custo_por_compra'])}"
        )
    return "\n".join(lines)


# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:12px 0 4px'>
      <span style='font-size:32px'>📊</span><br>
      <span style='font-size:16px;font-weight:700;color:#f1f5f9'>Meta Ads</span><br>
      <span style='font-size:12px;color:#475569'>Dashboard</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    preset_label = st.selectbox("📅 Período", list(PRESETS.keys()), index=2)
    date_preset  = PRESETS[preset_label]

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Atualizar"):
            with st.spinner("Buscando..."):
                st.session_state["report"] = fetch_report(date_preset)
            st.success("Atualizado!")
    with c2:
        if st.button("📋 Cache"):
            st.session_state["report"] = load_report()
            st.success("Carregado!")

    st.markdown("---")
    api_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    if api_ok:
        st.markdown("✅ **Chat IA:** Ativo")
    else:
        st.error("Chat IA inativo")

    st.markdown("---")
    st.caption(f"🕒 {datetime.datetime.now():%d/%m/%Y %H:%M}")


# ─── Carregar dados ──────────────────────────────────────────────────────────
if "report" not in st.session_state:
    cached = load_report()
    if cached:
        st.session_state["report"] = cached
    else:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px'>
          <span style='font-size:48px'>📡</span>
          <h3 style='color:#64748b;margin-top:16px'>Nenhum relatório carregado</h3>
          <p style='color:#475569'>Clique em <strong>Atualizar</strong> na barra lateral</p>
        </div>""", unsafe_allow_html=True)
        st.stop()

report = st.session_state["report"]

if not report or not report.get("contas"):
    st.warning("Nenhuma conta com dados.")
    st.stop()

# ─── Seletor de conta ────────────────────────────────────────────────────────
contas_nomes = [c["nome"] for c in report["contas"]]

col_sel, col_info = st.columns([3, 2])
with col_sel:
    conta_sel = st.selectbox("🏢 Conta de Anúncio", contas_nomes, label_visibility="collapsed")

conta_idx = contas_nomes.index(conta_sel)
conta     = report["contas"][conta_idx]
totais    = conta["totais"]
campanhas = conta.get("campanhas", [])
conjuntos = conta.get("conjuntos", [])

# ─── Header ──────────────────────────────────────────────────────────────────
gerado = report.get("gerado_em", "")[:16].replace("T", " ")
st.markdown(f"""
<div class="conta-header">
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px'>
    <div>
      <div style='font-size:22px;font-weight:700;color:#f1f5f9'>{conta_sel}</div>
      <div style='font-size:13px;color:#64748b;margin-top:4px'>
        📅 {preset_label} &nbsp;·&nbsp; 🕒 Atualizado em {gerado}
      </div>
    </div>
    <div style='display:flex;gap:16px;flex-wrap:wrap'>
      <div style='text-align:center'>
        <div style='font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>ROAS</div>
        <div style='font-size:26px;font-weight:700;color:{"#10b981" if totais["roas"]>=3 else ("#f59e0b" if totais["roas"]>=1 else "#ef4444")}'>{totais["roas"]:.2f}x</div>
      </div>
      <div style='text-align:center'>
        <div style='font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>Investido</div>
        <div style='font-size:26px;font-weight:700;color:#60a5fa'>{BRL(totais["gasto"])}</div>
      </div>
      <div style='text-align:center'>
        <div style='font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>Receita</div>
        <div style='font-size:26px;font-weight:700;color:#34d399'>{BRL(totais["receita"])}</div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── KPIs — 11 métricas ──────────────────────────────────────────────────────
st.markdown('<div class="section-title">Métricas Principais</div>', unsafe_allow_html=True)

# Linha 1 — Alcance e topo do funil
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(kpi("👥", "Alcance", NUM(totais.get("alcance",0)), "blue"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi("👁", "Impressões", NUM(totais.get("impressoes",0)), "purple"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi("🖱", "Cliques no Link", NUM(totais.get("cliques_link",0)), "teal"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi("📸", "Visitas Instagram", NUM(totais.get("visitas_instagram",0)), "pink"), unsafe_allow_html=True)

# Linha 2 — Mensagens e Compras
k5, k6, k7, k8 = st.columns(4)
with k5:
    st.markdown(kpi("💬", "Conv. por Mensagem", NUM(totais.get("conv_mensagens",0)), "indigo"), unsafe_allow_html=True)
with k6:
    sub_msg = f"por conversa" if totais.get("custo_por_mensagem",0) > 0 else ""
    st.markdown(kpi("💸", "Custo por Mensagem", BRL(totais.get("custo_por_mensagem",0)), "orange", sub_msg), unsafe_allow_html=True)
with k7:
    st.markdown(kpi("🛒", "Compras Realizadas", NUM(totais.get("compras",0)), "green"), unsafe_allow_html=True)
with k8:
    cpp = totais.get("custo_por_compra",0)
    cpp_sub = "✅ Ótimo" if 0 < cpp < 50 else ("⚠️ Alto" if cpp >= 150 else "")
    st.markdown(kpi("💲", "Custo por Compra", BRL(cpp), "red", cpp_sub), unsafe_allow_html=True)

# Linha 3 — Financeiro
k9, k10, k11, _ = st.columns(4)
with k9:
    st.markdown(kpi("💰", "Valor de Conversão", BRL(totais.get("receita",0)), "green"), unsafe_allow_html=True)
with k10:
    st.markdown(kpi("📤", "Valor Investido", BRL(totais.get("gasto",0)), "blue"), unsafe_allow_html=True)
with k11:
    roas_v = totais.get("roas",0)
    roas_sub = "🟢 Ótimo" if roas_v>=3 else ("🟡 Regular" if roas_v>=1 else "🔴 Negativo")
    st.markdown(kpi("📈", "Retorno (ROAS)", f"{roas_v:.2f}x", "purple", roas_sub), unsafe_allow_html=True)


# ─── Gráficos ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Análise de Campanhas</div>', unsafe_allow_html=True)

if campanhas:
    df = pd.DataFrame(campanhas)

    # garante colunas que podem faltar em caches antigos
    for col in ["visitas_instagram","custo_por_mensagem"]:
        if col not in df.columns:
            df[col] = 0

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💸 Gasto vs Receita",
        "📊 Métricas",
        "🔁 ROAS",
        "🌀 Funil",
        "📋 Tabela",
    ])

    # ── Tab 1: Gasto vs Receita ──────────────────────────────────────────────
    with tab1:
        df_s = df.sort_values("gasto", ascending=False).head(12)
        fig = go.Figure()
        fig.add_bar(name="💸 Gasto (R$)",   x=df_s["campaign_name"], y=df_s["gasto"],
                    marker_color="#3b82f6", marker_line_width=0)
        fig.add_bar(name="💰 Receita (R$)", x=df_s["campaign_name"], y=df_s["receita"],
                    marker_color="#10b981", marker_line_width=0)
        fig.update_layout(**PLOTLY_LAYOUT, barmode="group", height=400,
                          legend=dict(orientation="h", y=1.08, x=0),
                          xaxis=dict(tickangle=-30, tickfont=dict(size=11)),
                          yaxis=dict(tickprefix="R$ "))
        st.plotly_chart(fig, use_container_width=True)

        # Mini tabela resumo
        df_mini = df_s[["campaign_name","gasto","receita","roas","compras"]].copy()
        df_mini["roas_fmt"]    = df_mini["roas"].apply(lambda v: f"{v:.2f}x")
        df_mini["gasto_fmt"]   = df_mini["gasto"].apply(BRL)
        df_mini["receita_fmt"] = df_mini["receita"].apply(BRL)
        df_mini.rename(columns={"campaign_name":"Campanha","gasto_fmt":"Gasto",
                                  "receita_fmt":"Receita","roas_fmt":"ROAS","compras":"Compras"}, inplace=True)
        st.dataframe(df_mini[["Campanha","Gasto","Receita","ROAS","Compras"]],
                     use_container_width=True, hide_index=True)

    # ── Tab 2: Métricas ──────────────────────────────────────────────────────
    with tab2:
        metric_opts = {
            "Alcance":              "alcance",
            "Impressões":           "impressoes",
            "Cliques no Link":      "cliques_link",
            "Visitas Instagram":    "visitas_instagram",
            "Conv. por Mensagem":   "conv_mensagens",
            "Custo por Mensagem":   "custo_por_mensagem",
            "Compras":              "compras",
            "Custo por Compra":     "custo_por_compra",
            "ROAS":                 "roas",
            "Frequência":           "frequencia",
            "CPC":                  "cpc",
            "CPM":                  "cpm",
        }
        col_m1, col_m2 = st.columns([2,1])
        with col_m1:
            m_label = st.selectbox("Métrica", list(metric_opts.keys()))
        with col_m2:
            top_n = st.slider("Top N campanhas", 5, 20, 10)

        m_col = metric_opts[m_label]
        df_m  = df[df[m_col] > 0].sort_values(m_col, ascending=False).head(top_n)

        is_money = m_col in ["custo_por_compra","custo_por_mensagem","cpc","cpm"]
        tickpfx  = "R$ " if is_money else ""

        fig2 = px.bar(df_m, x="campaign_name", y=m_col,
                      color=m_col, color_continuous_scale="Blues",
                      template="plotly_dark",
                      labels={"campaign_name":"Campanha", m_col: m_label})
        fig2.update_layout(**PLOTLY_LAYOUT, height=400,
                           xaxis=dict(tickangle=-30),
                           yaxis=dict(tickprefix=tickpfx),
                           showlegend=False,
                           coloraxis_showscale=False)
        fig2.update_traces(marker_line_width=0)
        st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 3: ROAS ──────────────────────────────────────────────────────────
    with tab3:
        df_r = df[(df["roas"] > 0) & (df["gasto"] > 0)].copy()
        if df_r.empty:
            st.info("Sem dados de ROAS para exibir.")
        else:
            fig3 = px.scatter(
                df_r, x="gasto", y="roas",
                size="compras" if df_r["compras"].max() > 0 else None,
                color="frequencia",
                hover_name="campaign_name",
                hover_data={"gasto":True,"receita":True,"compras":True,"frequencia":True},
                color_continuous_scale="RdYlGn_r",
                labels={"gasto":"Gasto (R$)","roas":"ROAS","frequencia":"Frequência","compras":"Compras"},
                template="plotly_dark",
            )
            fig3.add_hline(y=1.0, line_dash="dash", line_color="#ef4444",
                           annotation_text="Break-even 1x", annotation_font_color="#ef4444")
            fig3.add_hline(y=3.0, line_dash="dash", line_color="#10b981",
                           annotation_text="ROAS ideal 3x", annotation_font_color="#10b981")
            fig3.update_layout(**PLOTLY_LAYOUT, height=440,
                               xaxis=dict(tickprefix="R$ "))
            st.plotly_chart(fig3, use_container_width=True)

            # distribuição pie
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                df_pie = df[df["gasto"] > 0].nlargest(8,"gasto")
                fig_pie = px.pie(df_pie, values="gasto", names="campaign_name",
                                 hole=0.5, template="plotly_dark",
                                 color_discrete_sequence=px.colors.sequential.Blues_r,
                                 title="Distribuição de Gasto")
                fig_pie.update_traces(textposition="inside", textinfo="percent")
                fig_pie.update_layout(**PLOTLY_LAYOUT, height=320,
                                      legend=dict(font=dict(size=10)))
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_p2:
                df_pie2 = df[df["receita"] > 0].nlargest(8,"receita")
                fig_pie2 = px.pie(df_pie2, values="receita", names="campaign_name",
                                  hole=0.5, template="plotly_dark",
                                  color_discrete_sequence=px.colors.sequential.Greens_r,
                                  title="Distribuição de Receita")
                fig_pie2.update_traces(textposition="inside", textinfo="percent")
                fig_pie2.update_layout(**PLOTLY_LAYOUT, height=320,
                                       legend=dict(font=dict(size=10)))
                st.plotly_chart(fig_pie2, use_container_width=True)

    # ── Tab 4: Funil ─────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### 🌀 Funil de Conversão")
        t = totais
        funil_labels  = ["Alcance","Impressões","Cliques no Link","Visitas Instagram",
                         "Conv. Mensagem","Compras"]
        funil_valores = [
            t.get("alcance",0),
            t.get("impressoes",0),
            t.get("cliques_link",0),
            t.get("visitas_instagram",0),
            t.get("conv_mensagens",0),
            t.get("compras",0),
        ]
        fig_funil = go.Figure(go.Funnel(
            y=funil_labels,
            x=funil_valores,
            textinfo="value+percent initial",
            marker=dict(
                color=["#3b82f6","#6366f1","#8b5cf6","#ec4899","#f59e0b","#10b981"],
                line=dict(width=0),
            ),
            connector=dict(line=dict(color="#1e293b", width=2)),
        ))
        fig_funil.update_layout(**PLOTLY_LAYOUT, height=400)
        st.plotly_chart(fig_funil, use_container_width=True)

        # Taxas de conversão
        st.markdown("#### Taxas de Conversão")
        col_tx = st.columns(4)
        total_alcance = t.get("alcance",1) or 1
        total_cliques = t.get("cliques_link",1) or 1
        total_conv    = t.get("conv_mensagens",1) or 1

        taxa_clique  = (t.get("cliques_link",0) / total_alcance * 100) if total_alcance else 0
        taxa_msg     = (t.get("conv_mensagens",0) / total_cliques * 100) if total_cliques else 0
        taxa_compra  = (t.get("compras",0) / total_cliques * 100) if total_cliques else 0
        taxa_msg_cmp = (t.get("compras",0) / (t.get("conv_mensagens",1) or 1) * 100)

        with col_tx[0]:
            st.metric("CTR (Clique/Alcance)", f"{taxa_clique:.2f}%")
        with col_tx[1]:
            st.metric("Msg/Clique", f"{taxa_msg:.2f}%")
        with col_tx[2]:
            st.metric("Compra/Clique", f"{taxa_compra:.2f}%")
        with col_tx[3]:
            st.metric("Compra/Mensagem", f"{taxa_msg_cmp:.2f}%")

    # ── Tab 5: Tabela Completa ───────────────────────────────────────────────
    with tab5:
        col_f1, col_f2 = st.columns([2,1])
        with col_f1:
            busca = st.text_input("🔍 Filtrar campanha", placeholder="Digite para filtrar...")
        with col_f2:
            sort_col = st.selectbox("Ordenar por", ["Gasto","Receita","ROAS","Compras","Alcance"], index=0)

        sort_map = {"Gasto":"gasto","Receita":"receita","ROAS":"roas",
                    "Compras":"compras","Alcance":"alcance"}

        df_tbl = df.copy()
        if busca:
            df_tbl = df_tbl[df_tbl["campaign_name"].str.contains(busca, case=False, na=False)]
        df_tbl = df_tbl.sort_values(sort_map[sort_col], ascending=False)

        cols_show = {
            "campaign_name":     "Campanha",
            "status":            "Status",
            "alcance":           "Alcance",
            "impressoes":        "Impressões",
            "frequencia":        "Freq.",
            "cliques_link":      "Cliques",
            "visitas_instagram":  "Visitas IG",
            "conv_mensagens":    "Conv.Msg",
            "custo_por_mensagem":"$/Msg",
            "compras":           "Compras",
            "custo_por_compra":  "$/Compra",
            "receita":           "Receita",
            "gasto":             "Gasto",
            "roas":              "ROAS",
        }
        existing = [c for c in cols_show if c in df_tbl.columns]
        df_show  = df_tbl[existing].rename(columns=cols_show)

        def highlight_row(row):
            styles = [""] * len(row)
            cols_list = list(df_show.columns)
            if "ROAS" in cols_list:
                v = row.get("ROAS", 0)
                i = cols_list.index("ROAS")
                styles[i] = f"color:{'#10b981' if v>=3 else ('#f59e0b' if v>=1 else '#ef4444')};font-weight:700"
            if "Freq." in cols_list:
                v = row.get("Freq.", 0)
                i = cols_list.index("Freq.")
                styles[i] = f"color:{'#ef4444' if v>4 else ('#f59e0b' if v>2.5 else '#10b981')}"
            return styles

        fmt = {}
        for col in ["Gasto","Receita","$/Compra","$/Msg"]:
            if col in df_show.columns:
                fmt[col] = "R$ {:,.2f}"
        for col in ["Alcance","Impressões","Cliques","Visitas IG","Conv.Msg","Compras"]:
            if col in df_show.columns:
                fmt[col] = "{:,.0f}"
        if "ROAS" in df_show.columns:   fmt["ROAS"]  = "{:.2f}x"
        if "Freq." in df_show.columns:  fmt["Freq."] = "{:.2f}"

        st.dataframe(
            df_show.style.apply(highlight_row, axis=1).format(fmt, na_rep="-"),
            use_container_width=True, height=460, hide_index=True,
        )
        st.caption(f"Total: {len(df_show)} campanhas")

# ─── Conjuntos de Anúncios ───────────────────────────────────────────────────
if conjuntos:
    st.markdown('<div class="section-title">Conjuntos de Anúncios</div>', unsafe_allow_html=True)
    df_as = pd.DataFrame(conjuntos).sort_values("gasto", ascending=False)

    col_as1, col_as2 = st.columns([3,1])
    with col_as2:
        top_as = st.slider("Top N conjuntos", 5, 20, 12)

    fig_as = px.bar(
        df_as.head(top_as), x="gasto", y="adset_name",
        color="roas", color_continuous_scale="RdYlGn",
        orientation="h",
        labels={"gasto":"Gasto (R$)","adset_name":"Conjunto","roas":"ROAS"},
        template="plotly_dark",
    )
    fig_as.update_layout(**PLOTLY_LAYOUT, height=max(300, top_as*34),
                         xaxis=dict(tickprefix="R$ "),
                         yaxis=dict(tickfont=dict(size=11)))
    fig_as.update_traces(marker_line_width=0)
    st.plotly_chart(fig_as, use_container_width=True)


# ─── Insights Automáticos ────────────────────────────────────────────────────
st.markdown('<div class="section-title">Insights Automáticos</div>', unsafe_allow_html=True)

insights = []
for c in campanhas:
    if c.get("gasto", 0) == 0:
        continue
    nome = c.get("campaign_name", "—")
    freq = c.get("frequencia", 0)
    roas = c.get("roas", 0)
    cpp  = c.get("custo_por_compra", 0)
    cpc  = c.get("cpc", 0)

    if freq > 4.0:
        insights.append(("red",    "🔴 Saturação de Público", nome,
                          f"Frequência {freq:.1f}x — público saturado. Renovar criativos ou expandir audiência urgentemente."))
    elif freq > 2.5:
        insights.append(("yellow", "🟡 Frequência Moderada", nome,
                          f"Frequência {freq:.1f}x — monitorar de perto nos próximos dias."))

    if c.get("compras",0) > 0 and roas >= 5:
        insights.append(("green",  "🚀 Alta Performance", nome,
                          f"ROAS {roas:.2f}x — excelente resultado! Considere escalar o orçamento."))
    elif c.get("compras",0) > 0 and roas >= 3:
        insights.append(("green",  "🟢 Boa Performance", nome,
                          f"ROAS {roas:.2f}x — campanha lucrativa. Boa oportunidade para escalar."))
    elif c.get("compras",0) > 0 and roas < 1:
        insights.append(("red",    "🔴 ROAS Negativo", nome,
                          f"ROAS {roas:.2f}x — campanha gerando prejuízo. Pausar e revisar estratégia."))

    if c.get("cliques_link",0) > 200 and c.get("compras",0) == 0:
        insights.append(("yellow", "🟡 Cliques sem Conversão", nome,
                          f"{c['cliques_link']} cliques sem compras — verificar pixel, página de destino e oferta."))

    if cpp > 300 and c.get("compras",0) > 0:
        insights.append(("red",    "🔴 Custo por Compra Alto", nome,
                          f"CPP R$ {cpp:.2f} — muito acima do ideal. Revisar segmentação e criativos."))

    if cpc > 5.0:
        insights.append(("yellow", "🟡 CPC Elevado", nome,
                          f"CPC R$ {cpc:.2f} — testar novos criativos e públicos mais qualificados."))

col_ins_a, col_ins_b = st.columns(2)
if not insights:
    st.success("✅ Todas as métricas estão dentro dos parâmetros esperados.")
else:
    for i, (tipo, titulo, nome, msg) in enumerate(insights):
        cls = f"insight-{tipo}"
        target = col_ins_a if i % 2 == 0 else col_ins_b
        with target:
            st.markdown(f"""
            <div class="insight-card {cls}">
              <strong>{titulo}</strong><br>
              <span style="font-size:12px;color:#94a3b8">{nome}</span><br>
              <span style="color:#cbd5e1">{msg}</span>
            </div>""", unsafe_allow_html=True)


# ─── Chat com IA ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">💬 Assistente IA</div>', unsafe_allow_html=True)

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    st.warning("Configure a ANTHROPIC_API_KEY para ativar o chat.")
else:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    ctx = build_context(report, conta_idx)

    # Histórico
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-ai">
              <div class="chat-ai-header">🤖 Assistente Meta Ads</div>
              {msg["content"]}
            </div>""", unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        col_inp, col_btn = st.columns([5,1])
        with col_inp:
            user_input = st.text_input(
                "Mensagem", label_visibility="collapsed",
                placeholder="Ex: Por que o ROAS está baixo? Como reduzir o custo por compra?",
            )
        with col_btn:
            submitted = st.form_submit_button("Enviar →")

    if submitted and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        sys_prompt = f"""Você é um especialista sênior em tráfego pago e Meta Ads com mais de 10 anos de experiência.
Analise os dados do relatório abaixo e responda de forma clara, objetiva e prática em português do Brasil.
Sempre que recomendar uma ação, seja específico sobre o que fazer. Use emojis para destacar pontos importantes.
Formate bem a resposta usando markdown quando necessário.

DADOS DO RELATÓRIO:
{ctx}"""

        messages = [{"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history]
        try:
            with st.spinner("Analisando..."):
                resp = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    system=sys_prompt,
                    messages=messages,
                )
            ai_reply = resp.content[0].text
        except Exception as e:
            ai_reply = f"Erro ao chamar a API: {e}"

        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
        st.rerun()

    col_chat_btn = st.columns([1,4])
    with col_chat_btn[0]:
        if st.button("🗑 Limpar conversa"):
            st.session_state.chat_history = []
            st.rerun()


# ─── Rodapé ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='text-align:center;color:#1e293b;font-size:12px'>"
    f"Meta Ads Dashboard · Meta Graph API v21.0 · "
    f"Última atualização: {report.get('gerado_em','')[:16].replace('T',' ')}"
    f"</p>",
    unsafe_allow_html=True,
)
