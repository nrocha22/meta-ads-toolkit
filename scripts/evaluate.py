#!/usr/bin/env python3
"""Evalúa desempeño de ads activos y genera ranking con recomendaciones."""

import json
import sys
import time
from helpers import run_meta, get_account, get_thresholds, normalize_period, ACCOUNTS
from _cache import cache_get, cache_set

# Mapeo de acción de conversión por tipo de campaña
LEAD_ACTIONS = ["offsite_conversion.fb_pixel_lead", "lead", "onsite_conversion.lead_grouped"]
WA_ACTIONS = ["onsite_conversion.messaging_first_reply", "messaging_first_reply"]

# Estado de cache (configurado por main, leído por get_*_insights)
_CACHE_ENABLED = True
_CACHE_TTL = 900  # 15 minutos default


def _cached_run_meta(cache_key: str, *args):
    """Wrapper para run_meta con cache opcional."""
    if _CACHE_ENABLED:
        cached, age = cache_get(cache_key, _CACHE_TTL)
        if cached is not None:
            sys.stderr.write(f"  ⚠ cache hit (hace {age}s) — pasa --no-cache para refrescar\n")
            return cached
    data = run_meta(*args)
    if _CACHE_ENABLED:
        cache_set(cache_key, data)
    return data


def get_active_campaigns():
    campaigns = run_meta("campaign", "list")
    return [c for c in campaigns if c.get("effective_status") == "ACTIVE"]


def get_campaign_insights(campaign_id, period, account_key):
    """Insights a nivel campaña — 1 call para saber si tiene spend."""
    key = f"campaign_insights:{account_key}:{campaign_id}:{period}"
    data = _cached_run_meta(
        key,
        "insights", "get",
        "--campaign-id", campaign_id,
        "--date-preset", period,
        "--fields", "spend",
    )
    if data.get("data"):
        return float(data["data"][0].get("spend", 0))
    return 0


def get_active_ads(campaign_id):
    ads = run_meta("ad", "list", campaign_id)
    return [a for a in ads if a.get("effective_status") == "ACTIVE"]


def get_ad_insights(ad_id, period, account_key):
    key = f"ad_insights:{account_key}:{ad_id}:{period}"
    data = _cached_run_meta(
        key,
        "insights", "get",
        "--ad-id", ad_id,
        "--date-preset", period,
        "--fields", "spend,impressions,clicks,ctr,cpc,actions",
    )
    if data.get("data"):
        return data["data"][0]
    return None


def extract_conversions(insights):
    """Extrae leads y WA replies del campo actions."""
    leads = 0
    wa_replies = 0
    actions = insights.get("actions") if insights else None
    if not actions:
        return leads, wa_replies
    for a in actions:
        action = a.get("action_type", "")
        value = int(a.get("value", 0))
        if action in LEAD_ACTIONS:
            leads = max(leads, value)  # max porque lead y fb_pixel_lead son el mismo evento
        elif action in WA_ACTIONS:
            wa_replies = max(wa_replies, value)
    return leads, wa_replies


def score_ads(ads_data, thresholds):
    """Calcula score relativo basado en CPL vs promedio + volumen de conversiones."""

    # Calcular promedios de campaña
    total_conversions = sum(a["leads"] + a["wa_replies"] for a in ads_data)
    total_spend = sum(a["spend"] for a in ads_data)
    avg_cpl = total_spend / total_conversions if total_conversions > 0 else None
    avg_conversions = total_conversions / len(ads_data) if ads_data else 0

    # Pre-calcular CTR promedio
    avg_ctr = sum(a["ctr"] for a in ads_data) / len(ads_data) if ads_data else 0

    for ad in ads_data:
        conversions = ad["leads"] + ad["wa_replies"]
        ad["conversions"] = conversions
        ad["cpl"] = ad["spend"] / conversions if conversions > 0 else None

        # Scoring: combina eficiencia (CPL) + volumen (conversiones)
        if avg_cpl and ad["cpl"] is not None:
            efficiency_ratio = avg_cpl / ad["cpl"]  # >1 = mejor CPL que promedio
            volume_ratio = conversions / avg_conversions if avg_conversions > 0 else 0  # >1 = más volumen que promedio

            # Score compuesto: eficiencia pesa 60%, volumen 40%
            composite = (efficiency_ratio * 0.6) + (volume_ratio * 0.4)

            if composite >= 1.3:
                ad["score"] = 3
                ad["status_rec"] = "TOP"
            elif composite >= 0.7:
                ad["score"] = 2
                ad["status_rec"] = "OK"
            else:
                ad["score"] = 1
                ad["status_rec"] = "WATCH"
        elif conversions == 0 and ad["spend"] >= thresholds["min_spend_for_flag"]:
            ad["score"] = 0
            ad["status_rec"] = "PAUSE?"
        elif conversions == 0:
            ad["score"] = 1
            ad["status_rec"] = "LOW DATA"
        else:
            ad["score"] = 2
            ad["status_rec"] = "OK"

        # CTR flag
        if ad["ctr"] < avg_ctr * 0.5 and ad["spend"] > 0:
            if ad["status_rec"] not in ("PAUSE?",):
                ad["status_rec"] = "FATIGUE?"

    return ads_data, avg_cpl


