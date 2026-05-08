#!/usr/bin/env python3
"""Detecta drift de eficiencia en campañas activas.

Compara CPL `last_90d` vs CPL `lifetime` por campaña activa con >12 meses de
edad. Cuando el ratio supera el threshold (default 1.5×), la campaña ya no
performa como su baseline histórico → candidata a refresh estilo "Andromeda".

Aprendizaje base: las cuentas paid degradan en silencio. Una campaña con CPL
lifetime $4 puede deslizar a $7 en 90d sin que nadie lo note si las decisiones
se toman con `last_14d`.

Usage:
    python3 scripts/check_drift.py --account colombia
    python3 scripts/check_drift.py --account colombia --threshold 2.0
    python3 scripts/check_drift.py --account colombia --min-age-days 180
    python3 scripts/check_drift.py --account colombia --json    # JSON a stdout

Output:
    stderr: tabla rankeada por gravedad de drift
    stdout (con --json): lista de campañas con sus métricas
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from helpers import run_meta, get_account, strip_account_flag


LEAD_ACTIONS = ["offsite_conversion.fb_pixel_lead", "lead", "onsite_conversion.lead_grouped"]
WA_ACTIONS = ["onsite_conversion.messaging_first_reply", "messaging_first_reply"]


def extract_conversions(actions):
    leads = wa = 0
    for a in actions or []:
        at = a.get("action_type", "")
        v = int(a.get("value", 0))
        if at in LEAD_ACTIONS:
            leads += v
        if at in WA_ACTIONS:
            wa += v
    return leads, wa


def get_insights(campaign_id, since, until):
    data = run_meta(
        "insights", "get",
        "--campaign-id", campaign_id,
        "--since", since, "--until", until,
        "--fields", "spend,impressions,clicks,actions",
    )
    rows = data.get("data", [])
    if not rows:
        return None
    r = rows[0]
    spend = float(r.get("spend", 0))
    leads, wa = extract_conversions(r.get("actions"))
    conversions = leads + wa  # tratamos ambas como evento de conversión
    return {
        "spend": spend,
        "impressions": int(r.get("impressions", 0)),
        "clicks": int(r.get("clicks", 0)),
        "leads": leads,
        "wa_replies": wa,
        "conversions": conversions,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--account", help="Cuenta declarada en accounts.yaml")
    ap.add_argument("--threshold", type=float, default=1.5,
                    help="Ratio CPL_90d/CPL_lifetime que dispara flag (default 1.5)")
    ap.add_argument("--min-age-days", type=int, default=365,
                    help="Edad mínima de campaña para evaluarla (default 365 = 12 meses)")
    ap.add_argument("--min-spend-90d", type=float, default=100.0,
                    help="Spend mínimo en 90d para considerar la campaña (default $100)")
    ap.add_argument("--json", action="store_true",
                    help="Emitir JSON estructurado a stdout (además de tabla a stderr)")
    args = ap.parse_args()

    acct = get_account()
    cur = acct["currency"]
    today = datetime.now()
    since_lifetime = (today - timedelta(days=37 * 30)).strftime("%Y-%m-%d")
    since_90d = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    until = today.strftime("%Y-%m-%d")
    min_age_cutoff = today - timedelta(days=args.min_age_days)

    # Listar campañas activas
    campaigns = run_meta("campaign", "list")
    actives = [c for c in campaigns if c.get("effective_status") == "ACTIVE"]
    sys.stderr.write(f"\n  CHECK DRIFT — {acct['label']}\n")
    sys.stderr.write(f"  Campañas activas: {len(actives)}  ·  threshold drift: {args.threshold}×\n")
    sys.stderr.write(f"  Edad mínima: {args.min_age_days}d  ·  spend mínimo 90d: {cur}{args.min_spend_90d}\n\n")

    rows = []
    for c in actives:
        name = c["name"]
        cid = c["id"]
        start_str = (c.get("start_time") or "")[:10]
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        except ValueError:
            start_dt = today  # sin fecha → asumimos jovencita, skip
        age_days = (today - start_dt).days
        if start_dt > min_age_cutoff:
            sys.stderr.write(f"  · skip (edad {age_days}d < min): {name}\n")
            continue

        sys.stderr.write(f"  · {name} ({age_days}d)...\n")
        lifetime = get_insights(cid, since_lifetime, until)
        last_90d = get_insights(cid, since_90d, until)
        if not lifetime or not last_90d:
            continue
        if last_90d["spend"] < args.min_spend_90d:
            sys.stderr.write(f"    skip (spend 90d ${last_90d['spend']:.2f} < min)\n")
            continue
        if lifetime["conversions"] == 0 or last_90d["conversions"] == 0:
            sys.stderr.write(f"    skip (sin conversiones en alguna ventana)\n")
            continue

        cpl_lifetime = lifetime["spend"] / lifetime["conversions"]
        cpl_90d = last_90d["spend"] / last_90d["conversions"]
        ratio = cpl_90d / cpl_lifetime if cpl_lifetime else None
        flagged = ratio is not None and ratio >= args.threshold

        rows.append({
            "campaign_id": cid,
            "name": name,
            "age_days": age_days,
            "spend_lifetime": round(lifetime["spend"], 2),
            "spend_90d": round(last_90d["spend"], 2),
            "conv_lifetime": lifetime["conversions"],
            "conv_90d": last_90d["conversions"],
            "cpl_lifetime": round(cpl_lifetime, 2),
            "cpl_90d": round(cpl_90d, 2),
            "ratio": round(ratio, 2) if ratio else None,
            "flagged": flagged,
        })

    rows.sort(key=lambda r: -(r["ratio"] or 0))

    sys.stderr.write("\n")
    sys.stderr.write(f"  {'Campaña':<32} {'Edad':>6} {'CPL life':>10} {'CPL 90d':>10} {'Ratio':>7}  Veredicto\n")
    sys.stderr.write(f"  {'-'*32} {'-'*6} {'-'*10} {'-'*10} {'-'*7}  {'-'*20}\n")
    for r in rows:
        verdict = "🚨 REFRESH" if r["flagged"] else "OK"
        sys.stderr.write(
            f"  {r['name'][:32]:<32} {r['age_days']:>5}d "
            f"{cur}{r['cpl_lifetime']:>8.2f} {cur}{r['cpl_90d']:>8.2f} "
            f"{(r['ratio'] or 0):>6.2f}×  {verdict}\n"
        )

    flagged = [r for r in rows if r["flagged"]]
    sys.stderr.write(f"\n  {len(flagged)}/{len(rows)} campañas con drift > {args.threshold}×\n")
    if flagged:
        sys.stderr.write(f"\n  Patrón Andromeda recomendado para:\n")
        for r in flagged:
            sys.stderr.write(f"    - {r['name']} (lifetime {cur}{r['cpl_lifetime']:.2f} → 90d {cur}{r['cpl_90d']:.2f}, +{(r['ratio']-1)*100:.0f}%)\n")
        sys.stderr.write(f"\n  Ver docs/api-gotchas.md y templates/andromeda_web_leads.example.yaml\n")

    if args.json:
        print(json.dumps({"account": acct["label"], "threshold": args.threshold, "campaigns": rows}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
