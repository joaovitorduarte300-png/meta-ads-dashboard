"""
Gerador de relatórios Meta Ads — busca dados e salva JSON/cache para o dashboard.
"""
import sys, json, os, datetime, requests

ACCESS_TOKEN = "EAANTGkkCPMABRTXnFpAyBEO5XDkN5OAGZATrIiP9oWDjLBYiDbkNHbZBjYi7ZAZBZCKaNCAKy7HasxR9rf6JfSFU4zCseZCEZB9DBMGwF70ZAtitBNgqFCUfjZBUYNTY3PlkEPDeB3GzEXQZBMFbx3Vd1Pl3YD3H0YoFhjqqzRKdWC9bR4qd3apOqennZB1sgZDZD"
BASE_URL  = "https://graph.facebook.com/v21.0"
CACHE_DIR = os.path.dirname(__file__) or "."

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


def _cache_path(date_preset):
    return os.path.join(CACHE_DIR, f"report_cache_{date_preset}.json")


def _get(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    p = {"access_token": ACCESS_TOKEN}
    if params:
        p.update(params)
    try:
        r = requests.get(url, params=p, timeout=30)
        data = r.json()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout ao chamar '{endpoint}'")
    except Exception as e:
        raise RuntimeError(f"Erro de rede em '{endpoint}': {e}")
    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"Meta API erro {err.get('code','?')} em '{endpoint}': {err.get('message', err)}"
        )
    return data


def _get_all(endpoint, params=None):
    result = _get(endpoint, params)
    data = list(result.get("data", []))
    paging = result.get("paging", {})
    while "next" in paging:
        try:
            r = requests.get(paging["next"], timeout=30).json()
            if "error" in r:
                break
            data.extend(r.get("data", []))
            paging = r.get("paging", {})
        except Exception:
            break
    return data


def _action(actions, atype):
    return float(next((a["value"] for a in (actions or []) if a.get("action_type") == atype), 0))


def _cost(costs, atype):
    return float(next((a["value"] for a in (costs or []) if a.get("action_type") == atype), 0))


