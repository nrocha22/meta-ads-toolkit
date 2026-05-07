#!/usr/bin/env python3
"""Vista rapida de campanas activas con spend e insights."""

import sys
from helpers import run_meta, get_account, strip_account_flag


def get_active_campaigns():
    campaigns = run_meta("campaign", "list")
    return [c for c in campaigns if c.get("effective_status") == "ACTIVE"]


def get_insights(campaign_id, preset="last_7d"):
    data = run_meta(
        "insights", "get",
        "--campaign-id", campaign_id,
        "--date-preset", preset,
        "--fields", "spend,impressions,clicks,ctr,cpc,reach",
    )
    if data.get("data"):
        return data["data"][0]
    return None


def format_budget(campaign, cur):
    daily = campaign.get("daily_budget")
    lifetime = campaign.get("lifetime_budget")
    if daily:
        return f"{cur}{int(daily) / 100:.2f}/dia"
    if lifetime:
        return f"{cur}{int(lifetime) / 100:.2f} lifetime"
    return "sin budget"


def main():
    args = strip_account_flag(sys.argv)
    preset = args[0] if args else "last_7d"
    acct = get_account()

    campaigns = get_active_campaigns()
    if not campaigns:
        print("No hay campanas activas.")
        return

    print(f"\n{'='*80}")
    print(f"  {acct['label']} — Campanas Activas ({len(campaigns)})")
    print(f"  Periodo: {preset}")
    print(f"{'='*80}\n")

    cur = acct["currency"]
    total_spend = 0

    for c in campaigns:
        insights = get_insights(c["id"], preset)
        budget_str = format_budget(c, cur)

        print(f"  {c['name']}")
        print(f"  {'─'*60}")
        print(f"  Objetivo: {c.get('objective', '?'):<25} Budget: {budget_str}")

        if insights:
            spend = float(insights.get("spend", 0))
            total_spend += spend
            print(f"  Spend: {cur}{spend:.2f}    Impressions: {int(insights.get('impressions', 0)):,}    Reach: {int(insights.get('reach', 0)):,}")
            print(f"  Clicks: {int(insights.get('clicks', 0)):,}       CTR: {float(insights.get('ctr', 0)):.2f}%             CPC: {cur}{float(insights.get('cpc', 0)):.2f}")
        else:
            print("  Sin datos para este periodo.")
        print()

    print(f"{'─'*80}")
    print(f"  TOTAL SPEND: {cur}{total_spend:.2f}")
    print(f"{'─'*80}\n")


if __name__ == "__main__":
    main()
