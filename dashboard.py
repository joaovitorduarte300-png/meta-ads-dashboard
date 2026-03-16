"""
Meta Ads Dashboard — Streamlit
Relatório interativo com chat IA (Claude) para análise de campanhas.
"""
import json, os, datetime, base64, threading
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

def _load_logo():
    for name in ["logo.png", "logo.png.png"]:
        path = os.path.join(os.path.dirname(__file__), name)
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            continue
    return None

_LOGO_B64 = _load_logo()

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from report_generator import fetch_report, load_report

st.set_page_config(
    page_title="Meta Ads Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
.stApp { background: #080c14; color: #e2e8f0; }
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg,#0d1220 0%,#111827 100%);
  border-right: 1px solid #1e293b;
}
.kpi-card {
  background: linear-gradient(135deg,#111827 0%,#1a2236 100%);
  border: 1px solid #1e293b; border-radius: 16px;
  padding: 18px 16px 14px; text-align: center;
  position: relative; overflow: hidden;
  transition: all .25s ease; margin-bottom: 12px;
}
.kpi-card::before { content:''; position:absolute; top:0;left:0;right:0; height:3px; }
.kpi-card.blue::before   { background:linear-gradient(90deg,#3b82f6,#60a5fa); }
.kpi-card.purple::before { background:linear-gradient(90deg,#8b5cf6,#a78bfa); }
.kpi-card.green::before  { background:linear-gradient(90deg,#10b981,#34d399); }
.kpi-card.orange::before { background:linear-gradient(90deg,#f59e0b,#fbbf24); }
.kpi-card.pink::before   { background:linear-gradient(90deg,#ec4899,#f472b6); }
.kpi-card.teal::before   { background:linear-gradient(90deg,#14b8a6,#2dd4bf); }
.kpi-card.red::before    { background:linear-gradient(90deg,#ef4444,#f87171); }
.kpi-card.indigo::before { background:linear-gradient(90deg,#6366f1,#818cf8); }
.kpi-card:hover { transform:translateY(-4px); box-shadow:0 12px 32px rgba(0,0,0,0.4); border-color:#334155; }
.kpi-icon  { font-size:22px; margin-bottom:6px; display:block; }
.kpi-label { font-size:10px; color:#64748b; letter-spacing:1.2px; text-transform:uppercase; margin-bottom:8px; font-weight:600; }
.kpi-value { font-size:24px; font-weight:700; color:#f1f5f9; line-height:1.1; }
.kpi-sub   { font-size:11px; color:#475569; margin-top:6px; }
.section-title {
  font-size:14px; font-weight:700; color:#64748b;
  text-transform:uppercase; letter-spacing:2px;
  margin:32px 0 16px; padding-bottom:8px;
  border-bottom:1px solid #1e293b;
}
.creative-card {
  background:#111827; border:1px solid #1e293b; border-radius:14px;
  overflow:hidden; transition:all .2s; margin-bottom:16px;
}
.creative-card:hover { border-color:#334155; transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,0,0,0.4); }
.creative-thumb {
  width:100%; height:160px; object-fit:cover;
  background:#1a2236; display:block;
}
.creative-thumb-placeholder {
  width:100%; height:160px; background:linear-gradient(135deg,#1a2236,#0f172a);
  display:flex; align-items:center; justify-content:center;
  font-size:36px; color:#334155;
}
.creative-body { padding:12px 14px; }
.creative-name { font-size:12px; font-weight:600; color:#94a3b8; margin-bottom:10px;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.creative-metric { display:flex; justify-content:space-between; align-items:center;
  padding:4px 0; border-bottom:1px solid #1e293b; font-size:12px; }
.creative-metric:last-child { border-bottom:none; }
.cm-label { color:#64748b; }
.cm-value { font-weight:600; color:#e2e8f0; }
.cm-value.green { color:#10b981; }
.cm-value.red   { color:#ef4444; }
.cm-value.yellow{ color:#f59e0b; }
.insight-card { border-radius:10px; padding:12px 16px; margin:6px 0; border-left:4px solid; font-size:13px; line-height:1.6; }
.insight-green  { background:#022c22; border-color:#10b981; }
.insight-red    { background:#1c0a0a; border-color:#ef4444; }
.insight-yellow { background:#1c1505; border-color:#f59e0b; }
.chat-user {
  background:#1e3a5f; border-radius:16px 16px 4px 16px;
  padding:10px 16px; margin:8px 0 8px auto; max-width:78%;
  color:#e2e8f0; font-size:14px; width:fit-content;
}
.chat-ai {
  background:#111827; border:1px solid #1e293b; border-radius:16px 16px 16px 4px;
  padding:14px 18px; margin:8px 0; max-width:88%;
  color:#cbd5e1; font-size:14px; line-height:1.7;
}
.chat-ai-header { font-size:10px; color:#6366f1; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:6px; }
.stButton > button {
  background:linear-gradient(135deg,#3b82f6,#6366f1) !important;
  color:white !important; border:none !important;
  border-radius:10px !important; font-weight:600 !important;
}
.stButton > button:hover { opacity:0.88 !important; transform:translateY(-1px) !important; }
.stTabs [data-baseweb="tab-list"] { background:transparent; gap:4px; }
.stTabs [data-baseweb="tab"] { background:#111827; border-radius:8px; color:#64748b; font-size:13px; font-weight:600; padding:8px 16px; }
.stTabs [aria-selected="true"] { background:#1e3a5f !important; color:#60a5fa !important; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ────────────────────────────────────────────────────────────────
BRL = lambda v: f"R$ {v:,.2f}"
NUM = lambda v: f"{int(v):,}"

CACHE_MAX_AGE_H = 6  # horas antes de considerar o cache expirado

def _cache_is_fresh(data):
    """Retorna True se o cache foi gerado há menos de CACHE_MAX_AGE_H horas."""
    try:
        age = (datetime.datetime.now() -
               datetime.datetime.fromisoformat(data.get("gerado_em", ""))).total_seconds()
        return age < CACHE_MAX_AGE_H * 3600
    except Exception:
        return False

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

LAYOUT = dict(
    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#94a3b8"),
    margin=dict(t=40, b=40, l=20, r=20),
)


def kpi(icon, label, value, color="blue", sub=""):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""<div class="kpi-card {color}">
      <span class="kpi-icon">{icon}</span>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>{sub_html}
    </div>"""


def safe(d, key, default=0):
    """Lê chave do dict com fallback — garante compatibilidade com cache antigo."""
    v = d.get(key, default)
    return v if v is not None else default


def build_context(report, idx):
    if not report or not report.get("contas"):
        return "Sem dados."
    c = report["contas"][idx]
    t = c["totais"]
    lines = [
        f"Conta: {c['nome']}",
        f"Periodo: {report.get('date_preset','?')}",
        f"Alcance: {NUM(safe(t,'alcance'))}",
        f"Impressoes: {NUM(safe(t,'impressoes'))}",
        f"Cliques no link: {NUM(safe(t,'cliques_link'))}",
        f"Visitas Instagram: {NUM(safe(t,'visitas_instagram'))}",
        f"Conversas iniciadas: {NUM(safe(t,'conv_mensagens'))}",
        f"Custo por mensagem: {BRL(safe(t,'custo_por_mensagem'))}",
        f"Compras: {NUM(safe(t,'compras'))}",
        f"Custo por compra: {BRL(safe(t,'custo_por_compra'))}",
        f"Valor de conversao: {BRL(safe(t,'receita'))}",
        f"Valor investido: {BRL(safe(t,'gasto'))}",
        f"ROAS: {safe(t,'roas',0):.2f}x",
        "", "Top campanhas:",
    ]
    for cp in sorted(c.get("campanhas",[]), key=lambda x: x.get("gasto",0), reverse=True)[:8]:
        lines.append(
            f"  [{cp.get('status','')}] {cp.get('campaign_name','')} | "
            f"Gasto={BRL(cp['gasto'])} Compras={cp['compras']} ROAS={cp['roas']:.2f}x "
            f"Freq={cp['frequencia']:.1f} CPP={BRL(cp['custo_por_compra'])}"
        )
    criativos = c.get("criativos", [])
    if criativos:
        lines.append("")
        lines.append("Top criativos:")
        for cr in sorted(criativos, key=lambda x: x.get("gasto",0), reverse=True)[:5]:
            lines.append(
                f"  {cr.get('ad_name','')} | Gasto={BRL(cr['gasto'])} "
                f"Impressoes={NUM(cr['impressoes'])} CTR={cr.get('ctr',0):.2f}% "
                f"Compras={cr['compras']} ROAS={cr['roas']:.2f}x"
            )
    return "\n".join(lines)


# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    if _LOGO_B64:
        st.markdown(f"""
        <div style='text-align:center;padding:16px 0 8px'>
          <img src="data:image/png;base64,{_LOGO_B64}"
               style="width:150px;filter:brightness(0) invert(1);margin-bottom:6px" />
          <div style='font-size:12px;color:#475569;margin-top:4px'>Meta Ads Dashboard</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center;padding:12px 0 4px'>
          <span style='font-size:32px'>📊</span><br>
          <span style='font-size:16px;font-weight:700;color:#f1f5f9'>Meta Ads</span><br>
          <span style='font-size:12px;color:#475569'>Dashboard</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

    preset_label = st.selectbox("📅 Período", list(PRESETS.keys()), index=2)
    date_preset  = PRESETS[preset_label]

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Atualizar"):
            with st.spinner("Buscando..."):
                novo = fetch_report(date_preset)
                if novo and novo.get("contas"):
                    st.session_state[f"report_{date_preset}"] = novo
            st.success("Atualizado!")
    with c2:
        if st.button("📋 Cache"):
            cached = load_report()
            if cached and cached.get("contas"):
                st.session_state[f"report_{cached.get('date_preset', date_preset)}"] = cached
            st.success("Carregado!")

    st.markdown("---")
    if os.getenv("ANTHROPIC_API_KEY"):
        st.markdown("✅ **Chat IA:** Ativo")
    else:
        st.error("Chat IA inativo")
    st.caption(f"🕒 {datetime.datetime.now():%d/%m/%Y %H:%M}")


# ─── Pré-busca em background dos períodos mais usados ────────────────────────
_PREFETCH = ["last_14d", "last_30d", "this_month"]

def _bg_prefetch(presets):
    """Roda em thread separada — NÃO acessa st.session_state."""
    for p in presets:
        cached = load_report(p)
        if cached and cached.get("contas") and _cache_is_fresh(cached):
            continue  # cache fresco no disco, pula
        try:
            fetch_report(p)
        except Exception:
            pass

if "prefetch_started" not in st.session_state:
    st.session_state["prefetch_started"] = True
    threading.Thread(target=_bg_prefetch, args=(_PREFETCH,), daemon=True).start()


# ─── Carregar dados ──────────────────────────────────────────────────────────
report_session_key = f"report_{date_preset}"

if report_session_key not in st.session_state:
    cached = load_report(date_preset)  # tenta cache do período específico
    if cached and cached.get("contas"):
        # Usa o cache (mesmo que antigo) — mostra os dados imediatamente
        st.session_state[report_session_key] = cached
    else:
        # Sem cache para este período → busca da API
        with st.spinner(f"🔄 Carregando dados para '{preset_label}'..."):
            try:
                novo = fetch_report(date_preset)
                if novo and novo.get("contas"):
                    st.session_state[report_session_key] = novo
            except Exception:
                pass

if report_session_key not in st.session_state:
    st.markdown("""
    <div style='text-align:center;padding:60px 20px'>
      <span style='font-size:48px'>📡</span>
      <h3 style='color:#64748b;margin-top:16px'>Nenhum relatório carregado</h3>
      <p style='color:#475569'>Clique em <strong>Atualizar</strong> na barra lateral</p>
    </div>""", unsafe_allow_html=True)
    st.stop()

report = st.session_state[report_session_key]
if not report or not report.get("contas"):
    st.warning("Nenhuma conta com dados.")
    st.stop()

# ─── Seletor de conta ────────────────────────────────────────────────────────
contas_nomes = [c["nome"] for c in report["contas"]]
conta_sel    = st.selectbox("🏢 Conta", contas_nomes, label_visibility="collapsed")
conta_idx    = contas_nomes.index(conta_sel)
conta        = report["contas"][conta_idx]
totais       = conta["totais"]
campanhas    = conta.get("campanhas", [])
conjuntos    = conta.get("conjuntos", [])
criativos    = conta.get("criativos", [])

# ─── Header ──────────────────────────────────────────────────────────────────
gerado = report.get("gerado_em","")[:16].replace("T"," ")
roas_v = safe(totais,"roas")
roas_cor = "#10b981" if roas_v>=3 else ("#f59e0b" if roas_v>=1 else "#ef4444")

st.markdown(f"""
<div style='background:linear-gradient(135deg,#111827,#1a2236);border:1px solid #1e293b;
     border-radius:16px;padding:20px 28px;margin-bottom:24px'>
  <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px'>
    <div>
      <div style='font-size:22px;font-weight:700;color:#f1f5f9'>{conta_sel}</div>
      <div style='font-size:13px;color:#64748b;margin-top:4px'>📅 {preset_label} &nbsp;·&nbsp; 🕒 {gerado}</div>
    </div>
    <div style='display:flex;gap:24px;flex-wrap:wrap'>
      <div style='text-align:center'>
        <div style='font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>ROAS</div>
        <div style='font-size:28px;font-weight:700;color:{roas_cor}'>{roas_v:.2f}x</div>
      </div>
      <div style='text-align:center'>
        <div style='font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>Investido</div>
        <div style='font-size:28px;font-weight:700;color:#60a5fa'>{BRL(safe(totais,"gasto"))}</div>
      </div>
      <div style='text-align:center'>
        <div style='font-size:10px;color:#64748b;letter-spacing:1px;text-transform:uppercase'>Receita</div>
        <div style='font-size:28px;font-weight:700;color:#34d399'>{BRL(safe(totais,"receita"))}</div>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)


# ─── KPIs ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Métricas Principais</div>', unsafe_allow_html=True)

r1 = st.columns(4)
with r1[0]: st.markdown(kpi("👥","Alcance",          NUM(safe(totais,"alcance")),          "blue"),   unsafe_allow_html=True)
with r1[1]: st.markdown(kpi("👁","Impressões",        NUM(safe(totais,"impressoes")),        "purple"), unsafe_allow_html=True)
with r1[2]: st.markdown(kpi("🖱","Cliques no Link",   NUM(safe(totais,"cliques_link")),      "teal"),   unsafe_allow_html=True)
with r1[3]: st.markdown(kpi("📸","Visitas Instagram", NUM(safe(totais,"visitas_instagram")), "pink"),   unsafe_allow_html=True)

r2 = st.columns(4)
with r2[0]: st.markdown(kpi("💬","Conv. por Mensagem", NUM(safe(totais,"conv_mensagens")),                              "indigo"), unsafe_allow_html=True)
with r2[1]: st.markdown(kpi("💸","Custo por Mensagem", BRL(safe(totais,"custo_por_mensagem")),                          "orange"), unsafe_allow_html=True)
with r2[2]: st.markdown(kpi("🛒","Compras Realizadas", NUM(safe(totais,"compras")),                                     "green"),  unsafe_allow_html=True)
with r2[3]:
    cpp = safe(totais,"custo_por_compra")
    sub = "✅ Ótimo" if 0<cpp<50 else ("⚠️ Alto" if cpp>=150 else "")
    st.markdown(kpi("💲","Custo por Compra", BRL(cpp), "red", sub), unsafe_allow_html=True)

r3 = st.columns(4)
with r3[0]: st.markdown(kpi("💰","Valor de Conversão", BRL(safe(totais,"receita")), "green"),  unsafe_allow_html=True)
with r3[1]: st.markdown(kpi("📤","Valor Investido",     BRL(safe(totais,"gasto")),   "blue"),   unsafe_allow_html=True)
with r3[2]:
    sub_r = "🟢 Ótimo" if roas_v>=3 else ("🟡 Regular" if roas_v>=1 else "🔴 Negativo")
    st.markdown(kpi("📈","Retorno (ROAS)", f"{roas_v:.2f}x", "purple", sub_r), unsafe_allow_html=True)
with r3[3]: pass  # placeholder


# ─── Gráficos de Campanhas ───────────────────────────────────────────────────
st.markdown('<div class="section-title">Análise de Campanhas</div>', unsafe_allow_html=True)

if campanhas:
    df = pd.DataFrame(campanhas)
    for col in ["visitas_instagram","custo_por_mensagem","impressoes"]:
        if col not in df.columns:
            df[col] = 0

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💸 Gasto vs Receita","📊 Métricas","🔁 ROAS","🌀 Funil","📋 Tabela",
    ])

    with tab1:
        df_s = df.sort_values("gasto", ascending=False).head(12)
        fig = go.Figure()
        fig.add_bar(name="💸 Gasto",   x=df_s["campaign_name"], y=df_s["gasto"],   marker_color="#3b82f6", marker_line_width=0)
        fig.add_bar(name="💰 Receita", x=df_s["campaign_name"], y=df_s["receita"], marker_color="#10b981", marker_line_width=0)
        fig.update_layout(**LAYOUT, barmode="group", height=400,
                          legend=dict(orientation="h",y=1.08,x=0),
                          xaxis=dict(tickangle=-30,tickfont=dict(size=11)),
                          yaxis=dict(tickprefix="R$ "))
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        opts = {
            "Alcance":"alcance","Impressões":"impressoes","Cliques no Link":"cliques_link",
            "Visitas Instagram":"visitas_instagram","Conv. Mensagem":"conv_mensagens",
            "Compras":"compras","Custo por Compra":"custo_por_compra",
            "ROAS":"roas","Frequência":"frequencia","CPC":"cpc","CPM":"cpm",
        }
        c_m1, c_m2 = st.columns([2,1])
        with c_m1: m_label = st.selectbox("Métrica", list(opts.keys()))
        with c_m2: top_n   = st.slider("Top N", 5, 20, 10)
        m_col = opts[m_label]
        df_m  = df[df[m_col]>0].sort_values(m_col, ascending=False).head(top_n)
        is_money = m_col in ["custo_por_compra","custo_por_mensagem","cpc","cpm"]
        fig2 = px.bar(df_m, x="campaign_name", y=m_col, color=m_col,
                      color_continuous_scale="Blues", template="plotly_dark",
                      labels={"campaign_name":"Campanha", m_col: m_label})
        fig2.update_layout(**LAYOUT, height=400,
                           xaxis=dict(tickangle=-30),
                           yaxis=dict(tickprefix="R$ " if is_money else ""),
                           showlegend=False, coloraxis_showscale=False)
        fig2.update_traces(marker_line_width=0)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        df_r = df[(df["roas"]>0)&(df["gasto"]>0)].copy()
        if df_r.empty:
            st.info("Sem dados de ROAS.")
        else:
            fig3 = px.scatter(df_r, x="gasto", y="roas",
                              size="compras" if df_r["compras"].max()>0 else None,
                              color="frequencia", hover_name="campaign_name",
                              color_continuous_scale="RdYlGn_r", template="plotly_dark",
                              labels={"gasto":"Gasto (R$)","roas":"ROAS","frequencia":"Frequência"})
            fig3.add_hline(y=1.0, line_dash="dash", line_color="#ef4444", annotation_text="Break-even 1x")
            fig3.add_hline(y=3.0, line_dash="dash", line_color="#10b981", annotation_text="ROAS ideal 3x")
            fig3.update_layout(**LAYOUT, height=420, xaxis=dict(tickprefix="R$ "))
            st.plotly_chart(fig3, use_container_width=True)
            cp1, cp2 = st.columns(2)
            with cp1:
                df_pg = df[df["gasto"]>0].nlargest(8,"gasto")
                fp = px.pie(df_pg, values="gasto", names="campaign_name", hole=0.5,
                            template="plotly_dark", color_discrete_sequence=px.colors.sequential.Blues_r,
                            title="Distribuição de Gasto")
                fp.update_traces(textposition="inside", textinfo="percent")
                fp.update_layout(**LAYOUT, height=300)
                st.plotly_chart(fp, use_container_width=True)
            with cp2:
                df_pr = df[df["receita"]>0].nlargest(8,"receita")
                fr = px.pie(df_pr, values="receita", names="campaign_name", hole=0.5,
                            template="plotly_dark", color_discrete_sequence=px.colors.sequential.Greens_r,
                            title="Distribuição de Receita")
                fr.update_traces(textposition="inside", textinfo="percent")
                fr.update_layout(**LAYOUT, height=300)
                st.plotly_chart(fr, use_container_width=True)

    with tab4:
        t = totais
        fl = ["Alcance","Impressões","Cliques no Link","Visitas Instagram","Conv. Mensagem","Compras"]
        fv = [safe(t,"alcance"),safe(t,"impressoes"),safe(t,"cliques_link"),
              safe(t,"visitas_instagram"),safe(t,"conv_mensagens"),safe(t,"compras")]
        fig_f = go.Figure(go.Funnel(
            y=fl, x=fv, textinfo="value+percent initial",
            marker=dict(color=["#3b82f6","#6366f1","#8b5cf6","#ec4899","#f59e0b","#10b981"],
                        line=dict(width=0)),
            connector=dict(line=dict(color="#1e293b", width=2)),
        ))
        fig_f.update_layout(**LAYOUT, height=400)
        st.plotly_chart(fig_f, use_container_width=True)
        alc = safe(t,"alcance") or 1
        clk = safe(t,"cliques_link") or 1
        cmp = safe(t,"compras") or 1
        cv1,cv2,cv3,cv4 = st.columns(4)
        cv1.metric("CTR (Clique/Alcance)",  f"{safe(t,'cliques_link')/alc*100:.2f}%")
        cv2.metric("Msg/Clique",            f"{safe(t,'conv_mensagens')/clk*100:.2f}%")
        cv3.metric("Compra/Clique",         f"{safe(t,'compras')/clk*100:.2f}%")
        cv4.metric("Compra/Mensagem",       f"{safe(t,'compras')/(safe(t,'conv_mensagens') or 1)*100:.2f}%")

    with tab5:
        bf1, bf2 = st.columns([2,1])
        with bf1: busca    = st.text_input("🔍 Filtrar", placeholder="Nome da campanha...")
        with bf2: sort_col = st.selectbox("Ordenar por", ["Gasto","Receita","ROAS","Compras"], index=0)
        sort_map = {"Gasto":"gasto","Receita":"receita","ROAS":"roas","Compras":"compras"}
        df_tbl = df.copy()
        if busca:
            df_tbl = df_tbl[df_tbl["campaign_name"].str.contains(busca, case=False, na=False)]
        df_tbl = df_tbl.sort_values(sort_map[sort_col], ascending=False)
        cols_show = {
            "campaign_name":"Campanha","status":"Status",
            "alcance":"Alcance","impressoes":"Impressões","frequencia":"Freq.",
            "cliques_link":"Cliques","visitas_instagram":"Visitas IG",
            "conv_mensagens":"Conv.Msg","custo_por_mensagem":"$/Msg",
            "compras":"Compras","custo_por_compra":"$/Compra",
            "receita":"Receita","gasto":"Gasto","roas":"ROAS",
        }
        existing = [c for c in cols_show if c in df_tbl.columns]
        df_show  = df_tbl[existing].rename(columns=cols_show)
        def hl(row):
            s = [""]*len(row)
            cl = list(df_show.columns)
            if "ROAS" in cl:
                v=row.get("ROAS",0); i=cl.index("ROAS")
                s[i]=f"color:{'#10b981' if v>=3 else ('#f59e0b' if v>=1 else '#ef4444')};font-weight:700"
            if "Freq." in cl:
                v=row.get("Freq.",0); i=cl.index("Freq.")
                s[i]=f"color:{'#ef4444' if v>4 else ('#f59e0b' if v>2.5 else '#10b981')}"
            return s
        fmt={}
        for c in ["Gasto","Receita","$/Compra","$/Msg"]:
            if c in df_show.columns: fmt[c]="R$ {:,.2f}"
        for c in ["Alcance","Impressões","Cliques","Visitas IG","Conv.Msg","Compras"]:
            if c in df_show.columns: fmt[c]="{:,.0f}"
        if "ROAS"  in df_show.columns: fmt["ROAS"] ="{:.2f}x"
        if "Freq." in df_show.columns: fmt["Freq."]="{:.2f}"
        st.dataframe(df_show.style.apply(hl,axis=1).format(fmt,na_rep="-"),
                     use_container_width=True, height=460, hide_index=True)
        st.caption(f"{len(df_show)} campanhas")


# ─── Conjuntos de Anúncios ───────────────────────────────────────────────────
if conjuntos:
    st.markdown('<div class="section-title">Conjuntos de Anúncios</div>', unsafe_allow_html=True)
    df_as = pd.DataFrame(conjuntos).sort_values("gasto", ascending=False)
    _, cas2 = st.columns([3,1])
    with cas2: top_as = st.slider("Top N conjuntos", 5, 20, 12)
    fig_as = px.bar(df_as.head(top_as), x="gasto", y="adset_name", color="roas",
                    color_continuous_scale="RdYlGn", orientation="h",
                    labels={"gasto":"Gasto (R$)","adset_name":"Conjunto","roas":"ROAS"},
                    template="plotly_dark")
    fig_as.update_layout(**LAYOUT, height=max(300, top_as*34),
                         xaxis=dict(tickprefix="R$ "), yaxis=dict(tickfont=dict(size=11)))
    fig_as.update_traces(marker_line_width=0)
    st.plotly_chart(fig_as, use_container_width=True)


# ─── Performance de Criativos ────────────────────────────────────────────────
st.markdown('<div class="section-title">🎨 Performance de Criativos</div>', unsafe_allow_html=True)

if not criativos:
    st.info("Atualize os dados para carregar a performance dos criativos.")
else:
    df_cr = pd.DataFrame(criativos)
    for col in ["visitas_instagram","custo_por_mensagem","impressoes","thumbnail_url","ad_name"]:
        if col not in df_cr.columns:
            df_cr[col] = "" if col in ["thumbnail_url","ad_name"] else 0

    # ── Controles ────────────────────────────────────────────────────────────
    cc1, cc2, cc3 = st.columns([2,1,1])
    with cc1: busca_cr  = st.text_input("🔍 Filtrar criativo", placeholder="Nome do anúncio...", key="cr_busca")
    with cc2: sort_cr   = st.selectbox("Ordenar por", ["Gasto","Receita","ROAS","Impressões","Cliques"], key="cr_sort")
    with cc3: view_mode = st.radio("Visualização", ["Cards","Tabela"], horizontal=True, key="cr_view")

    sort_cr_map = {"Gasto":"gasto","Receita":"receita","ROAS":"roas","Impressões":"impressoes","Cliques":"cliques_link"}
    df_cr_f = df_cr.copy()
    if busca_cr:
        df_cr_f = df_cr_f[df_cr_f["ad_name"].str.contains(busca_cr, case=False, na=False)]
    df_cr_f = df_cr_f[df_cr_f["gasto"] > 0].sort_values(sort_cr_map[sort_cr], ascending=False)

    if view_mode == "Cards":
        top_cr = st.slider("Quantidade de criativos", 3, 24, 9, key="cr_top")
        df_cr_show = df_cr_f.head(top_cr)
        cols_per_row = 3
        rows = [df_cr_show.iloc[i:i+cols_per_row] for i in range(0, len(df_cr_show), cols_per_row)]

        for row_df in rows:
            cols_html = st.columns(cols_per_row)
            for col_idx, (_, cr) in enumerate(row_df.iterrows()):
                with cols_html[col_idx]:
                    thumb = cr.get("thumbnail_url","")
                    roas_cr = cr.get("roas",0)
                    roas_cls = "green" if roas_cr>=3 else ("yellow" if roas_cr>=1 else "red")
                    cpp_cr = cr.get("custo_por_compra",0)

                    # Thumbnail
                    if thumb and thumb.startswith("http"):
                        thumb_html = f'<img src="{thumb}" class="creative-thumb" />'
                    else:
                        thumb_html = '<div class="creative-thumb-placeholder">🖼️</div>'

                    nome = cr.get("ad_name","Sem nome")
                    if len(nome) > 45:
                        nome = nome[:42] + "..."

                    st.markdown(f"""
                    <div class="creative-card">
                      {thumb_html}
                      <div class="creative-body">
                        <div class="creative-name" title="{cr.get('ad_name','')}">{nome}</div>
                        <div class="creative-metric">
                          <span class="cm-label">💸 Gasto</span>
                          <span class="cm-value">{BRL(cr['gasto'])}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">👁 Impressões</span>
                          <span class="cm-value">{NUM(cr['impressoes'])}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">🖱 Cliques</span>
                          <span class="cm-value">{NUM(cr['cliques_link'])}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">📊 CTR</span>
                          <span class="cm-value">{cr.get('ctr',0):.2f}%</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">🛒 Compras</span>
                          <span class="cm-value">{int(cr['compras'])}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">💲 CPP</span>
                          <span class="cm-value">{BRL(cpp_cr) if cpp_cr>0 else "—"}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">📈 ROAS</span>
                          <span class="cm-value {roas_cls}">{roas_cr:.2f}x</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">💬 Conv. Mensagem</span>
                          <span class="cm-value">{int(cr.get('conv_mensagens',0))}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">💸 Custo/Mensagem</span>
                          <span class="cm-value">{BRL(cr.get('custo_por_mensagem',0)) if cr.get('custo_por_mensagem',0)>0 else "—"}</span>
                        </div>
                        <div class="creative-metric">
                          <span class="cm-label">💰 Receita</span>
                          <span class="cm-value green">{BRL(cr['receita'])}</span>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)
    else:
        # Modo tabela
        cols_cr = {
            "ad_name":"Anúncio","campaign_name":"Campanha",
            "impressoes":"Impressões","cliques_link":"Cliques","ctr":"CTR %",
            "frequencia":"Freq.","conv_mensagens":"Conv.Msg","custo_por_mensagem":"$/Msg",
            "compras":"Compras","custo_por_compra":"$/Compra",
            "receita":"Receita","gasto":"Gasto","roas":"ROAS",
        }
        existing_cr = [c for c in cols_cr if c in df_cr_f.columns]
        df_cr_tbl   = df_cr_f[existing_cr].rename(columns=cols_cr)
        fmt_cr = {}
        for c in ["Gasto","Receita","$/Compra","$/Msg"]:
            if c in df_cr_tbl.columns: fmt_cr[c]="R$ {:,.2f}"
        for c in ["Impressões","Cliques","Compras","Conv.Msg"]:
            if c in df_cr_tbl.columns: fmt_cr[c]="{:,.0f}"
        if "ROAS"  in df_cr_tbl.columns: fmt_cr["ROAS"] ="{:.2f}x"
        if "Freq." in df_cr_tbl.columns: fmt_cr["Freq."]="{:.2f}"
        if "CTR %" in df_cr_tbl.columns: fmt_cr["CTR %"]="{:.2f}%"

        def hl_cr(row):
            s = [""]*len(row)
            cl = list(df_cr_tbl.columns)
            if "ROAS" in cl:
                v=row.get("ROAS",0); i=cl.index("ROAS")
                s[i]=f"color:{'#10b981' if v>=3 else ('#f59e0b' if v>=1 else '#ef4444')};font-weight:700"
            return s

        st.dataframe(df_cr_tbl.style.apply(hl_cr,axis=1).format(fmt_cr,na_rep="-"),
                     use_container_width=True, height=480, hide_index=True)

    # ── Gráfico ROAS x Gasto por criativo ────────────────────────────────────
    df_cr_chart = df_cr_f[(df_cr_f["roas"]>0)&(df_cr_f["impressoes"]>0)].head(20)
    if not df_cr_chart.empty:
        st.markdown("#### 📊 ROAS × Impressões por Criativo")
        fig_cr = px.scatter(
            df_cr_chart, x="impressoes", y="roas",
            size="gasto", color="ctr",
            hover_name="ad_name",
            hover_data={"gasto":True,"compras":True,"receita":True,"ctr":True},
            color_continuous_scale="RdYlGn",
            labels={"impressoes":"Impressões","roas":"ROAS","ctr":"CTR %","gasto":"Gasto"},
            template="plotly_dark",
        )
        fig_cr.add_hline(y=1.0, line_dash="dash", line_color="#ef4444", annotation_text="Break-even")
        fig_cr.add_hline(y=3.0, line_dash="dash", line_color="#10b981", annotation_text="ROAS ideal")
        fig_cr.update_layout(**LAYOUT, height=400)
        st.plotly_chart(fig_cr, use_container_width=True)


# ─── Insights Automáticos ────────────────────────────────────────────────────
st.markdown('<div class="section-title">Insights Automáticos</div>', unsafe_allow_html=True)

insights = []
for c in campanhas:
    if c.get("gasto",0) == 0: continue
    nome = c.get("campaign_name","—")
    freq = c.get("frequencia",0)
    roas = c.get("roas",0)
    cpp  = c.get("custo_por_compra",0)
    cpc  = c.get("cpc",0)
    if freq > 4.0:
        insights.append(("red","🔴 Saturação de Público",nome,f"Frequência {freq:.1f}x — renovar criativos ou expandir audiência urgentemente."))
    elif freq > 2.5:
        insights.append(("yellow","🟡 Frequência Moderada",nome,f"Frequência {freq:.1f}x — monitorar nos próximos dias."))
    if c.get("compras",0)>0 and roas>=5:
        insights.append(("green","🚀 Alta Performance",nome,f"ROAS {roas:.2f}x — escale o orçamento!"))
    elif c.get("compras",0)>0 and roas>=3:
        insights.append(("green","🟢 Boa Performance",nome,f"ROAS {roas:.2f}x — campanha lucrativa, boa oportunidade para escalar."))
    elif c.get("compras",0)>0 and roas<1:
        insights.append(("red","🔴 ROAS Negativo",nome,f"ROAS {roas:.2f}x — campanha em prejuízo. Pausar e revisar."))
    if c.get("cliques_link",0)>200 and c.get("compras",0)==0:
        insights.append(("yellow","🟡 Cliques sem Conversão",nome,f"{c['cliques_link']} cliques sem compras — verificar pixel e página de destino."))
    if cpp>300 and c.get("compras",0)>0:
        insights.append(("red","🔴 CPP Muito Alto",nome,f"CPP R$ {cpp:.2f} — revisar segmentação e criativos."))

# Insights de criativos
for cr in criativos:
    if cr.get("gasto",0)==0: continue
    if cr.get("ctr",0)>5 and cr.get("compras",0)==0:
        insights.append(("yellow","🟡 Criativo com Alto CTR sem Compras",
                         cr.get("ad_name",""),
                         f"CTR {cr.get('ctr',0):.2f}% mas sem compras — verificar página de destino."))
    if cr.get("roas",0)>=5 and cr.get("gasto",0)>0:
        insights.append(("green","🚀 Criativo Campeão",
                         cr.get("ad_name",""),
                         f"ROAS {cr.get('roas',0):.2f}x — este criativo está performando muito bem, duplique!"))

ci1, ci2 = st.columns(2)
if not insights:
    st.success("✅ Todas as métricas estão dentro dos parâmetros esperados.")
else:
    for i, (tipo, titulo, nome, msg) in enumerate(insights):
        cls = f"insight-{tipo}"
        target = ci1 if i%2==0 else ci2
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
    for msg in st.session_state.chat_history:
        if msg["role"]=="user":
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="chat-ai">
              <div class="chat-ai-header">🤖 Assistente Meta Ads</div>
              {msg["content"]}</div>""", unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        ci_a, ci_b = st.columns([5,1])
        with ci_a:
            user_input = st.text_input("msg", label_visibility="collapsed",
                                       placeholder="Ex: Quais criativos devo pausar? Como melhorar o ROAS?")
        with ci_b:
            submitted = st.form_submit_button("Enviar →")

    if submitted and user_input.strip():
        st.session_state.chat_history.append({"role":"user","content":user_input})
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        sys_p = f"""Você é um especialista sênior em tráfego pago e Meta Ads.
Analise os dados e responda em português do Brasil de forma clara, objetiva e acionável.
Use markdown e emojis para destacar pontos importantes.

DADOS DO RELATÓRIO:
{ctx}"""
        msgs = [{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_history]
        try:
            with st.spinner("Analisando..."):
                resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500,
                                              system=sys_p, messages=msgs)
            ai_reply = resp.content[0].text
        except Exception as e:
            ai_reply = f"Erro: {e}"
        st.session_state.chat_history.append({"role":"assistant","content":ai_reply})
        st.rerun()

    if st.button("🗑 Limpar conversa"):
        st.session_state.chat_history = []
        st.rerun()


# ─── Rodapé ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<p style='text-align:center;color:#1e293b;font-size:12px'>"
    f"Meta Ads Dashboard · Meta Graph API v21.0 · "
    f"Última atualização: {report.get('gerado_em','')[:16].replace('T',' ')}</p>",
    unsafe_allow_html=True,
)
