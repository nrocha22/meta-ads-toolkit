#!/usr/bin/env python3
"""Extrae datos a nivel de ad set: targeting geográfico, configuración e insights."""

import json
import sys
import re
from datetime import datetime, timedelta
from helpers import run_meta, get_account, strip_account_flag


def parse_geo(targeting_str):
    """Parse geographic targeting from targeting string."""
    included = []
    excluded = []

    # Split on excluded_geo_locations
    excl_pos = targeting_str.find('excluded_geo_locations')
    geo_pos = targeting_str.find('"geo_locations"')

    # Find all location blocks
    blocks = re.findall(
        r'"(?:latitude)":\s*([\d.-]+).*?"longitude":\s*([\d.-]+).*?"radius":\s*(\d+).*?"country":\s*"(\w+)"',
        targeting_str, re.DOTALL
    )

    if not blocks:
        # Try country-level
        countries = re.findall(r'"countries":\s*\[([^\]]+)\]', targeting_str)
        if countries:
            return [f"Country: {countries[0].strip()}"], []
        return [], []

    # Determine included vs excluded by position
    for lat_s, lng_s, radius, country in blocks:
        pos = targeting_str.find(lat_s)
        entry = f"{country} {lat_s},{lng_s} ({radius}mi)"

        if excl_pos > 0 and pos < geo_pos:
            excluded.append(entry)
        elif excl_pos > 0 and pos > excl_pos and pos < geo_pos:
            excluded.append(entry)
        else:
            included.append(entry)

    # Dedupe keeping order
    return included, excluded


def extract_action(actions, action_type):
    for a in actions:
        if a["action_type"] == action_type:
            return int(a["value"])
    return 0


def main():
    args = strip_account_flag(sys.argv)
    acct = get_account()
    cur = acct["currency"]

    if not args:
        print("Uso: python research_adsets.py <CAMPAIGN_ID> [CAMPAIGN_ID...]")
        sys.exit(0)

    earliest = (datetime.now() - timedelta(days=37 * 30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    campaigns = run_meta("campaign", "list")

    for campaign_id in args:
        info = next((c for c in campaigns if c["id"] == campaign_id), {})
        name = info.get("name", campaign_id)

        adsets = run_meta("adset", "list", campaign_id)

        print(f"\n{'='*110}")
        print(f"  {name} — {len(adsets)} ad sets")
        print(f"{'='*110}")

        for adset in adsets:
            adset_id = adset["id"]
            adset_name = adset.get("name", "?")
            status = adset.get("effective_status", "?")
            opt_goal = adset.get("optimization_goal", "?")
            billing = adset.get("billing_event", "?")
            targeting = str(adset.get("targeting", ""))

            # Parse targeting
            genders = re.search(r'"genders":\s*\[([^\]]*)\]', targeting)
            age_min = re.search(r'"age_min":\s*(\d+)', targeting)
            age_max = re.search(r'"age_max":\s*(\d+)', targeting)
            gender_str = "Mujeres" if genders and "2" in genders.group(1) else "Todos"
            age_str = f"{age_min.group(1) if age_min else '?'}-{age_max.group(1) if age_max else '?'}"

            # Geographic
            included, excluded = parse_geo(targeting)

            # Get insights
            data = run_meta(
                "insights", "get",
                "--adset-id", adset_id,
                "--since", earliest, "--until", today,
                "--fields", "spend,impressions,clicks,actions",
            )
            rows = data.get("data", [])

            print(f"\n  {adset_name} [{status}]")
            print(f"  {'─'*80}")
            print(f"  Optimización: {opt_goal}    Billing: {billing}")
            print(f"  Audiencia: {gender_str}, {age_str} años")
            if included:
                print(f"  Geo incluido: {', '.join(included)}")
            if excluded:
                print(f"  Geo excluido: {', '.join(excluded)}")

            if rows:
                r = rows[0]
                spend = float(r.get("spend", 0))
                impressions = int(r.get("impressions", 0))
                clicks = int(r.get("clicks", 0))
                actions = r.get("actions", [])

                leads = (
                    extract_action(actions, "offsite_conversion.fb_pixel_lead")
                    or extract_action(actions, "lead")
                )
                wa_reply = extract_action(actions, "onsite_conversion.messaging_first_reply")
                wa_conv = extract_action(actions, "onsite_conversion.messaging_conversation_started_7d")
                wa_d3 = extract_action(actions, "onsite_conversion.messaging_user_depth_3_message_send")

                cpl = spend / leads if leads else 0
                cpr = spend / wa_reply if wa_reply else 0

                print(f"  Spend: {cur}{spend:,.2f}  |  Impressions: {impressions:,}  |  Clicks: {clicks:,}")
                if leads:
                    print(f"  Web Leads: {leads:,}  ({cur}{cpl:.2f}/lead)")
                if wa_reply:
                    print(f"  WA Replies: {wa_reply:,}  ({cur}{cpr:.2f}/reply)  |  WA Conv: {wa_conv:,}  |  Depth3: {wa_d3:,}")
                if not leads and not wa_reply:
                    print(f"  Sin conversiones trackeadas")
            else:
                print(f"  Sin datos de insights")

        print()


if __name__ == "__main__":
    main()
