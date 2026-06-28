"""
USD → CLP exchange rate service.
Fetches from open.er-api.com and caches result for 1 hour in the settings table.
"""
import requests
from datetime import datetime, timedelta

API_URL       = "https://open.er-api.com/v6/latest/USD"
CACHE_TTL_MIN = 60
FALLBACK_RATE = 900.0


def get_rate(conn) -> float:
    """Return current USD→CLP rate, refreshing cache if older than 1 hour."""
    from app.db import database as db

    rate_str    = db.get_setting(conn, "usd_clp_rate")
    updated_str = db.get_setting(conn, "usd_clp_updated_at")

    if rate_str and updated_str:
        updated = datetime.fromisoformat(updated_str)
        if datetime.utcnow() - updated < timedelta(minutes=CACHE_TTL_MIN):
            return float(rate_str)

    try:
        resp = requests.get(API_URL, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data["rates"]["CLP"])
        db.set_setting(conn, "usd_clp_rate", str(rate))
        db.set_setting(conn, "usd_clp_updated_at", datetime.utcnow().isoformat())
        return rate
    except Exception:
        return float(rate_str) if rate_str else FALLBACK_RATE


def fetch_and_save(conn) -> tuple[float, str]:
    """Force-fetch ignoring cache. Returns (rate, human_readable_timestamp)."""
    from app.db import database as db

    try:
        resp = requests.get(API_URL, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data["rates"]["CLP"])
        now  = datetime.utcnow().isoformat()
        db.set_setting(conn, "usd_clp_rate", str(rate))
        db.set_setting(conn, "usd_clp_updated_at", now)
        return rate, now[:16].replace("T", " ") + " UTC"
    except Exception as e:
        raise RuntimeError(f"No se pudo obtener la tasa: {e}") from e


def to_clp(usd, rate: float) -> str:
    """Format a USD price as CLP string (e.g. '$1.250'). Returns '—' if None."""
    try:
        if usd is None or usd == "":
            return "—"
        value = float(usd) * rate
        return f"${value:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "—"