def print_table(campaign_name, ads_data, avg_cpl, currency):
    """Imprime tabla visual a stderr."""
    stars = {0: "---", 1: "*  ", 2: "** ", 3: "***"}
    total_conversions = sum(a["conversions"] for a in ads_data)

    sys.stderr.write(f"\n{'='*90}\n")
    sys.stderr.write(f"  {campaign_name} | Avg CPL: {currency}{avg_cpl:.2f} | Conv: {total_conversions} | Ads: {len(ads_data)}\n" if avg_cpl else
                     f"  {campaign_name} | Avg CPL: N/A | Conv: {total_conversions} | Ads: {len(ads_data)}\n")
    sys.stderr.write(f"{'='*90}\n")
    sys.stderr.write(f"  {'#':<3} {'AD NAME':<26} {'SPEND':>8} {'CONV':>5} {'%VOL':>5} {'CPL':>9} {'CTR':>6} {'SC':>3}  {'REC'}\n")
    sys.stderr.write(f"  {'─'*3} {'─'*26} {'─'*8} {'─'*5} {'─'*5} {'─'*9} {'─'*6} {'─'*3}  {'─'*8}\n")

    for i, ad in enumerate(ads_data, 1):
        cpl_str = f"{currency}{ad['cpl']:.2f}" if ad["cpl"] else "N/A"
        vol_pct = f"{ad['conversions']/total_conversions*100:.0f}%" if total_conversions > 0 else "-"
        sys.stderr.write(
            f"  {i:<3} {ad['name']:<26} {currency}{ad['spend']:>7.0f} {ad['conversions']:>5} "
            f"{vol_pct:>5} {cpl_str:>9} {ad['ctr']:>5.1f}% {stars[ad['score']]:>3}  {ad['status_rec']}\n"
        )

    pause_candidates = [a for a in ads_data if a["status_rec"] in ("PAUSE?", "FATIGUE?")]
    if pause_candidates:
        sys.stderr.write(f"\n  Candidatos a pausa:\n")
        for a in pause_candidates:
            sys.stderr.write(f"    - {a['name']} ({a['ad_id']}) — {a['status_rec']}\n")
    sys.stderr.write("\n")


def _parse_args(argv):
    """Extrae --no-cache, --cache-ttl. Devuelve (positional_args, no_cache, ttl, account_key)."""
    args = []
    no_cache = False
    ttl = 900
    account_key = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-cache":
            no_cache = True
        elif a == "--cache-ttl" and i + 1 < len(argv):
            ttl = int(argv[i + 1])
            i += 1
        elif a == "--account" and i + 1 < len(argv):
            account_key = argv[i + 1].lower()
            i += 1
        else:
            args.append(a)
        i += 1
    return args, no_cache, ttl, account_key


