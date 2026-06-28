"""
Tests for the database layer — schema, CRUD, search queries, settings, prices.
"""
import pytest
from app.db import database as db
from tests.conftest import LUGIA, CLEFAIRY


# ── Schema ─────────────────────────────────────────────────────────────────

def test_all_tables_created(mem_conn):
    tables = {r[0] for r in mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    for expected in ("categories", "groups", "products", "prices", "sync_log", "settings"):
        assert expected in tables, f"Missing table: {expected}"


def test_indexes_created(mem_conn):
    indexes = {r[0] for r in mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()}
    assert "idx_products_name"      in indexes
    assert "idx_products_extNumber" in indexes
    assert "idx_prices_productId"   in indexes


# ── Category / Group upsert ────────────────────────────────────────────────

def test_upsert_category(mem_conn):
    db.upsert_category(mem_conn, {"categoryId": 99, "name": "Test", "displayName": "Test Game"})
    mem_conn.commit()
    row = mem_conn.execute("SELECT * FROM categories WHERE categoryId=99").fetchone()
    assert row["displayName"] == "Test Game"


def test_upsert_group(mem_conn):
    db.upsert_group(mem_conn, {
        "groupId": 9999, "name": "Test Set", "abbreviation": "TST",
        "categoryId": 3, "publishedOn": None, "modifiedOn": None,
    })
    mem_conn.commit()
    row = mem_conn.execute("SELECT * FROM groups WHERE groupId=9999").fetchone()
    assert row["abbreviation"] == "TST"


# ── Product upsert & search ────────────────────────────────────────────────

def test_upsert_and_search_by_name(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    mem_conn.commit()
    results = db.search_products(mem_conn, name="Lugia")
    assert len(results) == 1
    assert results[0]["extNumber"] == "139/195"


def test_search_by_exact_number(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    mem_conn.commit()
    results = db.search_products(mem_conn, number="139/195")
    assert len(results) == 1
    assert results[0]["name"] == "Lugia VSTAR"


def test_search_by_group_id(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    db.upsert_product(mem_conn, CLEFAIRY)
    mem_conn.commit()
    results = db.search_products(mem_conn, group_id=3170)
    names = {r["name"] for r in results}
    assert "Lugia VSTAR"          in names
    assert "Lillie's Clefairy ex" in names


def test_search_case_insensitive(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    mem_conn.commit()
    assert db.search_products(mem_conn, name="lugia")
    assert db.search_products(mem_conn, name="LUGIA")


def test_upsert_replaces_existing(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    updated = {**LUGIA, "extHP": "999"}
    db.upsert_product(mem_conn, updated)
    mem_conn.commit()
    row = mem_conn.execute(
        "SELECT extHP FROM products WHERE productId=?", (LUGIA["productId"],)
    ).fetchone()
    assert row["extHP"] == "999"


def test_search_returns_all_without_filter(mem_conn):
    """search_products with no filters returns all products.
    The UI layer (tab_search._search) prevents empty calls."""
    db.upsert_product(mem_conn, LUGIA)
    mem_conn.commit()
    results = db.search_products(mem_conn)
    assert len(results) == 1


# ── Prices ─────────────────────────────────────────────────────────────────

def test_upsert_and_get_prices(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    db.upsert_price(mem_conn, {
        "productId": LUGIA["productId"], "subTypeName": "Holofoil",
        "lowPrice": 5.0, "midPrice": 7.0, "highPrice": 20.0,
        "marketPrice": 6.5, "directLowPrice": 5.8,
    })
    mem_conn.commit()
    prices = db.get_prices_for_product(mem_conn, LUGIA["productId"])
    assert len(prices) == 1
    assert prices[0]["marketPrice"] == 6.5


def test_price_composite_key(mem_conn):
    """Same productId + different subTypeName = two rows."""
    db.upsert_product(mem_conn, LUGIA)
    for sub in ("Normal", "Holofoil", "Reverse Holofoil"):
        db.upsert_price(mem_conn, {
            "productId": LUGIA["productId"], "subTypeName": sub,
            "lowPrice": 1.0, "midPrice": 2.0, "highPrice": 5.0,
            "marketPrice": 1.8, "directLowPrice": None,
        })
    mem_conn.commit()
    prices = db.get_prices_for_product(mem_conn, LUGIA["productId"])
    assert len(prices) == 3
    subtypes = {p["subTypeName"] for p in prices}
    assert subtypes == {"Normal", "Holofoil", "Reverse Holofoil"}


def test_price_none_values_stored_as_null(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    db.upsert_price(mem_conn, {
        "productId": LUGIA["productId"], "subTypeName": "Normal",
        "lowPrice": None, "midPrice": None, "highPrice": None,
        "marketPrice": None, "directLowPrice": None,
    })
    mem_conn.commit()
    price = db.get_prices_for_product(mem_conn, LUGIA["productId"])[0]
    assert price["marketPrice"] is None


# ── Settings ───────────────────────────────────────────────────────────────

def test_set_and_get_setting(mem_conn):
    db.set_setting(mem_conn, "test_key", "hello")
    assert db.get_setting(mem_conn, "test_key") == "hello"


def test_get_nonexistent_setting_returns_none(mem_conn):
    assert db.get_setting(mem_conn, "does_not_exist") is None


def test_setting_overwrite(mem_conn):
    db.set_setting(mem_conn, "k", "v1")
    db.set_setting(mem_conn, "k", "v2")
    assert db.get_setting(mem_conn, "k") == "v2"


# ── DB stats ────────────────────────────────────────────────────────────────

def test_get_db_stats(mem_conn):
    db.upsert_product(mem_conn, LUGIA)
    db.upsert_price(mem_conn, {
        "productId": LUGIA["productId"], "subTypeName": "Normal",
        "lowPrice": 1.0, "midPrice": 2.0, "highPrice": 5.0,
        "marketPrice": 1.8, "directLowPrice": None,
    })
    mem_conn.commit()
    stats = db.get_db_stats(mem_conn)
    assert stats["products"] == 1
    assert stats["prices"]   == 1
