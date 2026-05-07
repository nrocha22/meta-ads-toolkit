#!/usr/bin/env python3
"""Timeline mensual con eventos de conversión correctos y métricas de WhatsApp."""

import json
import sys
from datetime import datetime, timedelta
from helpers import run_meta, get_account, strip_account_flag


def extract_action(actions, action_type):
    """Extract a single action value from the actions array."""
    for a in actions:
        if a["action_type"] == action_type:
            return int(a["value"])
    return 0


def main():
    args = strip_account_flag(sys.argv)
    acct = get_account()
    cur = acct["currency"]

    if not args:
        print("Uso: python research_timeline.py <CAMPAIGN_ID> [CAMPAIGN_ID...]")
        sys.exit(0)

    earliest = (datetime.now() - timedelta(days=37 * 30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    for campaign_id in args:
        campaigns = run_meta("campaign", "list")
        info = next((c for c in campaigns if c["id"] == campaign_id), {})
        name = info.get("name", campaign_id)
        status = info.get("effective_status", "?")
        objective = info.get("objective", "?")

        data = run_meta(
            "insights", "get",
            "--campaign-id", campaign_id,
            "--since", earliest, "--until", today,
            "--time-increment", "monthly",
            "--fields", "spend,impressions,clicks,actions",
        )

        rows = data.get("data", [])
        active_rows = [r for r in rows if float(r.get("spend", 0)) > 0]

        if not active_rows:
            print(f"\n  {name} [{status}]: Sin datos en los últimos 37 meses\n")
            continue

        first_month = active_rows[0]["date_start"][:7]
        last_month = active_rows[-1]["date_start"][:7]
        total_spend = sum(float(r.get("spend", 0)) for r in active_rows)

        print(f"\n{'='*100}")
        print(f"  {name} [{status}]")
        print(f"  Objetivo: {objective}")
        print(f"  Corrió: {first_month} → {last_month} ({len(active_rows)} meses)")
        print(f"{'='*100}")

        # Header
        print(f"  {'Mes':<10} {'Spend':>10} {'Clicks':>8} │ {'Leads':>6} {'$/Lead':>8} │ {'WA Conv':>8} {'WA Reply':>8} {'WA Depth3':>9}")
        print(f"  {'─'*10} {'─'*10} {'─'*8} │ {'─'*6} {'─'*8} │ {'─'*8} {'─'*8} {'─'*9}")

        totals = {
            "spend": 0, "clicks": 0,
            "leads": 0, "wa_conv": 0, "wa_reply": 0, "wa_depth3": 0,
        }

        for r in active_rows:
            month = r["date_start"][:7]
            spend = float(r.get("spend", 0))
            clicks = int(r.get("clicks", 0))
            actions = r.get("actions", [])

            # Web leads — try multiple event names
            leads = (
                extract_action(actions, "offsite_conversion.fb_pixel_lead")
                or extract_action(actions, "lead")
                or extract_action(actions, "onsite_web_lead")
            )

            # WhatsApp metrics
            wa_conv = extract_action(actions, "onsite_conversion.messaging_conversation_started_7d")
            wa_reply = extract_action(actions, "onsite_conversion.messaging_first_reply")
            wa_depth3 = extract_action(actions, "onsite_conversion.messaging_user_depth_3_message_send")

            cost_per_lead = spend / leads if leads > 0 else 0

            totals["spend"] += spend
            totals["clicks"] += clicks
            totals["leads"] += leads
            totals["wa_conv"] += wa_conv
            totals["wa_reply"] += wa_reply
            totals["wa_depth3"] += wa_depth3

            leads_str = str(leads) if leads > 0 else "—"
            cpl_str = f"{cur}{cost_per_lead:.2f}" if leads > 0 else "—"
            wa_conv_str = str(wa_conv) if wa_conv > 0 else "—"
            wa_reply_str = str(wa_reply) if wa_reply > 0 else "—"
            wa_d3_str = str(wa_depth3) if wa_depth3 > 0 else "—"

            print(f"  {month:<10} {cur}{spend:>9.2f} {clicks:>8,} │ {leads_str:>6} {cpl_str:>8} │ {wa_conv_str:>8} {wa_reply_str:>8} {wa_d3_str:>9}")

        # Totals
        t_cpl = totals["spend"] / totals["leads"] if totals["leads"] > 0 else 0
        print(f"  {'─'*10} {'─'*10} {'─'*8} │ {'─'*6} {'─'*8} │ {'─'*8} {'─'*8} {'─'*9}")
        print(f"  {'TOTAL':<10} {cur}{totals['spend']:>9.2f} {totals['clicks']:>8,} │ {totals['leads']:>6} {cur}{t_cpl:>7.2f} │ {totals['wa_conv']:>8} {totals['wa_reply']:>8} {totals['wa_depth3']:>9}")

        # Summary
        print(f"\n  Resumen:")
        print(f"    Spend total: {cur}{totals['spend']:,.2f} ({cur}{totals['spend']/len(active_rows):,.2f}/mes)")
        if totals["leads"]:
            print(f"    Web leads: {totals['leads']:,} ({cur}{t_cpl:.2f}/lead)")
        if totals["wa_reply"]:
            wa_cost = totals["spend"] / totals["wa_reply"]
            print(f"    WA replies: {totals['wa_reply']:,} ({cur}{wa_cost:.2f}/reply)")
        if totals["leads"] and totals["wa_reply"]:
            total_actions = totals["leads"] + totals["wa_reply"]
            blended_cost = totals["spend"] / total_actions
            print(f"    Blended (leads + WA replies): {total_actions:,} ({cur}{blended_cost:.2f}/acción)")
        print()


if __name__ == "__main__":
    main()