def main():
    global _CACHE_ENABLED, _CACHE_TTL
    args, no_cache, ttl, account_key = _parse_args(sys.argv[1:])
    _CACHE_ENABLED = not no_cache
    _CACHE_TTL = ttl

    acct = get_account()
    thresholds = get_thresholds()
    if account_key is None:
        # derivar el key efectivo para el cache namespace
        for k, v in ACCOUNTS.items():
            if v["ad_account_id"] == acct["ad_account_id"]:
                account_key = k
                break
        account_key = account_key or "default"
    currency = acct["currency"]
    period = normalize_period(args[0]) if args else "last_14d"

    sys.stderr.write(f"Evaluando ads activos — {acct['label']} ({period})...\n")
    if _CACHE_ENABLED:
        sys.stderr.write(f"  Cache: ON (TTL {_CACHE_TTL}s)\n")
    else:
        sys.stderr.write(f"  Cache: OFF (--no-cache)\n")

    campaigns = get_active_campaigns()
    if not campaigns:
        sys.stderr.write("No hay campañas activas.\n")
        sys.exit(2)

    all_results = []

    # Fase 1: filtrar campañas con spend (1 call por campaña, barato)
    sys.stderr.write(f"  Checkeando spend por campaña...\n")
    campaigns_with_spend = []
    for campaign in campaigns:
        campaign_id = campaign["id"]
        campaign_name = campaign.get("name", campaign_id)
        spend = get_campaign_insights(campaign_id, period, account_key)
        if spend > 0:
            campaigns_with_spend.append(campaign)
            sys.stderr.write(f"    {campaign_name}: {currency}{spend:.0f}\n")
        else:
            sys.stderr.write(f"    {campaign_name}: $0, skip\n")
        time.sleep(0.3)

    if not campaigns_with_spend:
        sys.stderr.write("No hay campañas con spend en el período.\n")
        sys.exit(2)

    sys.stderr.write(f"\n  Evaluando {len(campaigns_with_spend)} campaña(s) con actividad...\n\n")

    # Fase 2: solo para campañas con spend, obtener insights por ad
    for campaign in campaigns_with_spend:
        campaign_id = campaign["id"]
        campaign_name = campaign.get("name", campaign_id)
        campaign_objective = campaign.get("objective", "")
        ads = get_active_ads(campaign_id)

        if not ads:
            sys.stderr.write(f"  {campaign_name}: sin ads activos, skip\n")
            continue

        ads_data = []
        for i, ad in enumerate(ads):
            sys.stderr.write(f"  [{i+1}/{len(ads)}] {ad.get('name', '?')}...\r")
            insights = get_ad_insights(ad["id"], period, account_key)
            leads, wa_replies = extract_conversions(insights)

            ads_data.append({
                "ad_id": ad["id"],
                "name": ad.get("name", "?"),
                "spend": float(insights.get("spend", 0)) if insights else 0,
                "impressions": int(insights.get("impressions", 0)) if insights else 0,
                "clicks": int(insights.get("clicks", 0)) if insights else 0,
                "ctr": float(insights.get("ctr", 0)) if insights else 0,
                "cpc": float(insights.get("cpc", 0)) if insights else 0,
                "leads": leads,
                "wa_replies": wa_replies,
            })
            time.sleep(0.5)  # Rate limiting

        # Filtrar ads sin spend
        ads_with_spend = [a for a in ads_data if a["spend"] > 0]
        if not ads_with_spend:
            continue
        ads_data = ads_with_spend

        # Score y ordenar (desempate por conversiones desc, luego CPL asc)
        # Solo score relativo si hay >1 ad (con 1 ad no hay referencia)
        if len(ads_data) == 1:
            ad = ads_data[0]
            ad["conversions"] = ad["leads"] + ad["wa_replies"]
            ad["cpl"] = ad["spend"] / ad["conversions"] if ad["conversions"] > 0 else None
            ad["score"] = 2
            ad["status_rec"] = "SOLO"
            avg_cpl = ad["cpl"]
        else:
            ads_data, avg_cpl = score_ads(ads_data, thresholds)
        ads_data.sort(key=lambda x: (-x["score"], -x["conversions"], x["cpl"] or 9999))

        print_table(campaign_name, ads_data, avg_cpl, currency)

        all_results.append({
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "avg_cpl": avg_cpl,
            "period": period,
            "ads": ads_data,
        })

    # JSON a stdout (para agentes/pipe)
    print(json.dumps(all_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
