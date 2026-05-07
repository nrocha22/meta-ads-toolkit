#!/usr/bin/env python3
"""Detalle de una campana con breakdowns por edad, genero, plataforma."""

import sys
from helpers import run_meta, get_account, strip_account_flag


def get_insights(campaign_id, preset, breakdown=None):
    fields = "spend,impressions,clicks,ctr,cpc,cpm,reach,frequency"
    if not breakdown:
        fields += ",conversions,cost_per_conversion"
    args = [
        "insights", "get",
        "--campaign-id", campaign_id,
        "--date-preset", preset,
        "--fields", fields,
    ]
    if breakdown:
        args.extend(["--breakdown", breakdown])
    data = run_meta(*args)
    return data.get("data", [])


def print_breakdown(title, rows, key_field, cur="$"):
    if not rows:
        print(f"\n  {title}: Sin datos\n")
        return

    print(f"\n  {title}")
    print(f"  {'─'*70}")
    print(f"  {key_field:<20} {'Spend':>8} {'Impr':>8} {'Clicks':>7} {'CTR':>6} {'CPC':>6}")
    print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*7} {'─'*6} {'─'*6}")

    for r in rows:
        key = r.get(key_field, "?")[:20]
        spend = float(r.get("spend", 0))
        impressions = int(r.get("impressions", 0))
        clicks = int(r.get("clicks", 0))
        ctr = float(r.get("ctr", 0))
        cpc = float(r.get("cpc", 0))
        print(f"  {key:<20} {cur}{spend:>7.2f} {impressions:>8,} {clicks:>7,} {ctr:>5.2f}% {cur}{cpc:>5.2f}")


def main():
    args = strip_account_flag(sys.argv)

    if not args:
        print("Uso: python report_campaign.py <CAMPAIGN_ID> [date_preset]")
        print("     python report_campaign.py --account mibrand <CAMPAIGN_ID> [date_preset]")
        print()
        acct = get_account()
        print(f"  Campanas en {acct['label']}:")
        print(f"  {'─'*80}")
        print(f"  {'ID':<22} {'Status':<10} {'Objetivo':<22} Nombre")
        print(f"  {'─'*22} {'─'*10} {'─'*22} {'─'*30}")
        campaigns = run_meta("campaign", "list")
        for c in campaigns:
            status = c.get("effective_status", "?")
            objective = c.get("objective", "?")
            print(f"  {c['id']:<22} {status:<10} {objective:<22} {c['name']}")
        sys.exit(0)

    campaign_id = args[0]
    from helpers import normalize_period
    preset = normalize_period(args[1]) if len(args) > 1 else "last_30d"
    acct = get_account()
    cur = acct["currency"]

    # Campaign info
    campaigns = run_meta("campaign", "list")
    info = next((c for c in campaigns if c["id"] == campaign_id), None)
    name = info["name"] if info else campaign_id
    objective = info.get("objective", "?") if info else "?"
    budget = info.get("daily_budget") if info else None
    budget_str = f"{cur}{int(budget)/100:.2f}/dia" if budget else "sin daily budget"

    print(f"\n{'='*70}")
    print(f"  REPORTE DE CAMPANA: {name}")
    print(f"  Objetivo: {objective}    Budget: {budget_str}")
    print(f"  Periodo: {preset}")
    print(f"{'='*70}")

    # Overall
    overall = get_insights(campaign_id, preset)
    if not overall:
        print("\n  Sin datos para este periodo.\n")
        return

    r = overall[0]
    spend = float(r.get("spend", 0))
    impressions = int(r.get("impressions", 0))
    clicks = int(r.get("clicks", 0))
    reach = int(r.get("reach", 0))
    frequency = float(r.get("frequency", 0))
    ctr = float(r.get("ctr", 0))
    cpc = float(r.get("cpc", 0))
    cpm = float(r.get("cpm", 0))

    print(f"\n  Resumen")
    print(f"  {'─'*50}")
    print(f"  Spend: {cur}{spend:.2f}          Reach: {reach:,}")
    print(f"  Impressions: {impressions:,}   Frequency: {frequency:.1f}")
    print(f"  Clicks: {clicks:,}            CTR: {ctr:.2f}%")
    print(f"  CPC: {cur}{cpc:.2f}              CPM: {cur}{cpm:.2f}")

    # Conversions (array of {action_type, value})
    conversions = r.get("conversions")
    cost_per_conv = r.get("cost_per_conversion")
    if conversions:
        print(f"\n  Conversiones")
        print(f"  {'─'*50}")
        cost_map = {}
        if cost_per_conv:
            cost_map = {c["action_type"]: float(c["value"]) for c in cost_per_conv}
        for conv in conversions:
            action = conv["action_type"]
            value = conv["value"]
            cost = cost_map.get(action)
            cost_str = f"  ({cur}{cost:.2f}/conv)" if cost else ""
            print(f"  {action}: {value}{cost_str}")

    # Breakdowns
    age_data = get_insights(campaign_id, preset, "age")
    print_breakdown("Por Edad", age_data, "age", cur)

    gender_data = get_insights(campaign_id, preset, "gender")
    gender_map = {"male": "Hombres", "female": "Mujeres", "unknown": "Desconocido"}
    for r in gender_data:
        r["gender"] = gender_map.get(r.get("gender", ""), r.get("gender", ""))
    print_breakdown("Por Genero", gender_data, "gender", cur)

    platform_data = get_insights(campaign_id, preset, "publisher_platform")
    print_breakdown("Por Plataforma", platform_data, "publisher_platform", cur)

    device_data = get_insights(campaign_id, preset, "device_platform")
    print_breakdown("Por Dispositivo", device_data, "device_platform", cur)

    print()


if __name__ == "__main__":
    main()
