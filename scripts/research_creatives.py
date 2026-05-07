#!/usr/bin/env python3
"""Extrae datos a nivel de ad/creativo para analizar competencia entre creativos."""

import json
import sys
import re
from pathlib import Path
from helpers import run_meta, get_account, strip_account_flag

PROJECT_DIR = Path(__file__).resolve().parent.parent


def get_ads_for_campaign(campaign_id):
    return run_meta("ad", "list", campaign_id)


def get_ad_insights(ad_id):
    from datetime import datetime, timedelta
    earliest = (datetime.now() - timedelta(days=37 * 30)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    data = run_meta(
        "insights", "get",
        "--ad-id", ad_id,
        "--since", earliest, "--until", today,
        "--fields", "spend,impressions,clicks,ctr,cpc,conversions",
    )
    if data.get("data"):
        return data["data"][0]
    return None


def get_creative_details(creative_id):
    try:
        data = run_meta("creative", "get", creative_id)
        if isinstance(data, list) and data:
            return data[0]
        return data
    except SystemExit:
        return None


def extract_creative_id(creative_field):
    """Parse creative ID from the ad's creative field."""
    match = re.search(r'"id":\s*"(\d+)"', str(creative_field))
    return match.group(1) if match else None


def extract_texts(creative):
    """Extract body texts, titles, and CTA from creative."""
    spec = creative.get("asset_feed_spec", "")
    spec_str = str(spec)

    bodies = []
    titles = []
    ctas = []

    # Parse asset_feed_spec if it's a string repr
    if "bodies" in spec_str:
        body_matches = re.findall(r'"text":\s*"([^"]*)"', spec_str)
        # Filter out empty strings and deduplicate
        seen = set()
        for b in body_matches:
            decoded = b.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            if decoded and decoded not in seen:
                bodies.append(decoded)
                seen.add(decoded)

    if "titles" in spec_str:
        title_section = spec_str[spec_str.find('"titles"'):]
        title_matches = re.findall(r'"text":\s*"([^"]*)"', title_section)
        for t in title_matches:
            decoded = t.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            if decoded and decoded not in titles:
                titles.append(decoded)

    if "call_to_action_types" in spec_str:
        cta_matches = re.findall(r'"call_to_action_types":\s*\[\s*"([^"]*)"', spec_str)
        ctas = cta_matches

    # Fallback to simple fields
    if not bodies:
        body = creative.get("body", "")
        if body:
            bodies = [body]
    if not titles:
        title = creative.get("title", "")
        if title:
            titles = [title]

    return bodies, titles, ctas


def main():
    args = strip_account_flag(sys.argv)
    acct = get_account()
    cur = acct["currency"]

    if not args:
        print("Uso: python research_creatives.py <CAMPAIGN_ID> [CAMPAIGN_ID...]")
        print("     python research_creatives.py --account mibrand <CAMPAIGN_ID>")
        print()
        print("Tip: Usa research_extract.py primero para identificar las campanas top.")
        sys.exit(0)

    campaign_ids = args
    all_results = []

    for campaign_id in campaign_ids:
        ads = get_ads_for_campaign(campaign_id)
        campaign_name = ads[0].get("campaign_id", campaign_id) if ads else campaign_id

        # Get campaign name from first ad's campaign_id or use ID
        campaigns = run_meta("campaign", "list")
        campaign_info = next((c for c in campaigns if c["id"] == campaign_id), {})
        campaign_name = campaign_info.get("name", campaign_id)

        print(f"\n{'='*90}")
        print(f"  CAMPANA: {campaign_name}")
        print(f"  Ads totales: {len(ads)} ({sum(1 for a in ads if a.get('status') == 'ACTIVE')} activos, {sum(1 for a in ads if a.get('status') == 'PAUSED')} pausados)")
        print(f"{'='*90}")

        ad_data = []

        for i, ad in enumerate(ads):
            ad_id = ad["id"]
            ad_name = ad.get("name", "?")
            ad_status = ad.get("status", "?")
            creative_id = extract_creative_id(ad.get("creative", ""))

            sys.stderr.write(f"  [{i+1}/{len(ads)}] {ad_name}...\n")

            insights = get_ad_insights(ad_id)

            row = {
                "ad_id": ad_id,
                "ad_name": ad_name,
                "status": ad_status,
                "creative_id": creative_id,
            }

            if insights:
                row["spend"] = float(insights.get("spend", 0))
                row["impressions"] = int(insights.get("impressions", 0))
                row["clicks"] = int(insights.get("clicks", 0))
                row["ctr"] = float(insights.get("ctr", 0))
                row["cpc"] = float(insights.get("cpc", 0))
                convs = insights.get("conversions")
                if convs:
                    contact = next((c for c in convs if c["action_type"] == "contact_website"), None)
                    row["contact_website"] = int(contact["value"]) if contact else 0
                else:
                    row["contact_website"] = 0
            else:
                row["spend"] = 0
                row["contact_website"] = 0

            # Get creative content
            if creative_id:
                creative = get_creative_details(creative_id)
                if creative:
                    bodies, titles, ctas = extract_texts(creative)
                    row["bodies"] = bodies
                    row["titles"] = titles
                    row["ctas"] = ctas

            ad_data.append(row)

        # Sort by spend
        ad_data.sort(key=lambda x: x.get("spend", 0), reverse=True)

        # Print table
        print(f"\n  {'Ad':<30} {'Status':<8} {'Spend':>10} {'Impr':>10} {'Clicks':>7} {'CTR':>6} {'CPC':>6} {'Contacts':>8}")
        print(f"  {'─'*30} {'─'*8} {'─'*10} {'─'*10} {'─'*7} {'─'*6} {'─'*6} {'─'*8}")

        for r in ad_data:
            name = r["ad_name"][:30]
            status = r["status"][:8]
            spend = r.get("spend", 0)
            if spend > 0:
                impr = r.get("impressions", 0)
                clicks = r.get("clicks", 0)
                ctr = r.get("ctr", 0)
                cpc = r.get("cpc", 0)
                contacts = r.get("contact_website", 0)
                print(f"  {name:<30} {status:<8} {cur}{spend:>9.2f} {impr:>10,} {clicks:>7,} {ctr:>5.2f}% {cur}{cpc:>5.2f} {contacts:>8}")
            else:
                print(f"  {name:<30} {status:<8} {'—':>10} {'—':>10} {'—':>7} {'—':>6} {'—':>6} {'—':>8}")

        # Print creative details for top ads
        print(f"\n  DETALLE DE CREATIVOS (top por spend)")
        print(f"  {'─'*80}")

        for r in ad_data[:10]:  # Top 10
            if r.get("spend", 0) == 0:
                continue
            print(f"\n  {r['ad_name']} [{r['status']}] — Spend: {cur}{r['spend']:.2f}, Contacts: {r.get('contact_website', 0)}")
            bodies = r.get("bodies", [])
            titles = r.get("titles", [])
            ctas = r.get("ctas", [])
            if titles:
                print(f"    Titulos: {' | '.join(titles)}")
            if ctas:
                print(f"    CTA: {', '.join(ctas)}")
            if bodies:
                for j, b in enumerate(bodies):
                    preview = b[:120] + "..." if len(b) > 120 else b
                    print(f"    Body {j+1}: {preview}")

        all_results.append({"campaign": campaign_name, "campaign_id": campaign_id, "ads": ad_data})

    # Save JSON
    output_file = PROJECT_DIR / "research" / f"{acct['label'].split()[-1].lower()}_creatives.json"
    with open(output_file, "w", errors="replace") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    sys.stderr.write(f"\n  Datos guardados en {output_file}\n")


if __name__ == "__main__":
    main()
