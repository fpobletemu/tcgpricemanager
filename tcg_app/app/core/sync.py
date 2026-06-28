"""
Data synchronization: reads CSVs from output_pokemon_tcg/ → SQLite.
Also orchestrates fresh downloads from the TCGCSV API.
"""
import csv
import io
import json
from pathlib import Path
from typing import Callable

from app.db import database as db
from app.api import tcgcsv

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "output_pokemon_tcg"

# Columns that go to the prices table
_PRICE_COLS = {"lowPrice", "midPrice", "highPrice", "marketPrice", "directLowPrice", "subTypeName"}


def _safe_filename(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "" for c in text).strip()


# ── Public API ─────────────────────────────────────────────────────────────

def import_local_csvs(
    conn,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[int, int]:
    """
    Import all existing CSVs from output_pokemon_tcg/ into SQLite.
    Returns (groups_processed, total_rows).
    """
    _load_metadata(conn)

    all_csvs: list[tuple[Path, int]] = []
    for cat_dir in sorted(OUTPUT_DIR.iterdir()):
        if not cat_dir.is_dir() or not cat_dir.name.isdigit():
            continue
        for csv_file in sorted(cat_dir.glob("*.csv")):
            all_csvs.append((csv_file, int(cat_dir.name)))

    total_files = len(all_csvs)
    total_rows  = 0
    groups_done = 0

    for idx, (csv_path, cat_id) in enumerate(all_csvs, 1):
        if progress_cb:
            progress_cb(idx, total_files, csv_path.stem)
        try:
            rows = _import_csv_file(conn, csv_path, cat_id)
            total_rows  += rows
            groups_done += 1
        except Exception as e:
            print(f"  Error en {csv_path.name}: {e}")

    conn.commit()
    db.log_sync(conn, None, groups_done, total_rows)
    return groups_done, total_rows


def sync_from_api(
    conn,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[int, int]:
    """
    Download fresh CSVs from TCGCSV API then import into SQLite.
    Returns (groups_processed, total_rows).
    """
    cats = tcgcsv.get_categories()
    pokemon_cats = [
        c for c in cats
        if "pokemon" in (c.get("name", "") + c.get("displayName", "")).lower()
        and c["categoryId"] not in tcgcsv.SKIP_CATS
    ]

    all_tasks: list[tuple[int, dict]] = []
    for cat in pokemon_cats:
        groups = tcgcsv.get_groups(cat["categoryId"])
        for g in groups:
            all_tasks.append((cat["categoryId"], g))

    total       = len(all_tasks)
    groups_done = 0
    total_rows  = 0

    for idx, (cat_id, group) in enumerate(all_tasks, 1):
        gid   = group["groupId"]
        gname = group["name"]
        if progress_cb:
            progress_cb(idx, total, gname)

        csv_text = tcgcsv.download_group_csv(cat_id, gid)
        if not csv_text:
            continue

        safe = _safe_filename(gname)[:60]
        dest = OUTPUT_DIR / str(cat_id) / f"{gid}_{safe}.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not (dest.exists() and dest.stat().st_size > 0):
            dest.write_text(csv_text, encoding="utf-8")

        rows = _import_csv_file(conn, dest, cat_id)
        total_rows  += rows
        groups_done += 1

    conn.commit()
    last_updated = tcgcsv.get_last_updated()
    if last_updated:
        db.set_setting(conn, "last_sync_at", last_updated)
    db.log_sync(conn, None, groups_done, total_rows)
    return groups_done, total_rows


# ── Internals ──────────────────────────────────────────────────────────────

def _load_metadata(conn):
    """Load categories.json and groups.json files into the DB."""
    cats_file = OUTPUT_DIR / "categories.json"
    if cats_file.exists():
        cats = json.loads(cats_file.read_text(encoding="utf-8"))
        for cat in cats:
            db.upsert_category(conn, cat)

    for cat_dir in OUTPUT_DIR.iterdir():
        if not cat_dir.is_dir() or not cat_dir.name.isdigit():
            continue
        groups_file = cat_dir / "groups.json"
        if groups_file.exists():
            groups = json.loads(groups_file.read_text(encoding="utf-8"))
            for group in groups:
                db.upsert_group(conn, group)
    conn.commit()


def _import_csv_file(conn, csv_path: Path, cat_id: int) -> int:
    """Import a single ProductsAndPrices CSV. Returns number of price rows."""
    text = csv_path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = 0
    seen_products: set[int] = set()

    for row in reader:
        raw_pid = row.get("productId", "").strip()
        if not raw_pid:
            continue
        try:
            pid = int(raw_pid)
        except ValueError:
            continue

        # Upsert product exactly once per productId
        if pid not in seen_products:
            prod = {k: v for k, v in row.items() if k not in _PRICE_COLS}
            db.upsert_product(conn, prod)
            seen_products.add(pid)

        # Upsert price row (one per subTypeName variant)
        db.upsert_price(conn, {
            "productId"     : pid,
            "subTypeName"   : row.get("subTypeName") or "Normal",
            "lowPrice"      : row.get("lowPrice"),
            "midPrice"      : row.get("midPrice"),
            "highPrice"     : row.get("highPrice"),
            "marketPrice"   : row.get("marketPrice"),
            "directLowPrice": row.get("directLowPrice"),
        })
        rows += 1

    return rows
