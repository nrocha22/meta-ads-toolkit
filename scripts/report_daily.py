#!/usr/bin/env python3
"""Reporte diario: metricas por campana activa con totales."""

import sys
from datetime import datetime
from helpers import run_meta, get_account, strip_account_flag


def get_insights_for_campaign(campaign_id, preset):
    data = run_meta(
        "insights", "get",
        "--campaign-id", campaign_id,
        "--date-preset", preset,
        "--fields", "spend,impressions,clicks,ctr,cpc,cpm,reach,frequency",
    )
    if data.get("data"):
        return data["data"][0]
    return None


def main():
    args = strip_account_flag(sys.argv)
    from helpers import normalize_period
    preset = normalize_period(args[0]) if args else "yesterday"
    acct = get_account()

    campaigns = run_meta("campaign", "list")
    active = [c for c in campaigns if c.get("effective_status") == "ACTIVE"]

    print(f"\n  REPORTE DIARIO — {acct['label']}")
    print(f"  Generado: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Periodo: {preset}")
    print(f"  Campanas activas: {len(active)}")
    print(f"\n{'─'*90}")

    print(f"  {'Campana':<30} {'Spend':>8} {'Impr':>8} {'Clicks':>7} {'CTR':>6} {'CPC':>6} {'CPM':>6} {'Reach':>8}")
    print(f"  {'─'*30} {'─'*8} {'─'*8} {'─'*7} {'─'*6} {'─'*6} {'─'*6} {'─'*8}")

    cur = acct["currency"]
    totals = {"spend": 0, "impressions": 0, "clicks": 0, "reach": 0}

    for c in active:
        insights = get_insights_for_campaign(c["id"], preset)
        name = c["name"][:30]

        if not insights:
            print(f"  {name:<30} {'—':>8} {'—':>8} {'—':>7} {'—':>6} {'—':>6} {'—':>6} {'—':>8}")
            continue

        spend = float(insights.get("spend", 0))
        impressions = int(insights.get("impressions", 0))
        clicks = int(insights.get("clicks", 0))
        ctr = float(insights.get("ctr", 0))
        cpc = float(insights.get("cpc", 0))
        cpm = float(insights.get("cpm", 0))
        reach = int(insights.get("reach", 0))

        totals["spend"] += spend
        totals["impressions"] += impressions
        totals["clicks"] += clicks
        totals["reach"] += reach

        print(f"  {name:<30} {cur}{spend:>7.2f} {impressions:>8,} {clicks:>7,} {ctr:>5.2f}% {cur}{cpc:>5.2f} {cur}{cpm:>5.2f} {reach:>8,}")

    total_ctr = (totals["clicks"] / totals["impressions"] * 100) if totals["impressions"] else 0
    total_cpc = (totals["spend"] / totals["clicks"]) if totals["clicks"] else 0
    total_cpm = (totals["spend"] / totals["impressions"] * 1000) if totals["impressions"] else 0

    print(f"  {'─'*30} {'─'*8} {'─'*8} {'─'*7} {'─'*6} {'─'*6} {'─'*6} {'─'*8}")
    print(f"  {'TOTAL':<30} {cur}{totals['spend']:>7.2f} {totals['impressions']:>8,} {totals['clicks']:>7,} {total_ctr:>5.2f}% {cur}{total_cpc:>5.2f} {cur}{total_cpm:>5.2f} {totals['reach']:>8,}")
    print()


if __name__ == "__main__":
    main()
