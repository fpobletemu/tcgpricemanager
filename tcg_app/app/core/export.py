"""
Export confirmed (and other) batch items to a standardized CSV file.

One row per (product × price variant). UTF-8 BOM encoding so Excel opens correctly.
"""
import csv
from pathlib import Path
from typing import TYPE_CHECKING

from app.db import database as db
from app.api import exchange

if TYPE_CHECKING:
    from app.core.fuzzy import BatchItem

HEADERS = [
    "Input original", "Estado",
    "Idioma (input)", "Rareza (input)",      # ← from user metadata
    "productId", "Nombre oficial", "Nombre limpio",
    "Código", "Rareza (DB)", "Tipo de carta", "HP", "Etapa",
    "Set", "Abreviación",
    "Variante",
    "Low USD", "Mid USD", "Market USD", "Direct Low USD",
    "Low CLP", "Mid CLP", "Market CLP", "Direct Low CLP",
    "URL imagen", "URL TCGplayer",
]

_STATUS = {
    "confirmed" : "Confirmado",
    "review"    : "Pendiente revisión",
    "not_found" : "No encontrado",
}


def export_batch_to_csv(
    items    : "list[BatchItem]",
    conn,
    dest_path: Path,
    rate     : float | None = None,
) -> int:
    """
    Write all batch items to CSV (any status).
    Fetches prices from the local DB for confirmed items.
    Returns the number of data rows written.
    """
    if rate is None:
        try:
            rate = exchange.get_rate(conn)
        except Exception:
            rate = 0.0

    rows_written = 0
    with open(dest_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for item in items:
            prod   = item.matched_product or {}
            pid    = prod.get("productId")
            prices = db.get_prices_for_product(conn, pid) if pid and item.status == "confirmed" else []

            if prices:
                for price in prices:
                    writer.writerow(_row(item, prod, price, rate))
                    rows_written += 1
            else:
                writer.writerow(_row(item, prod, {}, rate))
                rows_written += 1

    return rows_written


def export_search_to_csv(
    products : list[dict],
    conn,
    dest_path: Path,
    rate     : float | None = None,
) -> int:
    """Export a list of products from the search tab to CSV."""
    if rate is None:
        try:
            rate = exchange.get_rate(conn)
        except Exception:
            rate = 0.0

    # Fake a BatchItem-like structure for _row()
    class _FakeItem:
        input_text = ""
        status     = "confirmed"

    fake = _FakeItem()
    rows_written = 0
    with open(dest_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for prod in products:
            prices = db.get_prices_for_product(conn, prod.get("productId"))
            if prices:
                for price in prices:
                    writer.writerow(_row(fake, prod, price, rate))
                    rows_written += 1
            else:
                writer.writerow(_row(fake, prod, {}, rate))
                rows_written += 1
    return rows_written


def _row(item, prod: dict, price: dict, rate: float) -> dict:
    meta = getattr(item, "metadata", {})
    return {
        "Input original" : getattr(item, "input_text", ""),
        "Estado"         : _STATUS.get(getattr(item, "status", ""), ""),
        "Idioma (input)" : meta.get("idioma", ""),
        "Rareza (input)" : meta.get("rareza", ""),
        "productId"      : prod.get("productId", ""),
        "Nombre oficial" : prod.get("name", ""),
        "Nombre limpio"  : prod.get("cleanName", ""),
        "Código"         : prod.get("extNumber", ""),
        "Rareza (DB)"    : prod.get("extRarity", ""),
        "Tipo de carta"  : prod.get("extCardType", ""),
        "HP"             : prod.get("extHP", ""),
        "Etapa"          : prod.get("extStage", ""),
        "Set"            : prod.get("groupName", ""),
        "Abreviación"    : prod.get("groupAbbr", ""),
        "Variante"       : price.get("subTypeName", ""),
        "Low USD"        : _usd(price.get("lowPrice")),
        "Mid USD"        : _usd(price.get("midPrice")),
        "Market USD"     : _usd(price.get("marketPrice")),
        "Direct Low USD" : _usd(price.get("directLowPrice")),
        "Low CLP"        : _clp(price.get("lowPrice"),       rate),
        "Mid CLP"        : _clp(price.get("midPrice"),       rate),
        "Market CLP"     : _clp(price.get("marketPrice"),    rate),
        "Direct Low CLP" : _clp(price.get("directLowPrice"), rate),
        "URL imagen"     : prod.get("imageUrl", ""),
        "URL TCGplayer"  : prod.get("url", ""),
    }


def _usd(v) -> str:
    try:
        return f"{float(v):.2f}" if v not in (None, "", "None") else ""
    except (ValueError, TypeError):
        return ""


def _clp(v, rate: float) -> str:
    if not v or rate == 0:
        return ""
    try:
        return str(round(float(v) * rate))
    except (ValueError, TypeError):
        return ""
