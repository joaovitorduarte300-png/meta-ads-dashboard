"""
Gerador de relatórios Meta Ads — busca dados e salva JSON/cache para o dashboard.
Executado toda segunda-feira às 08h ou sob demanda.
"""
import sys, json, os, datetime, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

ACCESS_TOKEN = "EAAW8pPurJVQBQ5xd4AVeZBanXVxrVOhPYQCTH4p77P3d41RHBWZCRVopA3WhGbpqesokkGhNlXTZBZA3vexc4SF9Ol93IluKegPV7ZCTa0xaADMuX33wCWNCjlNoDC7sTVPeRgQzZBpAynKZBZANEpBeOXhTyMZCZCW4ZAzmMaluzHT2UG7INA939CPYx0xqYHtz0mcr3sYpZA03j6k7GgZDZD"
BASE_URL   = "https://graph.facebook.com/v21.0"
_CACHE_DIR  = os.path.dirname(__file__)
CACHE_FILE  = os.path.join(_CACHE_DIR, "report_cache.json")  # mantido para compatibilidade

def _cache_path(preset):
    return os.path.join(_CACHE_DIR, f"report_cache_{preset}.json")

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


def _ig_date_range(date_preset):
    """Converte date_preset para timestamps Unix para a Instagram Insights API."""
    now = datetime.datetime.now()
    days_map = {
        "today": 1, "yesterday": 2, "last_7d": 7, "last_14d": 14,
        "last_30d": 30, "this_month": max(1, now.day - 1), "last_month": 30, "maximum": 90,
    }
    days = days_map.get(date_preset, 7)
    since = int((now - datetime.timedelta(days=days)).timestamp())
    until = int(now.timestamp())
    return since, until, days


def _fetch_instagram_organic(ig_user_id, date_preset="last_7d"):
    """Busca dados orgânicos do Instagram: perfil, insights, mídia — em paralelo."""
    try:
        since, until, days = _ig_date_range(date_preset)

        def _get_profile():
            return _get(ig_user_id, {
                "fields": "followers_count,media_count,name,username,profile_picture_url,biography"
            })

        def _get_insights():
            try:
                r = _get(f"{ig_user_id}/insights", {
                    "metric": "reach,impressions,profile_views,follower_count",
                    "period": "day", "since": since, "until": until,
                })
                return r.get("data", [])
            except Exception:
                return []

        def _get_media():
            try:
                return _get_all(f"{ig_user_id}/media", {
                    "fields": "id,media_type,timestamp,like_count,comments_count,"
                              "thumbnail_url,media_url,permalink,caption",
                    "limit": 50,
                })
            except Exception:
                return []

        def _get_stories():
            try:
                return _get_all(f"{ig_user_id}/stories", {
                    "fields": "id,media_type,timestamp,thumbnail_url,media_url",
                })
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=4) as ex:
            f_profile  = ex.submit(_get_profile)
            f_insights = ex.submit(_get_insights)
            f_media    = ex.submit(_get_media)
            f_stories  = ex.submit(_get_stories)
            profile   = f_profile.result()
            ai_data   = f_insights.result()
            media_raw = f_media.result()
            stories   = f_stories.result()

        if "error" in profile or "followers_count" not in profile:
            return None

        def _sum_ig(name):
            item = next((i for i in ai_data if i.get("name") == name), None)
            return sum(v.get("value", 0) for v in item.get("values", [])) if item else 0

        follower_delta = 0
        fc = next((i for i in ai_data if i.get("name") == "follower_count"), None)
        if fc:
            vals = fc.get("values", [])
            if len(vals) >= 2:
                follower_delta = vals[-1].get("value", 0) - vals[0].get("value", 0)

        for m in media_raw:
            m["engagement"] = (m.get("like_count") or 0) + (m.get("comments_count") or 0)
        media_sorted = sorted(media_raw, key=lambda x: x.get("engagement", 0), reverse=True)

        since_dt = datetime.datetime.now() - datetime.timedelta(days=days)
        posts_periodo = 0
        for m in media_raw:
            try:
                ts = datetime.datetime.fromisoformat(
                    m.get("timestamp", "").replace("Z", "+00:00")
                ).replace(tzinfo=None)
                if ts >= since_dt:
                    posts_periodo += 1
            except Exception:
                pass

        reels     = [m for m in media_sorted if m.get("media_type") == "VIDEO"][:10]
        posts     = [m for m in media_sorted if m.get("media_type") == "IMAGE"][:10]
        carroseis = [m for m in media_sorted if m.get("media_type") == "CAROUSEL_ALBUM"][:10]

        return {
            "ig_user_id":           ig_user_id,
            "username":             profile.get("username", ""),
            "name":                 profile.get("name", ""),
            "followers":            profile.get("followers_count", 0),
            "media_count":          profile.get("media_count", 0),
            "profile_picture":      profile.get("profile_picture_url", ""),
            "biography":            profile.get("biography", ""),
            "follower_delta":       follower_delta,
            "alcance_organico":     _sum_ig("reach"),
            "impressoes_organicas": _sum_ig("impressions"),
            "visitas_perfil":       _sum_ig("profile_views"),
            "posts_no_periodo":     posts_periodo,
            "reels":                reels,
            "posts":                posts,
            "carroseis":            carroseis,
            "stories":              stories,
            "top_media":            media_sorted[:6],
        }
    except Exception:
        return None


