#!/usr/bin/env python3
"""Comparar dos periodos consecutivos (no superpuestos) para campanas activas."""

import sys
from datetime import datetime, timedelta
from helpers import run_meta, get_account, strip_account_flag

PERIODS = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
}


def get_date_ranges(period_days):
    """Return two non-overlapping date ranges: current and previous."""
    today = datetime.now().date()
    current_end = today - timedelta(days=1)  # yesterday
    current_start = current_end - timedelta(days=period_days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_days - 1)
    return (
        (current_start.isoformat(), current_end.isoformat()),
        (previous_start.isoformat(), previous_end.isoformat()),
    )


def get_insights(campaign_id, since, until):
    data = run_meta(
        "insights", "get",
        "--campaign-id", campaign_id,
        "--since", since,
        "--until", until,
        "--fields", "spend,impressions,clicks,ctr,cpc,reach",
    )
    if data.get("data"):
        return data["data"][0]
    return None


def delta(current, previous):
    if previous == 0:
        return " new" if current > 0 else "   —"
    pct = ((current - previous) / previous) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:>3.0f}%"


def main():
    args = strip_account_flag(sys.argv)
    period = args[0] if args else "7d"
    acct = get_account()

    if period not in PERIODS:
        print(f"Uso: python report_compare.py [7d|14d|30d] --account <name>")
        sys.exit(1)

    days = PERIODS[period]
    (c_start, c_end), (p_start, p_end) = get_date_ranges(days)

    campaigns = run_meta("campaign", "list")
    active = [c for c in campaigns if c.get("effective_status") == "ACTIVE"]

    print(f"\n  COMPARACION — {acct['label']}")
    print(f"  Actual:   {c_start} → {c_end} ({days} dias)")
    print(f"  Anterior: {p_start} → {p_end} ({days} dias)")
    print(f"\n{'─'*100}")
    print(f"  {'Campana':<25} {'Spend':>14}  {'Impr':>14}  {'Clicks':>11}  {'CTR':>10}  {'CPC':>10}")
    print(f"  {'─'*25} {'─'*14}  {'─'*14}  {'─'*11}  {'─'*10}  {'─'*10}")

    cur = acct["currency"]
    t_curr = {"spend": 0, "impressions": 0, "clicks": 0}
    t_prev = {"spend": 0, "impressions": 0, "clicks": 0}

    for c in active:
        curr = get_insights(c["id"], c_start, c_end)
        prev = get_insights(c["id"], p_start, p_end)

        name = c["name"][:25]

        if not curr and not prev:
            print(f"  {name:<25} {'sin datos':>14}")
            continue

        c_spend = float(curr["spend"]) if curr else 0
        c_impr = int(curr["impressions"]) if curr else 0
        c_clicks = int(curr["clicks"]) if curr else 0
        c_ctr = float(curr["ctr"]) if curr else 0
        c_cpc = float(curr["cpc"]) if curr else 0

        p_spend = float(prev["spend"]) if prev else 0
        p_impr = int(prev["impressions"]) if prev else 0
        p_clicks = int(prev["clicks"]) if prev else 0
        p_ctr = float(prev["ctr"]) if prev else 0
        p_cpc = float(prev["cpc"]) if prev else 0

        t_curr["spend"] += c_spend
        t_curr["impressions"] += c_impr
        t_curr["clicks"] += c_clicks
        t_prev["spend"] += p_spend
        t_prev["impressions"] += p_impr
        t_prev["clicks"] += p_clicks

        print(f"  {name:<25} {cur}{c_spend:>7.2f} {delta(c_spend, p_spend)}  {c_impr:>8,} {delta(c_impr, p_impr)}  {c_clicks:>6,} {delta(c_clicks, p_clicks)}  {c_ctr:>5.2f}% {delta(c_ctr, p_ctr)}  {cur}{c_cpc:>5.2f} {delta(c_cpc, p_cpc)}")

    # Totals
    print(f"  {'─'*25} {'─'*14}  {'─'*14}  {'─'*11}  {'─'*10}  {'─'*10}")
    t_c_ctr = (t_curr["clicks"] / t_curr["impressions"] * 100) if t_curr["impressions"] else 0
    t_p_ctr = (t_prev["clicks"] / t_prev["impressions"] * 100) if t_prev["impressions"] else 0
    t_c_cpc = (t_curr["spend"] / t_curr["clicks"]) if t_curr["clicks"] else 0
    t_p_cpc = (t_prev["spend"] / t_prev["clicks"]) if t_prev["clicks"] else 0

    print(f"  {'TOTAL':<25} {cur}{t_curr['spend']:>7.2f} {delta(t_curr['spend'], t_prev['spend'])}  {t_curr['impressions']:>8,} {delta(t_curr['impressions'], t_prev['impressions'])}  {t_curr['clicks']:>6,} {delta(t_curr['clicks'], t_prev['clicks'])}  {t_c_ctr:>5.2f}% {delta(t_c_ctr, t_p_ctr)}  {cur}{t_c_cpc:>5.2f} {delta(t_c_cpc, t_p_cpc)}")
    print()


if __name__ == "__main__":
    main()
