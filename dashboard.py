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

# ─── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meta Ads Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS customizado ───────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Fundo geral */
  .stApp { background: #0f1117; color: #e0e0e0; }

  /* Cards de KPI */
  .kpi-card {
    background: linear-gradient(135deg, #1e2130 0%, #252a3a 100%);
    border: 1px solid #2d3350;
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    transition: transform .2s;
  }
  .kpi-card:hover { transform: translateY(-3px); }
  .kpi-label { font-size: 12px; color: #8892b0; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }
  .kpi-value { font-size: 28px; font-weight: 700; color: #e0e6ff; }
  .kpi-delta { font-size: 12px; margin-top: 4px; }
  .delta-up   { color: #4ade80; }
  .delta-down { color: #f87171; }
  .delta-neu  { color: #94a3b8; }

  /* Título de seção */
  .section-title {
    font-size: 18px; font-weight: 600; color: #a5b4fc;
    border-left: 4px solid #6366f1; padding-left: 12px;
    margin: 28px 0 16px;
  }

  /* Chat IA */
  .chat-bubble-user {
    background: #2d3350; border-radius: 14px 14px 4px 14px;
    padding: 10px 16px; margin: 8px 0; max-width: 80%; margin-left: auto;
    color: #e0e6ff; font-size: 14px;
  }
  .chat-bubble-ai {
    background: #1e2537; border: 1px solid #3b4168; border-radius: 14px 14px 14px 4px;
    padding: 12px 16px; margin: 8px 0; max-width: 88%;
    color: #c8cfe0; font-size: 14px; line-height: 1.6;
  }
  .chat-header {
    font-size: 11px; color: #6366f1; font-weight: 600;
    margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px;
  }

  /* Tabela customizada */
  .dataframe { border-radius: 10px; overflow: hidden; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #141824; }

  /* Botões */
  .stButton > button {
    background: linear-gradient(135deg, #6366f1, #818cf8);
    color: white; border: none; border-radius: 8px;
    font-weight: 600; transition: all .2s;
  }
  .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ───────────────────────────────────────────────────────────────────
BRL = lambda v: f"R$ {v:,.2f}"
NUM = lambda v: f"{int(v):,}"
PCT = lambda v: f"{v:.1f}%"

PRESETS = {
    "Hoje":             "today",
    "Ontem":            "yesterday",
    "Últimos 7 dias":   "last_7d",
    "Últimos 14 dias":  "last_14d",
    "Últimos 30 dias":  "last_30d",
    "Este mês":         "this_month",
    "Mês passado":      "last_month",
    "Todo o período":   "maximum",
}

def status_color(field, value):
    thresholds = {
        "frequencia":       (2.5, 4.0, False),
        "cpc":              (1.5, 4.0, False),
        "cpm":              (15,  40,  False),
        "custo_por_compra": (50,  150, False),
        "roas":             (1.0, 3.0, True),
    }
    if field not in thresholds or value == 0:
        return "⬜"
    lo, hi, higher_is_better = thresholds[field]
    if higher_is_better:
        return "🟢" if value >= hi else ("🟡" if value >= lo else "🔴")
    return "🟢" if value <= lo else ("🟡" if value <= hi else "🔴")


def kpi_card(label, value, delta_text="", delta_type="neu"):
    delta_html = f'<div class="kpi-delta delta-{delta_type}">{delta_text}</div>' if delta_text else ""
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {delta_html}
    </div>"""


def build_context_text(report, conta_idx):
    """Monta texto resumido do relatório para o prompt do Claude."""
    if not report or not report.get("contas"):
        return "Sem dados disponíveis."
    conta = report["contas"][conta_idx]
    t = conta["totais"]
    lines = [
        f"Conta: {conta['nome']}",
        f"Período: {report.get('date_preset', '?')}",
        f"Gasto total: {BRL(t['gasto'])}",
        f"Compras: {NUM(t['compras'])}",
        f"Receita: {BRL(t['receita'])}",
        f"ROAS: {t['roas']:.2f}x",
        f"Alcance: {NUM(t['alcance'])}",
        f"Custo por compra: {BRL(t['custo_por_compra'])}",
        f"Conversas por mensagem: {NUM(t['conv_mensagens'])}",
        "",
        "Campanhas:",
    ]
    for c in conta.get("campanhas", [])[:10]:
        lines.append(
            f"  - [{c.get('status','')}] {c.get('campaign_name','')} | "
            f"Gasto={BRL(c['gasto'])} Compras={c['compras']} ROAS={c['roas']:.2f}x "
            f"Freq={c['frequencia']:.1f} CPP={BRL(c['custo_por_compra'])}"
        )
    return "\n".join(lines)


# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Meta Ads Dashboard")
    st.markdown("---")

    preset_label = st.selectbox("Período", list(PRESETS.keys()), index=2)
    date_preset  = PRESETS[preset_label]

    st.markdown("---")
    col_r, col_l = st.columns(2)
    with col_r:
        if st.button("🔄 Atualizar dados"):
            with st.spinner("Buscando dados..."):
                st.session_state["report"] = fetch_report(date_preset)
            st.success("Dados atualizados!")
    with col_l:
        if st.button("📋 Usar cache"):
            st.session_state["report"] = load_report()

    st.markdown("---")
    if os.getenv("ANTHROPIC_API_KEY"):
        st.markdown("✅ **Chat IA:** Ativo")
    else:
        st.warning("ANTHROPIC_API_KEY não encontrada no .env")

    st.markdown("---")
    st.caption(f"Gerado: {datetime.datetime.now():%d/%m/%Y %H:%M}")


# ─── Carregar dados ────────────────────────────────────────────────────────────
if "report" not in st.session_state:
    cached = load_report()
    if cached:
        st.session_state["report"] = cached
    else:
        st.info("Clique em **Atualizar dados** na barra lateral para carregar o relatório.")
        st.stop()

report = st.session_state["report"]

if not report or not report.get("contas"):
    st.warning("Nenhuma conta com dados disponíveis.")
    st.stop()

# Seletor de conta
contas_nomes = [c["nome"] for c in report["contas"]]
conta_sel    = st.selectbox("Conta de Anúncio", contas_nomes)
conta_idx    = contas_nomes.index(conta_sel)
conta        = report["contas"][conta_idx]
totais       = conta["totais"]
campanhas    = conta.get("campanhas", [])
conjuntos    = conta.get("conjuntos", [])

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"# 📊 Meta Ads — {conta['nome']}")
st.markdown(f"<span style='color:#8892b0;font-size:13px'>Período: **{preset_label}** &nbsp;|&nbsp; "
            f"Gerado em: {report.get('gerado_em','?')[:16].replace('T',' ')}</span>",
            unsafe_allow_html=True)
st.markdown("---")

# ─── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Visão Geral</div>', unsafe_allow_html=True)

cols = st.columns(4)
kpis = [
    ("💸 Gasto Total",          BRL(totais["gasto"]),            "", "neu"),
    ("🛒 Compras",               NUM(totais["compras"]),          "", "neu"),
    ("💰 Receita",               BRL(totais["receita"]),          "", "up" if totais["receita"] > totais["gasto"] else "down"),
    ("📈 ROAS",                  f"{totais['roas']:.2f}x",        "🟢 Bom" if totais["roas"] >= 3 else ("🟡 Regular" if totais["roas"] >= 1 else "🔴 Negativo"), "up" if totais["roas"] >= 3 else "down"),
    ("👁 Alcance",               NUM(totais["alcance"]),          "", "neu"),
    ("🖱 Cliques no Link",       NUM(totais["cliques_link"]),     "", "neu"),
    ("💬 Conv. Mensagens",       NUM(totais["conv_mensagens"]),   "", "neu"),
    ("💲 Custo por Compra",      BRL(totais["custo_por_compra"]), "", "up" if 0 < totais["custo_por_compra"] < 50 else "down"),
]

for i, (label, val, delta, dtype) in enumerate(kpis):
    with cols[i % 4]:
        st.markdown(kpi_card(label, val, delta, dtype), unsafe_allow_html=True)
    if i == 3:
        cols = st.columns(4)

# ─── Gráficos ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Desempenho por Campanha</div>', unsafe_allow_html=True)

if campanhas:
    df_camp = pd.DataFrame(campanhas)

    tab1, tab2, tab3, tab4 = st.tabs(["💸 Gasto vs Receita", "📊 Métricas", "🔁 ROAS", "📋 Tabela Completa"])

    with tab1:
        df_sorted = df_camp.sort_values("gasto", ascending=False).head(12)
        fig = go.Figure()
        fig.add_bar(name="Gasto (R$)",   x=df_sorted["campaign_name"], y=df_sorted["gasto"],
                    marker_color="#6366f1")
        fig.add_bar(name="Receita (R$)", x=df_sorted["campaign_name"], y=df_sorted["receita"],
                    marker_color="#4ade80")
        fig.update_layout(
            barmode="group", template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=380,
            legend=dict(orientation="h", y=1.1),
            xaxis_tickangle=-35,
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        metric_sel = st.selectbox("Métrica", ["alcance","impressoes","cliques_link",
                                               "compras","conv_mensagens","frequencia","cpc","cpm"])
        df_m = df_camp[df_camp[metric_sel] > 0].sort_values(metric_sel, ascending=False).head(15)
        fig2 = px.bar(df_m, x="campaign_name", y=metric_sel, color=metric_sel,
                      color_continuous_scale="Viridis", template="plotly_dark",
                      labels={"campaign_name": "Campanha", metric_sel: metric_sel.replace("_"," ").title()})
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           height=380, xaxis_tickangle=-35, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        df_roas = df_camp[(df_camp["roas"] > 0) & (df_camp["compras"] > 0)].copy()
        if df_roas.empty:
            st.info("Sem dados de ROAS com compras para exibir.")
        else:
            fig3 = px.scatter(
                df_roas, x="gasto", y="roas", size="compras", color="frequencia",
                hover_name="campaign_name",
                color_continuous_scale="RdYlGn_r",
                labels={"gasto": "Gasto (R$)", "roas": "ROAS", "compras": "Compras", "frequencia": "Frequência"},
                template="plotly_dark",
                title="Gasto × ROAS (tamanho = compras, cor = frequência)",
            )
            fig3.add_hline(y=1.0, line_dash="dash", line_color="#f87171",
                           annotation_text="Break-even (1x)")
            fig3.add_hline(y=3.0, line_dash="dash", line_color="#4ade80",
                           annotation_text="ROAS ideal (3x)")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430)
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        display_cols = {
            "campaign_name":   "Campanha",
            "status":          "Status",
            "objetivo":        "Objetivo",
            "alcance":         "Alcance",
            "impressoes":      "Impressões",
            "frequencia":      "Freq.",
            "cliques_link":    "Cliques",
            "conv_mensagens":  "Conv.Msg",
            "compras":         "Compras",
            "custo_por_compra":"Cst/Compra",
            "receita":         "Receita",
            "gasto":           "Gasto",
            "roas":            "ROAS",
        }
        df_show = df_camp[[c for c in display_cols if c in df_camp.columns]].rename(columns=display_cols)
        df_show = df_show.sort_values("Gasto", ascending=False)

        def highlight(row):
            styles = [""] * len(row)
            cols_list = list(df_show.columns)
            if "ROAS" in cols_list:
                roas = row.get("ROAS", 0)
                idx = cols_list.index("ROAS")
                styles[idx] = f"color: {'#4ade80' if roas >= 3 else ('#facc15' if roas >= 1 else '#f87171')}"
            if "Freq." in cols_list:
                freq = row.get("Freq.", 0)
                idx = cols_list.index("Freq.")
                styles[idx] = f"color: {'#f87171' if freq > 4 else ('#facc15' if freq > 2.5 else '#4ade80')}"
            return styles

        st.dataframe(
            df_show.style.apply(highlight, axis=1).format({
                "Gasto": "R$ {:,.2f}", "Receita": "R$ {:,.2f}",
                "Cst/Compra": "R$ {:,.2f}", "ROAS": "{:.2f}x",
                "Freq.": "{:.2f}", "Alcance": "{:,.0f}",
                "Impressões": "{:,.0f}", "Cliques": "{:,.0f}",
            }),
            use_container_width=True, height=420,
        )

# ─── Conjuntos ────────────────────────────────────────────────────────────────
if conjuntos:
    st.markdown('<div class="section-title">Conjuntos de Anúncios</div>', unsafe_allow_html=True)
    df_adset = pd.DataFrame(conjuntos)
    df_adset_disp = df_adset.sort_values("gasto", ascending=False)

    fig_as = px.bar(df_adset_disp.head(15), x="adset_name", y="gasto",
                    color="roas", color_continuous_scale="RdYlGn",
                    template="plotly_dark",
                    labels={"adset_name": "Conjunto", "gasto": "Gasto (R$)", "roas": "ROAS"})
    fig_as.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         height=340, xaxis_tickangle=-35)
    st.plotly_chart(fig_as, use_container_width=True)

# ─── Pie de distribuição de gasto ─────────────────────────────────────────────
if campanhas:
    st.markdown('<div class="section-title">Distribuição de Gasto por Campanha</div>',
                unsafe_allow_html=True)
    df_pie = df_camp[df_camp["gasto"] > 0].nlargest(10, "gasto")
    fig_pie = px.pie(df_pie, values="gasto", names="campaign_name",
                     template="plotly_dark", hole=0.45,
                     color_discrete_sequence=px.colors.sequential.Plasma_r)
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=380,
                          legend=dict(font=dict(size=11)))
    st.plotly_chart(fig_pie, use_container_width=True)

# ─── Insights automáticos ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Insights Automáticos</div>', unsafe_allow_html=True)

insights = []
for c in campanhas:
    if c["gasto"] == 0:
        continue
    nome = c.get("campaign_name", "")
    if c["frequencia"] > 4.0:
        insights.append(("🔴 ALERTA", nome, f"Frequência alta ({c['frequencia']:.1f}x) — renovar criativos ou expandir público."))
    elif c["frequencia"] > 2.5:
        insights.append(("🟡 ATENÇÃO", nome, f"Frequência moderada ({c['frequencia']:.1f}x) — monitorar."))
    if c["compras"] > 0 and c["roas"] >= 3:
        insights.append(("🟢 OPORTUNIDADE", nome, f"ROAS {c['roas']:.2f}x — boa performance, considere escalar orçamento."))
    elif c["compras"] > 0 and c["roas"] < 1:
        insights.append(("🔴 ALERTA", nome, f"ROAS {c['roas']:.2f}x — campanha deficitária, revisar ou pausar."))
    if c["cliques_link"] > 100 and c["compras"] == 0:
        insights.append(("🟡 ATENÇÃO", nome, f"{c['cliques_link']} cliques sem compras — verificar pixel e página de destino."))
    if c["cpc"] > 4.0:
        insights.append(("🟡 ATENÇÃO", nome, f"CPC alto R$ {c['cpc']:.2f} — testar novos criativos."))

if not insights:
    st.success("Todas as métricas estão dentro dos parâmetros esperados.")
else:
    for tipo, nome, msg in insights:
        color = "#1e3a2f" if "🟢" in tipo else ("#3a1e1e" if "🔴" in tipo else "#2e2b1e")
        border = "#4ade80" if "🟢" in tipo else ("#f87171" if "🔴" in tipo else "#facc15")
        st.markdown(f"""
        <div style="background:{color};border-left:4px solid {border};border-radius:8px;
                    padding:12px 16px;margin:8px 0;">
          <strong>{tipo}</strong> — {nome}<br>
          <span style="color:#c8cfe0;font-size:13px">{msg}</span>
        </div>""", unsafe_allow_html=True)

# ─── Chat com IA ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">💬 Chat com IA — Pergunte sobre o Relatório</div>',
            unsafe_allow_html=True)

if not os.getenv("ANTHROPIC_API_KEY"):
    st.warning("Insira sua ANTHROPIC_API_KEY na barra lateral para ativar o chat com IA.")
else:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    context_text = build_context_text(report, conta_idx)

    # Histórico de mensagens
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-bubble-user">{msg["content"]}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-bubble-ai">
                  <div class="chat-header">🤖 Assistente Meta Ads</div>
                  {msg["content"]}
                </div>""", unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Sua pergunta",
            placeholder="Ex: Por que o ROAS está baixo? O que fazer para reduzir o custo por compra?",
        )
        submitted = st.form_submit_button("Enviar →")

    if submitted and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        system_prompt = f"""Você é um especialista em tráfego pago e Meta Ads com mais de 10 anos de experiência.
O usuário está analisando um relatório de Meta Ads e tem dúvidas sobre os dados. Responda de forma clara, objetiva e prática.
Use emojis quando apropriado. Sempre que recomendar ação, seja específico.
Fale em português do Brasil.

Dados do relatório:
{context_text}"""

        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history
        ]

        try:
            with st.spinner("Analisando..."):
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=messages,
                )
            ai_reply = response.content[0].text
        except Exception as e:
            ai_reply = f"Erro ao chamar a API: {e}"

        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
        st.rerun()

    if st.button("🗑 Limpar conversa"):
        st.session_state.chat_history = []
        st.rerun()

# ─── Rodapé ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#4a5568;font-size:12px'>"
    "Meta Ads Dashboard · Dados via Meta Graph API v21.0 · "
    f"Última atualização: {report.get('gerado_em','?')[:16].replace('T',' ')}"
    "</p>",
    unsafe_allow_html=True,
)
