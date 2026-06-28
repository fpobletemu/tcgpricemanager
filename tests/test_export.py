"""
Tests for the CSV export module.
"""
import csv
from pathlib import Path

import pytest
from app.core import export
from app.core.fuzzy import BatchItem
from tests.conftest import LUGIA, CLEFAIRY


def _make_item(prod, status="confirmed", score=100):
    item = BatchItem(
        input_text      = prod.get("name", ""),
        status          = status,
        matched_product = {**prod, "groupName": "SWSH12", "groupAbbr": "SWSH12"},
        score           = score,
        suggestions     = [],
    )
    return item


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ── export_batch_to_csv ────────────────────────────────────────────────────

def test_export_writes_file(mem_conn, tmp_path):
    dest = tmp_path / "out.csv"
    items = [_make_item(LUGIA)]
    rows = export.export_batch_to_csv(items, mem_conn, dest, rate=950.0)
    assert dest.exists()
    assert rows >= 1


def test_export_headers(mem_conn, tmp_path):
    dest = tmp_path / "out.csv"
    export.export_batch_to_csv([_make_item(LUGIA)], mem_conn, dest, rate=950.0)
    rows = _read_csv(dest)
    assert set(export.HEADERS).issubset(set(rows[0].keys()))


def test_export_not_found_item(mem_conn, tmp_path):
    dest  = tmp_path / "out.csv"
    item  = BatchItem(input_text="xyz", status="not_found")
    rows_ = export.export_batch_to_csv([item], mem_conn, dest, rate=950.0)
    rows  = _read_csv(dest)
    assert len(rows) == 1
    assert rows[0]["Estado"] == "No encontrado"
    assert rows[0]["Nombre oficial"] == ""


def test_export_clp_calculation(mem_conn, tmp_path):
    """market price × rate should appear in Market CLP column."""
    from app.db import database as db

    db.upsert_product(mem_conn, LUGIA)
    db.upsert_price(mem_conn, {
        "productId": LUGIA["productId"], "subTypeName": "Holofoil",
        "lowPrice": 5.0, "midPrice": 7.0, "highPrice": 20.0,
        "marketPrice": 10.0, "directLowPrice": None,
    })
    mem_conn.commit()

    dest = tmp_path / "out.csv"
    export.export_batch_to_csv([_make_item(LUGIA)], mem_conn, dest, rate=1000.0)
    rows = _read_csv(dest)
    assert rows[0]["Market CLP"] == "10000"


def test_export_multiple_price_variants(mem_conn, tmp_path):
    """One product with 3 variants → 3 CSV rows."""
    from app.db import database as db

    db.upsert_product(mem_conn, LUGIA)
    for sub in ("Normal", "Holofoil", "Reverse Holofoil"):
        db.upsert_price(mem_conn, {
            "productId": LUGIA["productId"], "subTypeName": sub,
            "lowPrice": 1.0, "midPrice": 2.0, "highPrice": 5.0,
            "marketPrice": 1.8, "directLowPrice": None,
        })
    mem_conn.commit()

    dest = tmp_path / "out.csv"
    export.export_batch_to_csv([_make_item(LUGIA)], mem_conn, dest, rate=900.0)
    rows = _read_csv(dest)
    assert len(rows) == 3
    subtypes = {r["Variante"] for r in rows}
    assert subtypes == {"Normal", "Holofoil", "Reverse Holofoil"}


def test_export_utf8_bom(tmp_path, mem_conn):
    """File must start with UTF-8 BOM so Excel opens it correctly."""
    dest = tmp_path / "out.csv"
    export.export_batch_to_csv([_make_item(LUGIA)], mem_conn, dest, rate=950.0)
    raw = dest.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "File must start with UTF-8 BOM"
