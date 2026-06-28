"""
Shared pytest fixtures for TCG Price Manager tests.
"""
import sys
from pathlib import Path

import pytest

# Make tcg_app importable from tests/
sys.path.insert(0, str(Path(__file__).parent.parent / "tcg_app"))

from app.db import database as db


@pytest.fixture
def mem_conn(tmp_path, monkeypatch):
    """
    SQLite connection backed by a temp file DB (fresh for every test).
    All tables and indexes are created; categories and groups are pre-populated.
    """
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    conn = db.initialize_db()

    # Minimal reference data required by FK constraints
    db.upsert_category(conn, {"categoryId": 3,  "name": "Pokemon",      "displayName": "Pokemon"})
    db.upsert_category(conn, {"categoryId": 85, "name": "Pokemon Japan", "displayName": "Pokemon Japan"})
    db.upsert_group(conn, {
        "groupId": 3170, "name": "SWSH12: Silver Tempest",
        "abbreviation": "SWSH12", "categoryId": 3,
        "publishedOn": "2022-11-11T00:00:00", "modifiedOn": "2022-11-11T00:00:00",
        "isSupplemental": False,
    })
    conn.commit()
    yield conn
    conn.close()


# ── Reusable mock product dicts ────────────────────────────────────────────
LUGIA = {
    "productId": 451396, "name": "Lugia VSTAR", "cleanName": "Lugia VSTAR",
    "imageUrl": "https://example.com/451396_200w.jpg",
    "categoryId": 3, "groupId": 3170,
    "url": "https://tcgplayer.com/product/451396",
    "modifiedOn": "2022-11-11T00:00:00", "imageCount": 1,
    "extRarity": "Ultra Rare", "extNumber": "139/195",
    "extCardType": "Colorless", "extHP": "280", "extStage": "VSTAR",
    "extAttack1": "[4] Tempest Dive (220)",
    "extWeakness": "Lx2", "extResistance": "F-30", "extRetreatCost": "2",
}

CLEFAIRY = {
    "productId": 999001, "name": "Lillie's Clefairy ex", "cleanName": "Lillies Clefairy ex",
    "imageUrl": "https://example.com/999001_200w.jpg",
    "categoryId": 3, "groupId": 3170,
    "url": "https://tcgplayer.com/product/999001",
    "modifiedOn": "2024-09-13T00:00:00", "imageCount": 1,
    "extRarity": "Ultra Rare", "extNumber": "076/217",
    "extCardType": "Fairy", "extHP": "130", "extStage": "Stage 1",
}


# Candidates list for fuzzy tests (no DB needed)
FUZZY_CANDIDATES = [
    {**LUGIA,    "groupName": "SWSH12: Silver Tempest", "groupAbbr": "SWSH12"},
    {**CLEFAIRY, "groupName": "SV07: Stellar Crown",    "groupAbbr": "SCR"},
    {
        "productId": 2, "name": "Charizard ex", "cleanName": "Charizard ex",
        "extNumber": "199/165", "extRarity": "Special Illustration Rare",
        "groupName": "SV04: Paradox Rift", "groupAbbr": "PAR",
        "imageUrl": "", "url": "", "categoryId": 3,
    },
]
