"""
Gerador de relatórios Meta Ads — busca dados e salva JSON/cache para o dashboard.
Executado toda segunda-feira às 08h ou sob demanda.
"""
import sys, json, os, datetime, requests

ACCESS_TOKEN = "EAAW8pPurJVQBQ5ghAlBe4pEbcbvhlo3oz7VuGsJQOJcLxCKQWsDB1PhZCFrv1sp4FZCG74OE2JdfzYxDaXDfBdsZBgYVzqVPrOG7CymhLtzgD0dClyPEHO4s7H91rQlZB36gfCFHymot1QA3z3JQijNZB43Vf9t3vAqYi1ldNNHZBa2LFsUMLfy2Wx6iDZAhaGFLj7RLl9XoAZDZD"
BASE_URL   = "https://graph.facebook.com/v21.0"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "report_cache.json")

INSIGHT_FIELDS = (
    "reach,impressions,frequency,inline_link_clicks,spend,"
    "actions,cost_per_action_type,action_values,cpc,cpm,ctr,"
    "campaign_id,campaign_name,adset_id,adset_name"
)

AD_INSIGHT_FIELDS = (
    "reach,impressions,frequency,inline_link_clicks,spend,"
    "actions,cost_per_action_type,action_values,cpc,cpm,ctr,"
    "ad_id,ad_name,campaign_name,adset_name"
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
    # Visitas ao perfil do Instagram (tenta múltiplos action types)
    visitas_ig  = (
        _action(actions, "instagram_profile_visit") or
        _action(actions, "onsite_conversion.flow_complete") or
        _action(actions, "page_engagement")
    )
    cpp         = _cost(costs, "purchase")
    custo_msg   = _cost(costs, "onsite_conversion.messaging_conversation_started_7d")
    receita     = _action(values, "purchase")
    gasto       = float(raw.get("spend", 0) or 0)
    impressoes  = int(raw.get("impressions", 0) or 0)
    alcance     = int(raw.get("reach", 0) or 0)

    m = {
        "alcance":            alcance,
        "impressoes":         impressoes,
        "frequencia":         round(float(raw.get("frequency", 0) or 0), 2),
        "cliques_link":       int(raw.get("inline_link_clicks", 0) or 0),
        "visitas_instagram":  int(visitas_ig),
        "conv_mensagens":     int(conv_msg),
        "custo_por_mensagem": round(custo_msg, 2),
        "gasto":              round(gasto, 2),
        "compras":            int(compras),
        "custo_por_compra":   round(cpp, 2),
        "receita":            round(receita, 2),
        "cpc":                round(float(raw.get("cpc", 0) or 0), 2),
        "cpm":                round(float(raw.get("cpm", 0) or 0), 2),
        "ctr":                round(float(raw.get("ctr", 0) or 0), 2),
        "roas":               round(receita / gasto, 2) if gasto > 0 else 0.0,
    }
    if extra:
        m.update(extra)
    return m


def _fetch_ad_creatives(aid):
    """Busca anúncios com URL de thumbnail do criativo."""
    try:
        ads = _get_all(f"{aid}/ads", {
            "fields": "id,name,status,creative{id,thumbnail_url,object_story_spec,image_url}",
            "limit": 200,
        })
        resultado = {}
        for ad in ads:
            creative = ad.get("creative", {})
            thumb = (
                creative.get("thumbnail_url") or
                creative.get("image_url") or
                ""
            )
            # Tenta pegar imagem do object_story_spec se não tiver thumbnail
            if not thumb:
                oss = creative.get("object_story_spec", {})
                if "video_data" in oss:
                    thumb = oss["video_data"].get("image_url", "")
                elif "link_data" in oss:
                    thumb = oss["link_data"].get("image_hash", "")

            resultado[ad["id"]] = {
                "creative_id":   creative.get("id", ""),
                "thumbnail_url": thumb,
                "ad_name":       ad.get("name", ""),
                "status":        ad.get("status", ""),
            }
        return resultado
    except Exception:
        return {}


def fetch_report(date_preset="last_7d"):
    accounts_raw = _get_all("me/adaccounts", {
        "fields": "id,name,account_status,currency,amount_spent,balance"
    })
    accounts = [a for a in accounts_raw if a.get("account_status") == 1]

    report = {
        "gerado_em":   datetime.datetime.now().isoformat(),
        "date_preset": date_preset,
        "contas":      [],
    }

    for acc in accounts:
        aid  = acc["id"]
        nome = acc["name"]

        # ── Insights por campanha ─────────────────────────────────────────
        camp_insights = _get(f"{aid}/insights", {
            "fields":      INSIGHT_FIELDS,
            "date_preset": date_preset,
            "level":       "campaign",
        }).get("data", [])

        # ── Insights por conjunto ─────────────────────────────────────────
        adset_insights = _get(f"{aid}/insights", {
            "fields":      INSIGHT_FIELDS,
            "date_preset": date_preset,
            "level":       "adset",
        }).get("data", [])

        # ── Insights por anúncio (criativos) ─────────────────────────────
        ad_insights = _get(f"{aid}/insights", {
            "fields":      AD_INSIGHT_FIELDS,
            "date_preset": date_preset,
            "level":       "ad",
        }).get("data", [])

        # ── Metadados das campanhas ───────────────────────────────────────
        campaigns_raw = _get_all(f"{aid}/campaigns", {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget"
        })
        camp_map = {c["id"]: c for c in campaigns_raw}

        # ── Thumbnails dos criativos ──────────────────────────────────────
        creative_map = _fetch_ad_creatives(aid)

        # ── Processar campanhas ───────────────────────────────────────────
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

        # ── Processar conjuntos ───────────────────────────────────────────
        adset_metrics = []
        for ai_row in adset_insights:
            m = _parse(ai_row, {
                "adset_id":      ai_row.get("adset_id", ""),
                "adset_name":    ai_row.get("adset_name", ""),
                "campaign_name": ai_row.get("campaign_name", ""),
            })
            adset_metrics.append(m)

        # ── Processar anúncios / criativos ────────────────────────────────
        ad_metrics = []
        for ad_row in ad_insights:
            ad_id = ad_row.get("ad_id", "")
            info  = creative_map.get(ad_id, {})
            m = _parse(ad_row, {
                "ad_id":          ad_id,
                "ad_name":        ad_row.get("ad_name", info.get("ad_name", "")),
                "campaign_name":  ad_row.get("campaign_name", ""),
                "adset_name":     ad_row.get("adset_name", ""),
                "thumbnail_url":  info.get("thumbnail_url", ""),
                "creative_id":    info.get("creative_id", ""),
            })
            ad_metrics.append(m)

        # ── Totais da conta ───────────────────────────────────────────────
        t_gasto      = sum(m["gasto"]             for m in camp_metrics)
        t_compras    = sum(m["compras"]            for m in camp_metrics)
        t_receita    = sum(m["receita"]            for m in camp_metrics)
        t_alcance    = sum(m["alcance"]            for m in camp_metrics)
        t_impressoes = sum(m["impressoes"]         for m in camp_metrics)
        t_cliques    = sum(m["cliques_link"]       for m in camp_metrics)
        t_visitas_ig = sum(m["visitas_instagram"]  for m in camp_metrics)
        t_conv       = sum(m["conv_mensagens"]     for m in camp_metrics)
        t_cpp        = round(t_gasto / t_compras, 2)  if t_compras > 0 else 0
        t_custo_msg  = round(t_gasto / t_conv, 2)     if t_conv > 0    else 0
        t_roas       = round(t_receita / t_gasto, 2)  if t_gasto > 0   else 0

        report["contas"].append({
            "id":    aid,
            "nome":  nome,
            "moeda": acc.get("currency", "BRL"),
            "totais": {
                "alcance":            t_alcance,
                "impressoes":         t_impressoes,
                "cliques_link":       t_cliques,
                "visitas_instagram":  t_visitas_ig,
                "conv_mensagens":     t_conv,
                "custo_por_mensagem": t_custo_msg,
                "compras":            t_compras,
                "custo_por_compra":   t_cpp,
                "receita":            round(t_receita, 2),
                "gasto":              round(t_gasto, 2),
                "roas":               t_roas,
            },
            "campanhas":  camp_metrics,
            "conjuntos":  adset_metrics,
            "criativos":  ad_metrics,
        })

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def load_report():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    preset = sys.argv[1] if len(sys.argv) > 1 else "last_7d"
    fetch_report(preset)
