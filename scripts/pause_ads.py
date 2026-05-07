#!/usr/bin/env python3
"""Pausa ads con confirmación y logging."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from helpers import run_meta, get_account, strip_account_flag, PROJECT_DIR

LOGS_DIR = PROJECT_DIR / "logs"


def get_ad_info(ad_id):
    """Fetch ad por ID via insights (incluye nombre en el response si existe)."""
    try:
        data = run_meta("ad", "get", ad_id)
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data:
            return data[0]
    except SystemExit:
        pass
    return None


def get_ad_insights_14d(ad_id):
    data = run_meta(
        "insights", "get",
        "--ad-id", ad_id,
        "--date-preset", "last_14d",
        "--fields", "spend,impressions,clicks,ctr,actions",
    )
    if data.get("data"):
        return data["data"][0]
    return {}


def extract_lead_count(insights):
    actions = insights.get("actions", [])
    if not actions:
        return 0
    lead_actions = ["offsite_conversion.fb_pixel_lead", "lead"]
    wa_actions = ["onsite_conversion.messaging_first_reply", "messaging_first_reply"]
    leads = 0
    wa = 0
    for a in actions:
        action_type = a.get("action_type", "")
        value = int(a.get("value", 0))
        if action_type in lead_actions:
            leads = max(leads, value)
        elif action_type in wa_actions:
            wa = max(wa, value)
    return leads + wa


def pause_ad(ad_id):
    """Ejecuta pausa via CLI. Retorna True si OK, False si error."""
    import subprocess
    from helpers import PROJECT_DIR
    acct = get_account()
    cmd = ["meta", "--output", "json", "ads", "--ad-account-id", acct["ad_account_id"],
           "ad", "update", ad_id, "--status", "PAUSED"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    return result.returncode == 0


def log_pause(ad_id, ad_name, account_label, metrics_str):
    """Append al log de pausas."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / "paused.log"
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp} | {account_label} | {ad_id} | {ad_name} | {metrics_str}\n"
    with open(log_file, "a") as f:
        f.write(line)


def main():
    args = strip_account_flag(sys.argv)
    acct = get_account()
    currency = acct["currency"]
    yes_flag = "--yes" in args
    args = [a for a in args if a != "--yes"]

    # Leer IDs de argumentos o stdin
    ad_ids = []
    if args:
        ad_ids = args
    elif not sys.stdin.isatty():
        # Intentar parsear JSON de evaluate.py desde stdin
        stdin_data = sys.stdin.read().strip()
        try:
            data = json.loads(stdin_data)
            for campaign in data:
                for ad in campaign.get("ads", []):
                    if ad.get("status_rec") in ("PAUSE?", "FATIGUE?"):
                        ad_ids.append(ad["ad_id"])
        except (json.JSONDecodeError, TypeError):
            # Asumir un ID por línea
            ad_ids = [line.strip() for line in stdin_data.split("\n") if line.strip()]

    if not ad_ids:
        print("Uso: python pause_ads.py --account <name> [--yes] <AD_ID> [AD_ID...]")
        print("     python evaluate.py --account <name> | python pause_ads.py --account <name>")
        sys.exit(1)

    # Fetch info de cada ad
    sys.stderr.write(f"Consultando {len(ad_ids)} ad(s) en {acct['label']}...\n\n")
    ads_info = []
    skipped = []

    for ad_id in ad_ids:
        # Verificar status actual
        ad_info = get_ad_info(ad_id)
        ad_name = ad_info.get("name", ad_id) if ad_info else ad_id
        current_status = (ad_info or {}).get("effective_status", "UNKNOWN")

        if current_status == "PAUSED":
            skipped.append({"ad_id": ad_id, "name": ad_name, "reason": "ya está PAUSED"})
            continue

        insights = get_ad_insights_14d(ad_id)
        spend = float(insights.get("spend", 0))
        leads = extract_lead_count(insights)
        cpl = spend / leads if leads > 0 else None

        ads_info.append({
            "ad_id": ad_id,
            "name": ad_name,
            "spend": spend,
            "leads": leads,
            "cpl": cpl,
        })
        time.sleep(0.5)

    if skipped:
        sys.stderr.write(f"  Skipped (ya pausados):\n")
        for s in skipped:
            sys.stderr.write(f"    - {s['name']} ({s['ad_id']})\n")
        sys.stderr.write(f"\n")

    if not ads_info:
        sys.stderr.write("  No hay ads activos para pausar.\n")
        sys.exit(0)

    # Mostrar preview
    sys.stderr.write(f"  PAUSAR:\n")
    sys.stderr.write(f"  {'AD ID':<20} {'SPEND (14d)':>12} {'CONV':>5} {'CPL':>10}\n")
    sys.stderr.write(f"  {'─'*20} {'─'*12} {'─'*5} {'─'*10}\n")

    for ad in ads_info:
        cpl_str = f"{currency}{ad['cpl']:.2f}" if ad["cpl"] else "N/A"
        sys.stderr.write(f"  {ad['ad_id']:<20} {currency}{ad['spend']:>10.2f} {ad['leads']:>5} {cpl_str:>10}\n")

    sys.stderr.write(f"\n")

    # Confirmar
    if not yes_flag:
        response = input("  Proceder con pausa? [y/N]: ").strip().lower()
        if response != "y":
            sys.stderr.write("  Cancelado.\n")
            sys.exit(0)

    # Ejecutar pausas
    results = []
    for ad in ads_info:
        success = pause_ad(ad["ad_id"])
        if success:
            metrics_str = f"{currency}{ad['spend']:.0f} spent | {ad['leads']} leads"
            log_pause(ad["ad_id"], ad["name"], acct["label"], metrics_str)
            sys.stderr.write(f"  PAUSED: {ad['ad_id']}\n")
            results.append({"ad_id": ad["ad_id"], "status": "paused"})
        else:
            sys.stderr.write(f"  ERROR: {ad['ad_id']} — no se pudo pausar\n")
            results.append({"ad_id": ad["ad_id"], "status": "error"})
        time.sleep(0.5)

    sys.stderr.write(f"\n  Listo. {sum(1 for r in results if r['status'] == 'paused')}/{len(results)} pausados.\n")
    sys.stderr.write(f"  Log: logs/paused.log\n")

    # JSON a stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
