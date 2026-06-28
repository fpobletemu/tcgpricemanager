"""
TCGCSV API client.
Downloads fresh CSVs and checks for new daily builds.
"""
import time
from pathlib import Path

import requests

BASE_URL           = "https://tcgcsv.com"
USER_AGENT         = "TCGPriceManager/1.0.0"
DELAY              = 0.25
SKIP_CATS          = {21, 69, 70}
POKEMON_CATEGORIES = [3, 85]

# Resolved at runtime: busquedastcgcsv/output_pokemon_tcg/
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "output_pokemon_tcg"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _get(url: str) -> requests.Response | None:
    """GET with 3 retries and rate-limit delay. Returns None on 404."""
    for attempt in range(1, 4):
        try:
            r = _session.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(DELAY)
            return r
        except requests.RequestException:
            time.sleep(1.5 * attempt)
    return None


def get_last_updated() -> str:
    r = _get(f"{BASE_URL}/last-updated.txt")
    return r.text.strip() if r else ""


def get_categories() -> list[dict]:
    r = _get(f"{BASE_URL}/tcgplayer/categories")
    if not r:
        return []
    return r.json().get("results", [])


def get_groups(category_id: int) -> list[dict]:
    r = _get(f"{BASE_URL}/tcgplayer/{category_id}/groups")
    if not r:
        return []
    return r.json().get("results", [])


def download_group_csv(category_id: int, group_id: int) -> str | None:
    """Download ProductsAndPrices.csv for a group. Returns CSV text or None."""
    r = _get(f"{BASE_URL}/tcgplayer/{category_id}/{group_id}/ProductsAndPrices.csv")
    return r.text if r else None


def check_for_updates(last_known: str) -> bool:
    """True if the server has a newer build than last_known."""
    server_ts = get_last_updated()
    if not server_ts or not last_known:
        return True
    return server_ts.strip() != last_known.strip()
