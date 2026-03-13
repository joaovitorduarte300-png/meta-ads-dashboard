"""
Gerador de relatórios Meta Ads — busca dados e salva JSON/cache para o dashboard.
Executado toda segunda-feira às 08h ou sob demanda.
"""
import sys, io, json, os, datetime, requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ACCESS_TOKEN = "EAAW8pPurJVQBQ5ghAlBe4pEbcbvhlo3oz7VuGsJQOJcLxCKQWsDB1PhZCFrv1sp4FZCG74OE2JdfzYxDaXDfBdsZBgYVzqVPrOG7CymhLtzgD0dClyPEHO4s7H91rQlZB36gfCFHymot1QA3z3JQijNZB43Vf9t3vAqYi1ldNNHZBa2LFsUMLfy2Wx6iDZAhaGFLj7RLl9XoAZDZD"
BASE_URL = "https://graph.facebook.com/v21.0"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "report_cache.json")

INSIGHT_FIELDS = (
    "reach,impressions,frequency,inline_link_clicks,spend,"
    "actions,cost_per_action_type,action_values,cpc,cpm,ctr,"
    "campaign_id,campaign_name,adset_id,adset_name"
)


def _get(endpoint, params=None):
    p = {"access_token": ACCESS_TOKEN}
    if params:
        p.update(params)
    r = requests.get(f"{BASE_URL}/{endpoint.lstrip('/')}", params=p)
    return r.json()


def _get_all(endpoint, params=None):
    data, result = [], _get(endpoint, params)
    data.extend(result.get("data", []))
    paging = result.get("paging", {})
    while "next" in paging:
        result = requests.get(paging["next"]).json()
        data.extend(result.get("data", []))
        paging = result.get("paging", {})
    return data


def _action(actions, atype):
    return float(next((a["value"] for a in (actions or []) if a.get("action_type") == atype), 0))


def _cost(costs, atype):
    return float(next((a["value"] for a in (costs or []) if a.get("action_type") == atype), 0))


def _parse(raw, extra=None):
    actions = raw.get("actions", [])
    costs   = raw.get("cost_per_action_type", [])
    values  = raw.get("action_values", [])
    compras     = _action(actions, "purchase")
    conv_msg    = _action(actions, "onsite_conversion.messaging_conversation_started_7d")
    cpp         = _cost(costs, "purchase")
    receita     = _action(values, "purchase")
    gasto       = float(raw.get("spend", 0) or 0)
    impressoes  = int(raw.get("impressions", 0) or 0)
    m = {
        "alcance":          int(raw.get("reach", 0) or 0),
        "impressoes":       impressoes,
        "frequencia":       round(float(raw.get("frequency", 0) or 0), 2),
        "cliques_link":     int(raw.get("inline_link_clicks", 0) or 0),
        "gasto":            round(gasto, 2),
        "compras":          int(compras),
        "conv_mensagens":   int(conv_msg),
        "custo_por_compra": round(cpp, 2),
        "receita":          round(receita, 2),
        "cpc":              round(float(raw.get("cpc", 0) or 0), 2),
        "cpm":              round(float(raw.get("cpm", 0) or 0), 2),
        "ctr":              round(float(raw.get("ctr", 0) or 0), 2),
        "roas":             round(receita / gasto, 2) if gasto > 0 else 0.0,
    }
    if extra:
        m.update(extra)
    return m


def fetch_report(date_preset="last_7d"):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] Gerando relatório ({date_preset})...")

    # Contas
    accounts_raw = _get_all("me/adaccounts", {
        "fields": "id,name,account_status,currency,amount_spent,balance"
    })
    accounts = [a for a in accounts_raw if a.get("account_status") == 1]
    print(f"  {len(accounts)} conta(s) ativa(s)")

    report = {
        "gerado_em":  datetime.datetime.now().isoformat(),
        "date_preset": date_preset,
        "contas":     [],
    }

    for acc in accounts:
        aid = acc["id"]
        print(f"  Processando: {acc['name']}")

        # Insights por campanha
        camp_insights = _get(f"{aid}/insights", {
            "fields": INSIGHT_FIELDS,
            "date_preset": date_preset,
            "level": "campaign",
        }).get("data", [])

        # Insights por conjunto
        adset_insights = _get(f"{aid}/insights", {
            "fields": INSIGHT_FIELDS,
            "date_preset": date_preset,
            "level": "adset",
        }).get("data", [])

        # Campanhas
        campaigns_raw = _get_all(f"{aid}/campaigns", {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget"
        })

        camp_map = {c["id"]: c for c in campaigns_raw}

        camp_metrics = []
        for ci in camp_insights:
            cid  = ci.get("campaign_id", "")
            meta = camp_map.get(cid, {})
            m    = _parse(ci, {
                "campaign_id":   cid,
                "campaign_name": ci.get("campaign_name", meta.get("name", "")),
                "status":        meta.get("status", ""),
                "objetivo":      meta.get("objective", ""),
            })
            camp_metrics.append(m)

        adset_metrics = []
        for ai in adset_insights:
            m = _parse(ai, {
                "adset_id":      ai.get("adset_id", ""),
                "adset_name":    ai.get("adset_name", ""),
                "campaign_name": ai.get("campaign_name", ""),
            })
            adset_metrics.append(m)

        # Totais da conta
        t_gasto   = sum(m["gasto"]   for m in camp_metrics)
        t_compras = sum(m["compras"] for m in camp_metrics)
        t_receita = sum(m["receita"] for m in camp_metrics)
        t_alcance = sum(m["alcance"] for m in camp_metrics)
        t_cliques = sum(m["cliques_link"] for m in camp_metrics)
        t_conv    = sum(m["conv_mensagens"] for m in camp_metrics)
        t_cpp     = round(t_gasto / t_compras, 2) if t_compras > 0 else 0
        t_roas    = round(t_receita / t_gasto, 2) if t_gasto > 0 else 0

        report["contas"].append({
            "id":     aid,
            "nome":   acc["name"],
            "moeda":  acc.get("currency", "BRL"),
            "totais": {
                "gasto":            round(t_gasto, 2),
                "compras":          t_compras,
                "receita":          round(t_receita, 2),
                "alcance":          t_alcance,
                "cliques_link":     t_cliques,
                "conv_mensagens":   t_conv,
                "custo_por_compra": t_cpp,
                "roas":             t_roas,
            },
            "campanhas":  camp_metrics,
            "conjuntos":  adset_metrics,
        })

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Relatório salvo em: {CACHE_FILE}")
    return report


def load_report():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    preset = sys.argv[1] if len(sys.argv) > 1 else "last_7d"
    fetch_report(preset)
