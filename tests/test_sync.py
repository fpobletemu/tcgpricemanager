"""
Tests for the sync layer — CSV parsing, product/price separation, deduplication.
"""
import io
import csv
from pathlib import Path

import pytest
from app.db import database as db
from app.core import sync


# ── Sample CSV matching real ProductsAndPrices.csv format ─────────────────
SAMPLE_CSV = """\
productId,name,cleanName,imageUrl,categoryId,groupId,url,modifiedOn,imageCount,extCardText,lowPrice,midPrice,highPrice,marketPrice,directLowPrice,subTypeName,extUPC,extRarity,extNumber,extCardType,extHP,extStage,extAttack1,extAttack2,extWeakness,extResistance,extRetreatCost
451396,Lugia VSTAR,Lugia VSTAR,https://example.com/451396_200w.jpg,3,3170,https://tcgplayer.com/451396,2022-11-11,1,Card text here.,6.31,8.00,25.00,6.31,,Holofoil,,Ultra Rare,139/195,Colorless,280,VSTAR,[4] Tempest Dive,,Lx2,F-30,2
451397,Test Card,Test Card,https://example.com/451397_200w.jpg,3,3170,https://tcgplayer.com/451397,2022-11-11,1,,0.50,1.00,5.00,0.75,,Normal,,,Common,140/195,,,,,,, ,1
451397,Test Card,Test Card,https://example.com/451397_200w.jpg,3,3170,https://tcgplayer.com/451397,2022-11-11,1,,1.00,2.00,8.00,1.50,,Reverse Holofoil,,,Common,140/195,,,,,,, ,1
"""


@pytest.fixture
def csv_file(tmp_path):
    f = tmp_path / "3170_SWSH12.csv"
    f.write_text(SAMPLE_CSV, encoding="utf-8")
    return f


# ── _import_csv_file ────────────────────────────────────────────────────────

def test_import_returns_correct_row_count(mem_conn, csv_file):
    rows = sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    assert rows == 3   # 1 Lugia + 2 Test Card variants


def test_import_creates_products(mem_conn, csv_file):
    sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    count = mem_conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    assert count == 2   # Lugia + Test Card (deduplicated)


def test_import_creates_prices(mem_conn, csv_file):
    sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    count = mem_conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    assert count == 3   # Holofoil + Normal + Reverse Holofoil


def test_import_product_fields(mem_conn, csv_file):
    sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    row = mem_conn.execute(
        "SELECT * FROM products WHERE productId=451396"
    ).fetchone()
    assert row is not None
    assert row["name"]      == "Lugia VSTAR"
    assert row["extNumber"] == "139/195"
    assert row["extRarity"] == "Ultra Rare"
    assert row["extHP"]     == "280"


def test_import_price_fields(mem_conn, csv_file):
    sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    price = mem_conn.execute(
        "SELECT * FROM prices WHERE productId=451396 AND subTypeName='Holofoil'"
    ).fetchone()
    assert price is not None
    assert price["marketPrice"] == 6.31
    assert price["lowPrice"]    == 6.31


def test_import_deduplates_products(mem_conn, csv_file):
    """Running import twice should not create duplicate products."""
    sync._import_csv_file(mem_conn, csv_file, 3)
    sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    count = mem_conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    assert count == 2   # still 2, not 4


def test_import_deduplicates_prices(mem_conn, csv_file):
    """Same productId + subTypeName → upsert, not duplicate."""
    sync._import_csv_file(mem_conn, csv_file, 3)
    sync._import_csv_file(mem_conn, csv_file, 3)
    mem_conn.commit()
    count = mem_conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    assert count == 3


def test_import_skips_empty_productid(mem_conn, tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "productId,name,cleanName,imageUrl,categoryId,groupId,url,modifiedOn,"
        "imageCount,extCardText,lowPrice,midPrice,highPrice,marketPrice,"
        "directLowPrice,subTypeName,extUPC,extRarity,extNumber,extCardType,"
        "extHP,extStage,extAttack1,extAttack2,extWeakness,extResistance,extRetreatCost\n"
        ",bad row,,,,,,,,,,,,,,,,,,,,,,,,\n",
        encoding="utf-8",
    )
    rows = sync._import_csv_file(mem_conn, bad_csv, 3)
    assert rows == 0


# ── import_local_csvs (integration) ─────────────────────────────────────────

def test_import_local_csvs_integration(mem_conn, tmp_path, monkeypatch):
    """Full import_local_csvs with a minimal fake output_pokemon_tcg/ tree."""
    import json

    # Build fake directory structure
    fake_root = tmp_path / "output_pokemon_tcg"
    cat_dir   = fake_root / "3"
    cat_dir.mkdir(parents=True)

    (fake_root / "categories.json").write_text(
        json.dumps([{"categoryId": 3, "name": "Pokemon", "displayName": "Pokemon"}]),
        encoding="utf-8",
    )
    (cat_dir / "groups.json").write_text(
        json.dumps([{
            "groupId": 3170, "name": "SWSH12", "abbreviation": "SWSH12",
            "categoryId": 3, "publishedOn": None, "modifiedOn": None,
        }]),
        encoding="utf-8",
    )
    (cat_dir / "3170_SWSH12.csv").write_text(SAMPLE_CSV, encoding="utf-8")

    monkeypatch.setattr(sync, "OUTPUT_DIR", fake_root)

    groups, rows = sync.import_local_csvs(mem_conn)
    assert groups == 1
    assert rows   == 3

    products = mem_conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    assert products == 2
