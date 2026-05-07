"""Funciones compartidas para scripts de Meta Ads."""

import subprocess
import json
import sys
import os
from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
API_VERSION = "v21.0"
API_BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

DEFAULT_THRESHOLDS = {
    "max_cpl": 20.00,
    "min_spend_for_flag": 50.0,
}


def _load_config():
    path = PROJECT_DIR / "accounts.yaml"
    if not path.exists():
        print(
            "Error: falta accounts.yaml en la raíz del proyecto.\n"
            "       Copia accounts.example.yaml a accounts.yaml y rellena los IDs.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    if not cfg.get("accounts"):
        print("Error: accounts.yaml no tiene la sección 'accounts:' o está vacía.", file=sys.stderr)
        sys.exit(1)
    return cfg


_CONFIG = _load_config()
ACCOUNTS = _CONFIG.get("accounts", {})
THRESHOLDS = _CONFIG.get("thresholds", {})


def get_account(name=None):
    """Return account config. Reads from --account flag, COUNTRY env var, or defaults to first account."""
    # Check sys.argv for --account flag
    if name is None:
        for i, arg in enumerate(sys.argv):
            if arg == "--account" and i + 1 < len(sys.argv):
                name = sys.argv[i + 1]
                break

    if name is None:
        name = os.environ.get("COUNTRY")

    if name is None:
        # Default: primera cuenta declarada en accounts.yaml
        name = next(iter(ACCOUNTS))

    name = name.lower()
    if name not in ACCOUNTS:
        print(
            f"Error: Cuenta '{name}' no existe en accounts.yaml. Opciones: {', '.join(ACCOUNTS.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    return ACCOUNTS[name]


def get_thresholds(name=None):
    """Return scoring thresholds for an account. Falls back to DEFAULT_THRESHOLDS."""
    if name is None:
        for i, arg in enumerate(sys.argv):
            if arg == "--account" and i + 1 < len(sys.argv):
                name = sys.argv[i + 1]
                break
    if name is None:
        name = os.environ.get("COUNTRY")
    if name is None:
        name = next(iter(ACCOUNTS))
    name = name.lower()
    return THRESHOLDS.get(name, DEFAULT_THRESHOLDS)


def run_meta(*args, account=None):
    """Run a meta ads command and return parsed JSON."""
    acct = get_account(account)
    cmd = ["meta", "--output", "json", "ads", "--ad-account-id", acct["ad_account_id"], *args]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)

    if result.returncode == 3:
        print("Error: No autenticado. Configura ACCESS_TOKEN en .env", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print(f"Error (exit {result.returncode}): {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    return json.loads(result.stdout)


def strip_account_flag(argv):
    """Remove --account and its value from argv, return remaining args."""
    result = []
    skip_next = False
    for arg in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg == "--account":
            skip_next = True
            continue
        result.append(arg)
    return result


def get_access_token():
    """Lee ACCESS_TOKEN del .env."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        print("Error: ACCESS_TOKEN no encontrado en .env", file=sys.stderr)
        sys.exit(1)
    return token
