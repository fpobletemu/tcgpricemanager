"""
Central SQLite database module for TCG Price Manager.
Single source of truth for all DB operations.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

# tcg_app/app/db/database.py → tcg_app/data/tcg.db
_BASE   = Path(__file__).resolve().parent.parent.parent
DB_PATH = _BASE / "data" / "tcg.db"

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    categoryId  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    displayName TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS groups (
    groupId        INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    abbreviation   TEXT DEFAULT '',
    categoryId     INTEGER NOT NULL REFERENCES categories(categoryId),
    publishedOn    TEXT,
    modifiedOn     TEXT,
    isSupplemental INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    productId      INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    cleanName      TEXT,
    imageUrl       TEXT,
    categoryId     INTEGER NOT NULL,
    groupId        INTEGER NOT NULL REFERENCES groups(groupId),
    url            TEXT,
    modifiedOn     TEXT,
    imageCount     INTEGER DEFAULT 0,
    extCardText    TEXT,
    extRarity      TEXT,
    extNumber      TEXT,
    extCardType    TEXT,
    extHP          TEXT,
    extStage       TEXT,
    extAttack1     TEXT,
    extAttack2     TEXT,
    extWeakness    TEXT,
    extResistance  TEXT,
    extRetreatCost TEXT,
    extUPC         TEXT,
    extDescription TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    productId      INTEGER NOT NULL REFERENCES products(productId),
    subTypeName    TEXT NOT NULL DEFAULT 'Normal',
    lowPrice       REAL,
    midPrice       REAL,
    highPrice      REAL,
    marketPrice    REAL,
    directLowPrice REAL,
    UNIQUE(productId, subTypeName)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at      TEXT NOT NULL,
    category_id    INTEGER,
    groups_synced  INTEGER DEFAULT 0,
    rows_processed INTEGER DEFAULT 0,
    status         TEXT DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_products_name       ON products(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_products_cleanName  ON products(cleanName COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_products_extNumber  ON products(extNumber);
CREATE INDEX IF NOT EXISTS idx_products_groupId    ON products(groupId);
CREATE INDEX IF NOT EXISTS idx_products_categoryId ON products(categoryId);
CREATE INDEX IF NOT EXISTS idx_prices_productId    ON prices(productId);
"""


# ── Connection ─────────────────────────────────────────────────────────────
def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> sqlite3.Connection:
    conn = get_connection()
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


# ── Upsert helpers ─────────────────────────────────────────────────────────
def upsert_category(conn: sqlite3.Connection, row: dict):
    conn.execute(
        "INSERT OR REPLACE INTO categories(categoryId, name, displayName) VALUES(?,?,?)",
        (row["categoryId"], row["name"], row.get("displayName", row["name"]))
    )


def upsert_group(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT OR REPLACE INTO groups
            (groupId, name, abbreviation, categoryId, publishedOn, modifiedOn, isSupplemental)
        VALUES (?,?,?,?,?,?,?)
    """, (
        row["groupId"], row["name"], row.get("abbreviation", ""),
        row["categoryId"], row.get("publishedOn"), row.get("modifiedOn"),
        1 if row.get("isSupplemental") else 0,
    ))


_PRODUCT_FIELDS = (
    "productId", "name", "cleanName", "imageUrl", "categoryId", "groupId",
    "url", "modifiedOn", "imageCount",
    "extCardText", "extRarity", "extNumber", "extCardType", "extHP",
    "extStage", "extAttack1", "extAttack2", "extWeakness", "extResistance",
    "extRetreatCost", "extUPC", "extDescription",
)


def upsert_product(conn: sqlite3.Connection, row: dict):
    vals = [_str_or_none(row.get(f)) for f in _PRODUCT_FIELDS]
    # productId and name must be present
    if not vals[0]:
        return
    placeholders = ",".join("?" * len(_PRODUCT_FIELDS))
    cols = ",".join(_PRODUCT_FIELDS)
    conn.execute(f"INSERT OR REPLACE INTO products({cols}) VALUES({placeholders})", vals)


def upsert_price(conn: sqlite3.Connection, row: dict):
    pid = row.get("productId")
    if not pid:
        return
    conn.execute("""
        INSERT OR REPLACE INTO prices
            (productId, subTypeName, lowPrice, midPrice, highPrice, marketPrice, directLowPrice)
        VALUES (?,?,?,?,?,?,?)
    """, (
        pid,
        row.get("subTypeName") or "Normal",
        _float(row.get("lowPrice")),
        _float(row.get("midPrice")),
        _float(row.get("highPrice")),
        _float(row.get("marketPrice")),
        _float(row.get("directLowPrice")),
    ))


def _str_or_none(v) -> str | None:
    if v in (None, "", "None"):
        return None
    return str(v)


def _float(v) -> float | None:
    try:
        return float(v) if v not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


# ── Sync log ───────────────────────────────────────────────────────────────
def log_sync(conn: sqlite3.Connection, category_id: int | None,
             groups: int, rows: int, status: str = "ok"):
    conn.execute(
        "INSERT INTO sync_log(synced_at, category_id, groups_synced, rows_processed, status) "
        "VALUES(?,?,?,?,?)",
        (datetime.utcnow().isoformat(), category_id, groups, rows, status)
    )
    conn.commit()


# ── Settings ───────────────────────────────────────────────────────────────
def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str):
    conn.execute(
        "INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES(?,?,?)",
        (key, value, datetime.utcnow().isoformat())
    )
    conn.commit()


# ── Queries ────────────────────────────────────────────────────────────────
def get_all_groups(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("""
        SELECT g.groupId, g.name, g.abbreviation, g.categoryId,
               c.displayName AS categoryName
        FROM groups g
        JOIN categories c ON g.categoryId = c.categoryId
        ORDER BY c.displayName, g.name
    """).fetchall()
    return [dict(r) for r in rows]


def search_products(conn: sqlite3.Connection,
                    name: str = "",
                    number: str = "",
                    group_id: int | None = None,
                    limit: int = 300) -> list[dict]:
    where, params = [], []
    if name:
        where.append("(p.name LIKE ? OR p.cleanName LIKE ?)")
        params += [f"%{name}%", f"%{name}%"]
    if number:
        where.append("p.extNumber = ?")
        params.append(number)
    if group_id:
        where.append("p.groupId = ?")
        params.append(group_id)

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)

    rows = conn.execute(f"""
        SELECT p.*, g.name AS groupName, g.abbreviation AS groupAbbr
        FROM products p
        JOIN groups g ON p.groupId = g.groupId
        {clause}
        ORDER BY p.name
        LIMIT ?
    """, params).fetchall()
    return [dict(r) for r in rows]


def get_prices_for_product(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM prices WHERE productId=? ORDER BY subTypeName",
        (product_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_db_stats(conn: sqlite3.Connection) -> dict:
    products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    prices   = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    last     = conn.execute(
        "SELECT synced_at FROM sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {
        "products" : products,
        "prices"   : prices,
        "last_sync": last["synced_at"][:16].replace("T", " ") if last else "—",
    }


def load_all_for_fuzzy(conn: sqlite3.Connection) -> list[dict]:
    """Minimal product data for fuzzy matching — keeps memory footprint low."""
    rows = conn.execute("""
        SELECT p.productId, p.name, p.cleanName, p.extNumber, p.extRarity,
               p.imageUrl, p.url, p.categoryId,
               g.name AS groupName, g.abbreviation AS groupAbbr
        FROM products p
        JOIN groups g ON p.groupId = g.groupId
    """).fetchall()
    return [dict(r) for r in rows]