def _parse(raw, extra=None):
    actions = raw.get("actions", [])
    costs   = raw.get("cost_per_action_type", [])
    values  = raw.get("action_values", [])

    compras    = _action(actions, "purchase")
    conv_msg   = _action(actions, "onsite_conversion.messaging_conversation_started_7d")
    visitas_ig = (
        _action(actions, "instagram_profile_visit") or
        _action(actions, "onsite_conversion.flow_complete") or
        _action(actions, "page_engagement")
    )
    cpp       = _cost(costs, "purchase")
    custo_msg = _cost(costs, "onsite_conversion.messaging_conversation_started_7d")
    receita   = _action(values, "purchase")
    gasto     = float(raw.get("spend", 0) or 0)

    m = {
        "alcance":            int(raw.get("reach", 0) or 0),
        "impressoes":         int(raw.get("impressions", 0) or 0),
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
    try:
        ads = _get_all(f"{aid}/ads", {
            "fields": "id,name,status,creative{id,thumbnail_url,object_story_spec,image_url}",
            "limit": 200,
        })
        resultado = {}
        for ad in ads:
            creative = ad.get("creative", {})
            thumb = creative.get("thumbnail_url") or creative.get("image_url") or ""
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


def get_accounts():
    """Retorna lista de contas de anúncios e a resposta bruta da API para debug."""
    raw = _get("me/adaccounts", {"fields": "id,name,account_status", "limit": 200})
    accounts_raw = raw.get("data", [])
    # Pagina manualmente se houver mais contas
    paging = raw.get("paging", {})
    while "next" in paging:
        try:
            r = requests.get(paging["next"], timeout=30).json()
            if "error" in r:
                break
            accounts_raw.extend(r.get("data", []))
            paging = r.get("paging", {})
        except Exception:
            break
    return accounts_raw, raw


def fetch_report(date_preset="last_7d"):
    accounts_raw, raw_response = get_accounts()

    if not accounts_raw:
        raise RuntimeError(
            f"API retornou 0 contas. Resposta: {json.dumps(raw_response)[:800]}"
        )

    # Usa todas as contas exceto fechadas/desativadas
    accounts = [a for a in accounts_raw if a.get("account_status") not in (2, 101, 100)]
    if not accounts:
        accounts = accounts_raw

    report = {
        "gerado_em":   datetime.datetime.now().isoformat(),
        "date_preset": date_preset,
        "contas":      [],
        "erros":       [],
    }

    for acc in accounts:
        aid  = acc["id"]
        nome = acc["name"]
        try:
            camp_insights  = _get(f"{aid}/insights", {
                "fields": INSIGHT_FIELDS, "date_preset": date_preset, "level": "campaign",
            }).get("data", [])
            adset_insights = _get(f"{aid}/insights", {
                "fields": INSIGHT_FIELDS, "date_preset": date_preset, "level": "adset",
            }).get("data", [])
            ad_insights    = _get(f"{aid}/insights", {
                "fields": AD_INSIGHT_FIELDS, "date_preset": date_preset, "level": "ad",
            }).get("data", [])

            campaigns_raw  = _get_all(f"{aid}/campaigns", {
                "fields": "id,name,status,objective,daily_budget,lifetime_budget"
            })
            camp_map     = {c["id"]: c for c in campaigns_raw}
            creative_map = _fetch_ad_creatives(aid)

            camp_metrics = [
                _parse(ci, {
                    "campaign_id":   ci.get("campaign_id", ""),
                    "campaign_name": ci.get("campaign_name",
                                           camp_map.get(ci.get("campaign_id", ""), {}).get("name", "")),
                    "status":        camp_map.get(ci.get("campaign_id", ""), {}).get("status", ""),
                    "objetivo":      camp_map.get(ci.get("campaign_id", ""), {}).get("objective", ""),
                }) for ci in camp_insights
            ]
            adset_metrics = [
                _parse(r, {
                    "adset_id":      r.get("adset_id", ""),
                    "adset_name":    r.get("adset_name", ""),
                    "campaign_name": r.get("campaign_name", ""),
                }) for r in adset_insights
            ]
            ad_metrics = [
                _parse(r, {
                    "ad_id":         r.get("ad_id", ""),
                    "ad_name":       r.get("ad_name",
                                          creative_map.get(r.get("ad_id", ""), {}).get("ad_name", "")),
                    "campaign_name": r.get("campaign_name", ""),
                    "adset_name":    r.get("adset_name", ""),
                    "thumbnail_url": creative_map.get(r.get("ad_id", ""), {}).get("thumbnail_url", ""),
                    "creative_id":   creative_map.get(r.get("ad_id", ""), {}).get("creative_id", ""),
                }) for r in ad_insights
            ]

            t_gasto      = sum(m["gasto"]            for m in camp_metrics)
            t_compras    = sum(m["compras"]           for m in camp_metrics)
            t_receita    = sum(m["receita"]           for m in camp_metrics)
            t_alcance    = sum(m["alcance"]           for m in camp_metrics)
            t_impressoes = sum(m["impressoes"]        for m in camp_metrics)
            t_cliques    = sum(m["cliques_link"]      for m in camp_metrics)
            t_visitas_ig = sum(m["visitas_instagram"] for m in camp_metrics)
            t_conv       = sum(m["conv_mensagens"]    for m in camp_metrics)

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
                    "custo_por_mensagem": round(t_gasto / t_conv, 2)    if t_conv    > 0 else 0,
                    "compras":            t_compras,
                    "custo_por_compra":   round(t_gasto / t_compras, 2) if t_compras > 0 else 0,
                    "receita":            round(t_receita, 2),
                    "gasto":              round(t_gasto, 2),
                    "roas":               round(t_receita / t_gasto, 2) if t_gasto   > 0 else 0,
                },
                "campanhas": camp_metrics,
                "conjuntos": adset_metrics,
                "criativos": ad_metrics,
            })
        except Exception as e:
            report["erros"].append(f"{nome} ({aid}): {e}")

    # Salva cache em arquivo por período
    try:
        with open(_cache_path(date_preset), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        if date_preset == "last_7d":
            with open(os.path.join(CACHE_DIR, "report_cache.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # erro de escrita não deve quebrar o dashboard

    return report


def load_report(date_preset="last_7d"):
    """Carrega cache do período. Retorna None se não existir."""
    for path in [_cache_path(date_preset),
                 os.path.join(CACHE_DIR, "report_cache.json")]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("date_preset") == date_preset and data.get("contas"):
                    return data
            except Exception:
                continue
    return None


if __name__ == "__main__":
    preset = sys.argv[1] if len(sys.argv) > 1 else "last_7d"
    fetch_report(preset)
