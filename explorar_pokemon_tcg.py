#!/usr/bin/env python3
"""
TCGCSV API — Exploración empírica completa de Pokemon TCG
=========================================================
Descubre todas las categorías relacionadas con Pokemon, obtiene
todos sus grupos y descarga ProductsAndPrices.csv por cada grupo.

Salida:
  output_pokemon_tcg/
    categories.json          ← todas las categorías Pokemon encontradas
    {categoryId}/
      groups.json            ← grupos de esa categoría
      {groupId}_{nombre}.csv ← productos + precios de cada grupo

Uso:
  python explorar_pokemon_tcg.py             ← descarga todo
  python explorar_pokemon_tcg.py --dry-run   ← solo lista sin descargar
  python explorar_pokemon_tcg.py --resumen   ← muestra resumen de lo descargado
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Forzar UTF-8 en stdout/stderr (necesario en Windows)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_URL    = "https://tcgcsv.com"
USER_AGENT  = "PokemonTCGExplorer/1.0.0"
DELAY_SEC   = 0.25   # entre requests (obligatorio según docs)
SKIP_CATS   = {21, 69, 70}  # categorías vacías/rotas documentadas
OUTPUT_DIR  = Path("output_pokemon_tcg")

# ── Sesión HTTP ────────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

stats = {
    "requests"   : 0,
    "errores"    : 0,
    "grupos_ok"  : 0,
    "grupos_skip": 0,   # 404 = grupo vacío
    "filas_csv"  : 0,
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get(url: str, binary: bool = False):
    """GET con 3 reintentos y rate-limit."""
    for intento in range(1, 4):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 404:
                return None   # grupo vacío, no es un error real
            r.raise_for_status()
            stats["requests"] += 1
            time.sleep(DELAY_SEC)
            return r.content if binary else r.text
        except requests.RequestException as exc:
            stats["errores"] += 1
            print(f"    ⚠  intento {intento}/3 — {exc}")
            time.sleep(1.5 * intento)
    return None


def get_json(path: str) -> dict | None:
    raw = _get(f"{BASE_URL}{path}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON inválido en {path}: {e}")
        return None


def get_csv(path: str) -> str | None:
    return _get(f"{BASE_URL}{path}")


def safe_filename(text: str) -> str:
    """Convierte un nombre a algo seguro para el sistema de archivos."""
    return "".join(c if c.isalnum() or c in "-_ " else "" for c in text).strip().replace(" ", "_")


# ── 1. Última actualización ────────────────────────────────────────────────────
def check_last_updated():
    raw = _get(f"{BASE_URL}/last-updated.txt")
    ts = raw.strip() if raw else "desconocido"
    print(f"  Última actualización del servidor : {ts}")
    return ts


# ── 2. Categorías ─────────────────────────────────────────────────────────────
def get_pokemon_categories() -> list[dict]:
    data = get_json("/tcgplayer/categories")
    if not data:
        print("  ✗ No se pudieron obtener las categorías.")
        sys.exit(1)

    all_cats = data.get("results", [])
    print(f"  Total categorías en TCGplayer  : {data.get('totalItems', '?')}")

    # Filtrar por nombre — incluye variaciones de idioma
    pokemon_cats = []
    for cat in all_cats:
        name_lower = (cat.get("name", "") + cat.get("displayName", "")).lower()
        if "pokemon" in name_lower and (cat["categoryId"] not in SKIP_CATS):
            pokemon_cats.append(cat)

    print(f"  Categorias Pokemon encontradas : {len(pokemon_cats)}")
    for cat in pokemon_cats:
        print(f"    -> id={cat['categoryId']:>4}  nombre='{cat['name']}'  "
              f"displayName='{cat['displayName']}'")
    return pokemon_cats


# ── 3. Grupos por categoría ───────────────────────────────────────────────────
def get_groups(category_id: int) -> list[dict]:
    data = get_json(f"/tcgplayer/{category_id}/groups")
    if not data:
        return []
    return data.get("results", [])


# ── 4. Descargar ProductsAndPrices.csv ────────────────────────────────────────
def download_group_csv(category_id: int, group: dict, output_dir: Path) -> int:
    """Descarga el CSV combinado de un grupo. Devuelve el número de filas."""
    group_id   = group["groupId"]
    group_name = safe_filename(group["name"])[:60]
    dest       = output_dir / f"{group_id}_{group_name}.csv"

    # Resume: saltar si ya existe y no está vacío
    if dest.exists() and dest.stat().st_size > 0:
        lines = dest.read_text(encoding="utf-8").count("\n") - 1
        return lines

    csv_text = get_csv(f"/tcgplayer/{category_id}/{group_id}/ProductsAndPrices.csv")

    if csv_text is None:
        stats["grupos_skip"] += 1
        return 0

    dest.write_text(csv_text, encoding="utf-8")
    row_count = csv_text.count("\n") - 1   # menos el header
    stats["grupos_ok"] += 1
    stats["filas_csv"] += row_count
    return row_count


# ── 5. Resumen de lo ya descargado ────────────────────────────────────────────
def mostrar_resumen():
    if not OUTPUT_DIR.exists():
        print("  No hay datos descargados todavía. Ejecuta sin --resumen primero.")
        return

    cats_file = OUTPUT_DIR / "categories.json"
    if not cats_file.exists():
        print("  No se encontró categories.json.")
        return

    cats = json.loads(cats_file.read_text(encoding="utf-8"))
    print(f"\n  Categorías Pokemon : {len(cats)}")

    total_grupos = 0
    total_csvs   = 0
    total_filas  = 0

    for cat in cats:
        cat_id  = cat["categoryId"]
        cat_dir = OUTPUT_DIR / str(cat_id)
        groups_file = cat_dir / "groups.json"

        if not groups_file.exists():
            continue

        groups = json.loads(groups_file.read_text(encoding="utf-8"))
        csvs   = list(cat_dir.glob("*.csv"))
        filas  = 0
        for csv_path in csvs:
            filas += csv_path.read_text(encoding="utf-8").count("\n") - 1

        total_grupos += len(groups)
        total_csvs   += len(csvs)
        total_filas  += filas

        print(f"\n  {cat['displayName']} (id={cat_id})")
        print(f"    Grupos   : {len(groups)}")
        print(f"    CSVs     : {len(csvs)}")
        print(f"    Filas    : {filas:,}")

    print(f"\n  ─────────────────────────────────────")
    print(f"  Total grupos    : {total_grupos:,}")
    print(f"  Total CSVs      : {total_csvs:,}")
    print(f"  Total filas     : {total_filas:,}")
    print(f"  Directorio      : {OUTPUT_DIR.resolve()}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Exploración empírica de Pokemon TCG via TCGCSV API"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Solo lista grupos sin descargar nada"
    )
    parser.add_argument(
        "--resumen", action="store_true",
        help="Muestra resumen de datos ya descargados y sale"
    )
    parser.add_argument(
        "--categoria", type=int, default=None,
        help="Procesar solo esta categoryId (ej: --categoria 3)"
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  TCGCSV — Exploración empírica de Pokemon TCG")
    print("=" * 60)

    if args.resumen:
        mostrar_resumen()
        return

    # ── Verificar servidor ────────────────────────────────────────
    print("\n[1] Estado del servidor")
    check_last_updated()

    # ── Descubrir categorías Pokemon ─────────────────────────────
    print("\n[2] Categorías Pokemon en TCGplayer")
    pokemon_cats = get_pokemon_categories()

    if args.categoria:
        pokemon_cats = [c for c in pokemon_cats if c["categoryId"] == args.categoria]
        if not pokemon_cats:
            print(f"  ✗ No se encontró categoryId={args.categoria} entre las categorías Pokemon.")
            sys.exit(1)

    if args.dry_run:
        # Modo listado: mostrar grupos sin descargar
        print("\n[DRY-RUN] Grupos por categoría (sin descargar)\n")
        for cat in pokemon_cats:
            cat_id = cat["categoryId"]
            groups = get_groups(cat_id)
            print(f"  {cat['displayName']} (id={cat_id}) - {len(groups)} grupos")
            for g in groups:
                print(f"    groupId={g['groupId']:>6}  abbr={g['abbreviation']:<12}  {g['name']}")
        print(f"\n  Total requests realizados : {stats['requests']}")
        return

    # ── Descarga completa ─────────────────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Guardar categorías encontradas
    (OUTPUT_DIR / "categories.json").write_text(
        json.dumps(pokemon_cats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n[3] Descargando grupos y CSVs → {OUTPUT_DIR}/")

    for cat in pokemon_cats:
        cat_id   = cat["categoryId"]
        cat_name = cat["displayName"]
        cat_dir  = OUTPUT_DIR / str(cat_id)
        cat_dir.mkdir(exist_ok=True)

        print(f"  -- {cat_name} (categoryId={cat_id}) ------------------")

        # Obtener y guardar grupos
        groups = get_groups(cat_id)
        if not groups:
            print("    Sin grupos.")
            continue

        (cat_dir / "groups.json").write_text(
            json.dumps(groups, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"    {len(groups)} grupos encontrados")

        # Descargar CSV por grupo
        for i, group in enumerate(groups, 1):
            row_count = download_group_csv(cat_id, group, cat_dir)
            status = f"{row_count:>4} filas" if row_count > 0 else "vacio/skip"
            print(f"    [{i:>3}/{len(groups)}] {group['groupId']}  "
                  f"{group['abbreviation']:<12} {group['name'][:45]:<45} -> {status}")

    # ── Resumen final ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    print(f"  Requests realizados  : {stats['requests']}")
    print(f"  Errores HTTP         : {stats['errores']}")
    print(f"  Grupos descargados   : {stats['grupos_ok']}")
    print(f"  Grupos vacíos (404)  : {stats['grupos_skip']}")
    print(f"  Total filas de datos : {stats['filas_csv']:,}")
    print(f"  Directorio de salida : {OUTPUT_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