def _fetch_ig_for_account(aid, date_preset):
    """Descobre a conta Instagram ligada ao ad account e busca dados orgânicos."""
    try:
        ig_id = None
        ig_accs = _get_all(f"{aid}/connected_instagram_accounts", {"fields": "id,username,name"})
        if ig_accs:
            ig_id = ig_accs[0]["id"]
        if not ig_id:
            acc_info = _get(aid, {"fields": "business"})
            biz = acc_info.get("business", {})
            biz_id = biz.get("id") if biz else None
            if biz_id:
                ig_biz = _get_all(f"{biz_id}/instagram_business_accounts", {"fields": "id,username,name"})
                if ig_biz:
                    ig_id = ig_biz[0]["id"]
        return _fetch_instagram_organic(ig_id, date_preset) if ig_id else None
    except Exception:
        return None


def _fetch_account(acc, date_preset):
    """Busca todos os dados de uma única conta de anúncios — paralelizado internamente."""
    aid  = acc["id"]
    nome = acc["name"]

    with ThreadPoolExecutor(max_workers=6) as ex:
        f_camp      = ex.submit(_get, f"{aid}/insights", {
            "fields": INSIGHT_FIELDS, "date_preset": date_preset, "level": "campaign"})
        f_adset     = ex.submit(_get, f"{aid}/insights", {
            "fields": INSIGHT_FIELDS, "date_preset": date_preset, "level": "adset"})
        f_ad        = ex.submit(_get, f"{aid}/insights", {
            "fields": AD_INSIGHT_FIELDS, "date_preset": date_preset, "level": "ad"})
        f_campaigns = ex.submit(_get_all, f"{aid}/campaigns", {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget"})
        f_creatives = ex.submit(_fetch_ad_creatives, aid)
        f_ig        = ex.submit(_fetch_ig_for_account, aid, date_preset)

        camp_insights  = f_camp.result().get("data", [])
        adset_insights = f_adset.result().get("data", [])
        ad_insights    = f_ad.result().get("data", [])
        campaigns_raw  = f_campaigns.result()
        creative_map   = f_creatives.result()
        ig_organic     = f_ig.result()

    camp_map = {c["id"]: c for c in campaigns_raw}

    camp_metrics = []
    for ci in camp_insights:
        cid  = ci.get("campaign_id", "")
        meta = camp_map.get(cid, {})
        camp_metrics.append(_parse(ci, {
            "campaign_id":   cid,
            "campaign_name": ci.get("campaign_name", meta.get("name", "")),
            "status":        meta.get("status", ""),
            "objetivo":      meta.get("objective", ""),
        }))

    adset_metrics = [_parse(r, {
        "adset_id":      r.get("adset_id", ""),
        "adset_name":    r.get("adset_name", ""),
        "campaign_name": r.get("campaign_name", ""),
    }) for r in adset_insights]

    ad_metrics = []
    for ad_row in ad_insights:
        ad_id = ad_row.get("ad_id", "")
        info  = creative_map.get(ad_id, {})
        ad_metrics.append(_parse(ad_row, {
            "ad_id":         ad_id,
            "ad_name":       ad_row.get("ad_name", info.get("ad_name", "")),
            "campaign_name": ad_row.get("campaign_name", ""),
            "adset_name":    ad_row.get("adset_name", ""),
            "thumbnail_url": info.get("thumbnail_url", ""),
            "creative_id":   info.get("creative_id", ""),
        }))

    t_gasto      = sum(m["gasto"]            for m in camp_metrics)
    t_compras    = sum(m["compras"]           for m in camp_metrics)
    t_receita    = sum(m["receita"]           for m in camp_metrics)
    t_alcance    = sum(m["alcance"]           for m in camp_metrics)
    t_impressoes = sum(m["impressoes"]        for m in camp_metrics)
    t_cliques    = sum(m["cliques_link"]      for m in camp_metrics)
    t_visitas_ig = sum(m["visitas_instagram"] for m in camp_metrics)
    t_conv       = sum(m["conv_mensagens"]    for m in camp_metrics)

    return {
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
        "campanhas":          camp_metrics,
        "conjuntos":          adset_metrics,
        "criativos":          ad_metrics,
        "instagram_organico": ig_organic,
    }


def fetch_report(date_preset="last_7d"):
    accounts_raw = _get_all("me/adaccounts", {
        "fields": "id,name,account_status,currency,amount_spent,balance"
    })
    accounts = [a for a in accounts_raw if a.get("account_status") == 1]

    contas = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_account, acc, date_preset): acc["name"] for acc in accounts}
        for future in as_completed(futures):
            try:
                contas.append(future.result())
            except Exception:
                pass

    contas.sort(key=lambda x: x["nome"])

    report = {
        "gerado_em":   datetime.datetime.now().isoformat(),
        "date_preset": date_preset,
        "contas":      contas,
    }

    # Salva cache por período E o cache principal (last_7d)
    per_period_path = _cache_path(date_preset)
    with open(per_period_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if date_preset == "last_7d":
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def load_report(preset=None):
    """Carrega cache do disco.
    Se `preset` for fornecido, retorna APENAS o cache daquele período (ou None).
    Sem preset, retorna o cache principal (last_7d).
    """
    if preset:
        path = _cache_path(preset)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Garante que o arquivo é realmente do período certo
                    if data.get("date_preset") == preset:
                        return data
            except Exception:
                pass
        return None  # Não faz fallback — evita mostrar dados do período errado
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


if __name__ == "__main__":
    preset = sys.argv[1] if len(sys.argv) > 1 else "last_7d"
    fetch_report(preset)
