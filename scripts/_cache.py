"""Cache local en disco con TTL para resultados de Graph API/insights.

Diseño minimalista: lee y escribe JSON en `.cache/<sha1(key)>.json`. La key se
construye como string por el caller — usar tuplas determinísticas que reflejen
todo lo que afecta el resultado (account, endpoint, params, date_preset).
"""

import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


def _path(key: str) -> Path:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.json"


def cache_get(key: str, ttl_seconds: int):
    """Devuelve (value, age_seconds) si hay cache fresco, o (None, None) si no."""
    p = _path(key)
    if not p.exists():
        return None, None
    try:
        with open(p) as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None, None
    age = time.time() - entry.get("ts", 0)
    if age > ttl_seconds:
        return None, None
    return entry.get("value"), int(age)


def cache_set(key: str, value) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    p = _path(key)
    with open(p, "w") as f:
        json.dump({"ts": time.time(), "value": value}, f)
