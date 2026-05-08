#!/usr/bin/env python3
"""Crea un ad set vía Graph API directa con targeting completo.

El Meta Ads CLI oficial solo soporta `--targeting-countries` al crear adsets.
Este script llama POST {ad_account}/adsets directamente para soportar:
- geo_locations con countries + custom_locations (lat/lng + radio)
- excluded_geo_locations
- age_min/age_max, género, locales
- custom_audiences, excluded_custom_audiences
- targeting_optimization (Advantage audience)
- promoted_object (pixel + custom_event_type, o page_id para WhatsApp)
- destination_type (WEBSITE, WHATSAPP, MESSENGER, ON_AD)
- attribution_spec parseable de strings tipo "click_7d_view_1d"
- is_dynamic_creative

Lee defaults desde un YAML template; flags CLI los overridean. Crea siempre en
PAUSED. Loguea a logs/created_adsets.log.

Uso:
  python3 scripts/create_adset.py --account mibrand \\
    --campaign-id 1234567 \\
    --template templates/leads.example.yaml \\
    --name "Web Leads — Bogota Test" \\
    --daily-budget 5000 \\
    [--lifetime-budget 100000] [--start-time 2026-05-08T08:00:00-0500] \\
    [--dry-run] [--yes]

Budgets se pasan en MINOR UNITS de la moneda de la cuenta:
  - USD/EUR/MXN/PEN: cents (5000 = $50.00)
  - COP/JPY/KRW: unidad raw (5000 = COP 5,000)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml

from helpers import (
    API_BASE_URL,
    PROJECT_DIR,
    get_access_token,
    get_account,
    ACCOUNTS,
)


# ---------- targeting ----------

def _build_geo(targeting_cfg, key_inc="geo_locations", key_exc="excluded_geo_locations"):
    """Construye geo_locations / excluded_geo_locations desde el YAML.

    Acepta:
      countries: [US, MX]
      custom_locations:
        - {lat: 40.7128, lng: -74.0060, radius_mi: 10, country: US}
      cities:
        - {key: "474037", radius_mi: 8}

    NOTA: si pasás `custom_locations` o `cities`, omitimos `countries` del nivel
    superior (Meta lo interpreta como solapamiento "país + zona dentro" y rechaza
    el adset con error 1487756). Cada custom_location ya lleva su propio country.
    Ver docs/api-gotchas.md.
    """
    out = {}
    custom = targeting_cfg.get("custom_locations") or []
    cities = targeting_cfg.get("cities") or []

    if custom:
        rows = []
        for loc in custom:
            lat = loc["lat"] if "lat" in loc else loc.get("latitude")
            lng = loc["lng"] if "lng" in loc else loc.get("longitude")
            if lat is None or lng is None:
                continue
            rows.append({
                "latitude": float(lat),
                "longitude": float(lng),
                "radius": int(loc.get("radius_mi", 10)),
                "distance_unit": "mile",
                "country": loc.get("country") or (targeting_cfg.get("countries") or ["US"])[0],
            })
        if rows:
            out["custom_locations"] = rows

    if cities:
        out["cities"] = [
            {"key": str(c["key"]), "radius": int(c.get("radius_mi", 10)), "distance_unit": "mile"}
            for c in cities
        ]

    # Solo agregar 'countries' si NO hay custom_locations ni cities (evita overlap).
    if targeting_cfg.get("countries") and not custom and not cities:
        out["countries"] = list(targeting_cfg["countries"])

    return out


def build_targeting(targeting_cfg):
    spec = {}

    geo_inc = _build_geo(targeting_cfg)
    if geo_inc:
        spec["geo_locations"] = geo_inc

    exclusions = targeting_cfg.get("excluded_geo_locations") or {}
    if exclusions:
        excl_built = _build_geo(exclusions)
        if excl_built:
            spec["excluded_geo_locations"] = excl_built

    if "age_min" in targeting_cfg:
        spec["age_min"] = int(targeting_cfg["age_min"])
    if "age_max" in targeting_cfg:
        spec["age_max"] = int(targeting_cfg["age_max"])

    gender = (targeting_cfg.get("gender") or "all").lower()
    if gender == "female":
        spec["genders"] = [2]
    elif gender == "male":
        spec["genders"] = [1]
    # "all" → omitir

    if targeting_cfg.get("locales"):
        spec["locales"] = list(targeting_cfg["locales"])

    if targeting_cfg.get("custom_audiences"):
        spec["custom_audiences"] = [{"id": str(a)} for a in targeting_cfg["custom_audiences"]]
    if targeting_cfg.get("excluded_custom_audiences"):
        spec["excluded_custom_audiences"] = [{"id": str(a)} for a in targeting_cfg["excluded_custom_audiences"]]

    if targeting_cfg.get("flexible_spec"):
        spec["flexible_spec"] = list(targeting_cfg["flexible_spec"])

    # advantage_audience: Meta exige declaración explícita (0 o 1) en adsets nuevos.
    # Si el template no lo declara, default a 0 (off). Ver docs/api-gotchas.md #6.
    aa_value = targeting_cfg.get("advantage_audience")
    if aa_value is None:
        spec["targeting_automation"] = {"advantage_audience": 0}
    else:
        spec["targeting_automation"] = {"advantage_audience": 1 if aa_value else 0}

    return spec


# ---------- attribution ----------

def parse_attribution(setting):
    """'click_7d_view_1d' → [{event_type:CLICK_THROUGH,window_days:7},{event_type:VIEW_THROUGH,window_days:1}]."""
    if not setting:
        return None
    spec = []
    parts = setting.lower().split("_")
    i = 0
    while i < len(parts):
        token = parts[i]
        if token in ("click", "view") and i + 1 < len(parts):
            try:
                days = int(parts[i + 1].rstrip("d"))
            except ValueError:
                i += 1
                continue
            spec.append({
                "event_type": "CLICK_THROUGH" if token == "click" else "VIEW_THROUGH",
                "window_days": days,
            })
            i += 2
        else:
            i += 1
    return spec or None


# ---------- payload ----------

def build_payload(template, account_cfg, args):
    adset = template.get("adset") or {}
    targeting_cfg = adset.get("targeting") or {}

    payload = {
        "name": args.name,
        "campaign_id": args.campaign_id,
        "status": "PAUSED",
        "optimization_goal": adset.get("optimization_goal") or "OFFSITE_CONVERSIONS",
        "billing_event": adset.get("billing_event") or "IMPRESSIONS",
        "targeting": json.dumps(build_targeting(targeting_cfg)),
    }

    if args.daily_budget is not None:
        payload["daily_budget"] = int(args.daily_budget)
    elif args.lifetime_budget is not None:
        payload["lifetime_budget"] = int(args.lifetime_budget)

    if args.start_time:
        payload["start_time"] = args.start_time
    if args.end_time:
        payload["end_time"] = args.end_time

    # destination_type + promoted_object
    destination = (adset.get("destination_type") or "").upper()
    promoted = {}
    if destination == "WHATSAPP":
        payload["destination_type"] = "WHATSAPP"
        # Para CTWA, promoted_object.page_id viene de la cuenta
        promoted["page_id"] = account_cfg["page_id"]
    elif destination:
        payload["destination_type"] = destination

    # Si hay pixel, asume web conversion
    pixel = account_cfg.get("pixel_id")
    custom_event = adset.get("custom_event_type")
    if pixel and custom_event and not destination == "WHATSAPP":
        promoted["pixel_id"] = pixel
        promoted["custom_event_type"] = custom_event

    if promoted:
        payload["promoted_object"] = json.dumps(promoted)

    attr = parse_attribution(adset.get("attribution_setting"))
    if attr:
        payload["attribution_spec"] = json.dumps(attr)

    # is_dynamic_creative: campo immutable post-creación. Pasarlo siempre explícito
    # si el template lo declara (true o false). Default = false (más flexible: permite
    # múltiples ads por adset). Ver docs/api-gotchas.md #4 y #5.
    if "is_dynamic_creative" in adset:
        payload["is_dynamic_creative"] = bool(adset["is_dynamic_creative"])

    # bid_strategy a nivel adset (para ABO). En CBO va en la campaña con campaign budget.
    # Ver docs/api-gotchas.md #3.
    if adset.get("bid_strategy"):
        payload["bid_strategy"] = adset["bid_strategy"].upper()

    if adset.get("bid_amount"):
        payload["bid_amount"] = int(adset["bid_amount"])

    return payload


# ---------- preview / log ----------

def print_preview(payload, account_cfg, args):
    sys.stderr.write("\n" + "=" * 78 + "\n")
    sys.stderr.write(f"  AD SET PREVIEW — {account_cfg['label']}\n")
    sys.stderr.write("=" * 78 + "\n")
    sys.stderr.write(f"  Name:           {payload['name']}\n")
    sys.stderr.write(f"  Campaign:       {payload['campaign_id']}\n")
    sys.stderr.write(f"  Status:         {payload['status']}\n")
    sys.stderr.write(f"  Optimization:   {payload['optimization_goal']}\n")
    sys.stderr.write(f"  Billing:        {payload['billing_event']}\n")
    if "destination_type" in payload:
        sys.stderr.write(f"  Destination:    {payload['destination_type']}\n")
    if "daily_budget" in payload:
        sys.stderr.write(f"  Daily budget:   {payload['daily_budget']} (minor units {account_cfg['currency']})\n")
    if "lifetime_budget" in payload:
        sys.stderr.write(f"  Lifetime:       {payload['lifetime_budget']} (minor units {account_cfg['currency']})\n")
    if "start_time" in payload:
        sys.stderr.write(f"  Start time:     {payload['start_time']}\n")
    if "promoted_object" in payload:
        sys.stderr.write(f"  Promoted obj:   {payload['promoted_object']}\n")
    if "attribution_spec" in payload:
        sys.stderr.write(f"  Attribution:    {payload['attribution_spec']}\n")
    if payload.get("is_dynamic_creative"):
        sys.stderr.write(f"  Dynamic creative: True\n")
    sys.stderr.write(f"  Targeting:\n")
    targeting = json.loads(payload["targeting"])
    for line in json.dumps(targeting, indent=4, ensure_ascii=False).splitlines():
        sys.stderr.write(f"    {line}\n")
    sys.stderr.write("=" * 78 + "\n")
    if args.dry_run:
        sys.stderr.write("  DRY-RUN — no se hace POST a Graph API\n\n")


def confirm():
    sys.stderr.write("¿Crear ad set en PAUSED? [y/N]: ")
    sys.stderr.flush()
    answer = input().strip().lower()
    return answer in ("y", "yes", "s", "si", "sí")


def log_creation(account_cfg, payload, adset_id):
    log_dir = PROJECT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    line = (
        f"{datetime.now().isoformat(timespec='seconds')}\t"
        f"account={account_cfg['ad_account_id']}\t"
        f"campaign={payload['campaign_id']}\t"
        f"adset={adset_id}\t"
        f"name={payload['name']}\n"
    )
    with open(log_dir / "created_adsets.log", "a") as f:
        f.write(line)


# ---------- main ----------

def parse_args():
    p = argparse.ArgumentParser(description="Crea ad set con targeting completo vía Graph API")
    p.add_argument("--account", help="Nombre de la cuenta en accounts.yaml")
    p.add_argument("--campaign-id", required=True, help="ID de la campaña padre")
    p.add_argument("--template", required=True, help="Path a YAML con configuración del adset")
    p.add_argument("--name", required=True, help="Nombre del ad set")
    p.add_argument("--daily-budget", type=int, help="Daily budget en minor units (ej: 5000 = $50 USD)")
    p.add_argument("--lifetime-budget", type=int, help="Lifetime budget en minor units")
    p.add_argument("--start-time", help="ISO 8601 con timezone (ej: 2026-05-08T08:00:00-0500)")
    p.add_argument("--end-time", help="ISO 8601 con timezone (solo con lifetime budget)")
    p.add_argument("--dry-run", action="store_true", help="Imprime payload pero no llama API")
    p.add_argument("--yes", "-y", action="store_true", help="Sin confirmación interactiva")
    return p.parse_args()


def main():
    args = parse_args()

    if args.daily_budget is not None and args.lifetime_budget is not None:
        sys.stderr.write("Error: pasa solo --daily-budget o --lifetime-budget, no ambos.\n")
        sys.exit(1)
    if args.daily_budget is None and args.lifetime_budget is None:
        sys.stderr.write("Error: falta --daily-budget o --lifetime-budget.\n")
        sys.exit(1)

    template_path = Path(args.template)
    if not template_path.is_absolute():
        template_path = PROJECT_DIR / template_path
    if not template_path.exists():
        sys.stderr.write(f"Error: template no encontrado: {template_path}\n")
        sys.exit(1)
    with open(template_path) as f:
        template = yaml.safe_load(f) or {}

    account_cfg = get_account()

    payload = build_payload(template, account_cfg, args)
    print_preview(payload, account_cfg, args)

    if args.dry_run:
        # Echo el payload completo a stdout para inspección
        echo = {k: (json.loads(v) if k in ("targeting", "promoted_object", "attribution_spec") and isinstance(v, str) else v)
                for k, v in payload.items()}
        print(json.dumps(echo, indent=2, ensure_ascii=False))
        sys.exit(0)

    if not args.yes and not confirm():
        sys.stderr.write("Cancelado.\n")
        sys.exit(2)

    access_token = get_access_token()
    payload["access_token"] = access_token
    url = f"{API_BASE_URL}/{account_cfg['ad_account_id']}/adsets"

    sys.stderr.write(f"\nPOST {url}\n")
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        sys.stderr.write(f"Error API ({response.status_code}): {response.text}\n")
        sys.exit(1)

    body = response.json()
    adset_id = body.get("id")
    sys.stderr.write(f"\n✓ Ad set creado en PAUSED: {adset_id}\n")
    log_creation(account_cfg, payload, adset_id)

    print(json.dumps({"adset_id": adset_id}, indent=2))


if __name__ == "__main__":
    main()
