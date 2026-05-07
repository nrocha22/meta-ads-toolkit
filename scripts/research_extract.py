#!/usr/bin/env python3
"""Extrae datos historicos de todas las campanas para investigacion."""

import json
import sys
from pathlib import Path
from helpers import run_meta, get_account, strip_account_flag

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent


def get_all_insights(campaign_id):
    """Get max-range insights for a campaign (API limit: 37 months)."""
    from datetime import datetime, timedelta
    # API limits to 37 months back
    earliest = (datetime.now() - timedelta(days=37 * 30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    data = run_meta(
        "insights", "get",
        "--campaign-id", campaign_id,
        "--since", earliest,
        "--until", today,
        "--fields", "spend,impressions,clicks,ctr,cpc,cpm,reach,frequency,conversions,cost_per_conversion",
    )
    if data.get("data"):
        return data["data"][0]
    return None


def main():
    args = strip_account_flag(sys.argv)
    acct = get_account()
    cur = acct["currency"]

    campaigns = run_meta("campaign", "list")

    print(f"\n  EXTRACCION DE DATOS — {acct['label']}")
    print(f"  Total campanas: {len(campaigns)}")
    print(f"{'='*100}\n")

    results = []

    for i, c in enumerate(campaigns):
        name = c["name"]
        cid = c["id"]
        status = c.get("effective_status", "?")
        objective = c.get("objective", "?")
        daily_budget = c.get("daily_budget")
        lifetime_budget = c.get("lifetime_budget")
        start = c.get("start_time", "?")[:10]

        sys.stderr.write(f"  [{i+1}/{len(campaigns)}] {name}...\n")

        insights = get_all_insights(cid)

        row = {
            "name": name,
            "id": cid,
            "status": status,
            "objective": objective,
            "daily_budget": int(daily_budget) / 100 if daily_budget else None,
            "lifetime_budget": int(lifetime_budget) / 100 if lifetime_budget else None,
            "start_date": start,
        }

        if insights:
            row["spend"] = float(insights.get("spend", 0))
            row["impressions"] = int(insights.get("impressions", 0))
            row["clicks"] = int(insights.get("clicks", 0))
            row["ctr"] = float(insights.get("ctr", 0))
            row["cpc"] = float(insights.get("cpc", 0))
            row["cpm"] = float(insights.get("cpm", 0))
            row["reach"] = int(insights.get("reach", 0))
            row["frequency"] = float(insights.get("frequency", 0))

            conversions = insights.get("conversions")
            if conversions:
                row["conversions"] = conversions
        else:
            row["spend"] = 0

        results.append(row)

    # Sort by spend descending
    results.sort(key=lambda x: x.get("spend", 0), reverse=True)

    # Print summary table
    print(f"  {'Campana':<35} {'Spend':>10} {'Impr':>10} {'Clicks':>8} {'CTR':>6} {'CPC':>6} {'Objetivo':<22} {'Inicio':<12} {'Status':<8}")
    print(f"  {'─'*35} {'─'*10} {'─'*10} {'─'*8} {'─'*6} {'─'*6} {'─'*22} {'─'*12} {'─'*8}")

    total_spend = 0
    for r in results:
        name = r["name"][:35]
        spend = r.get("spend", 0)
        total_spend += spend
        impr = r.get("impressions", 0)
        clicks = r.get("clicks", 0)
        ctr = r.get("ctr", 0)
        cpc = r.get("cpc", 0)
        objective = r.get("objective", "?")[:22]
        start = r.get("start_date", "?")
        status = r.get("status", "?")[:8]

        if spend > 0:
            print(f"  {name:<35} {cur}{spend:>9.2f} {impr:>10,} {clicks:>8,} {ctr:>5.2f}% {cur}{cpc:>5.2f} {objective:<22} {start:<12} {status}")
        else:
            print(f"  {name:<35} {'—':>10} {'—':>10} {'—':>8} {'—':>6} {'—':>6} {objective:<22} {start:<12} {status}")

    print(f"\n  TOTAL SPEND HISTORICO: {cur}{total_spend:,.2f}")

    # Print conversions detail
    print(f"\n\n  DETALLE DE CONVERSIONES")
    print(f"  {'='*80}")
    for r in results:
        convs = r.get("conversions")
        if convs:
            print(f"\n  {r['name']} (spend: {cur}{r['spend']:.2f})")
            for conv in convs:
                print(f"    {conv['action_type']}: {conv['value']}")

    # Save raw JSON
    output_file = PROJECT_DIR / "research" / f"{acct['label'].split()[-1].lower()}_raw.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    sys.stderr.write(f"\n  Datos guardados en {output_file}\n")


if __name__ == "__main__":
    main()
