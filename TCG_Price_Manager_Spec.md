# TCG Price Manager — Especificación Técnica

> **Versión:** 1.0.0  
> **Fecha:** 2026-06-27

---

## Stack tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.11+ |
| UI | PyQt6 | ≥ 6.7 |
| Base de datos | SQLite | stdlib |
| Fuzzy matching | rapidfuzz | ≥ 3.9 |
| HTTP | requests | ≥ 2.32 |
| Íconos | qtawesome (Font Awesome 6) | ≥ 1.3 |
| Score matrix | numpy (via rapidfuzz.process.cdist) | ≥ 1.26 |
| EXE packaging | PyInstaller | ≥ 6.0 |

---

## Arquitectura de módulos

```
tcg_app/
├── main.py                 Entry point + global exception handler
├── version.py              __version__ = "1.0.0"
└── app/
    ├── db/database.py      SQLite: conexión, schema, queries, upserts
    ├── api/
    │   ├── exchange.py     USD→CLP: open.er-api.com, caché 1h en settings
    │   └── tcgcsv.py       TCGCSV API client (download CSVs, check updates)
    ├── core/
    │   ├── fuzzy.py        Matching 2 fases: número exacto + fuzzy nombre
    │   ├── sync.py         CSV → SQLite (import_local_csvs, sync_from_api)
    │   ├── export.py       Exportar BatchItems → CSV UTF-8 BOM
    │   ├── images.py       Descargar imágenes alta res + batch concurrente
    │   ├── updater.py      Auto-actualización: check + download + replace EXE
    │   └── paths.py        Rutas unificadas para script mode vs frozen EXE
    └── ui/
        ├── theme.py        QSS dark theme + badge_style() + icon()
        ├── main_window.py  QMainWindow + QTabWidget + status bar
        ├── tab_sync.py     SyncTab: import/sync con QThread + progress
        ├── tab_search.py   SearchTab: filtros + QTableView + detail panel
        ├── tab_batch.py    BatchTab: input parsing + fuzzy + confirm + export
        ├── tab_settings.py SettingsTab: tasa CLP + DB stats + update section
        └── dialogs.py      FuzzyConfirmDialog: buscador manual + progreso
```

---

## Base de datos — Schema SQLite

```sql
categories (categoryId PK, name, displayName)
groups     (groupId PK, name, abbreviation, categoryId FK, publishedOn, modifiedOn, isSupplemental)
products   (productId PK, name, cleanName, imageUrl, categoryId, groupId FK,
            url, modifiedOn, imageCount,
            extCardText, extRarity, extNumber, extCardType, extHP, extStage,
            extAttack1, extAttack2, extWeakness, extResistance, extRetreatCost,
            extUPC, extDescription)
prices     (id PK, productId FK, subTypeName, lowPrice, midPrice, highPrice,
            marketPrice, directLowPrice)   UNIQUE(productId, subTypeName)
sync_log   (id PK, synced_at, category_id, groups_synced, rows_processed, status)
settings   (key PK, value, updated_at)
```

**Índices:** `idx_products_name`, `idx_products_cleanName`, `idx_products_extNumber`, `idx_products_groupId`, `idx_products_categoryId`, `idx_prices_productId`

**Settings keys:** `usd_clp_rate`, `usd_clp_updated_at`, `last_sync_at`, `update_url`

---

## Fuzzy matching — 2 fases

### Fase 1: Lookup por número exacto

```
Query: "Dragapult ex 073/131"
  │
  ├─ _extract_query_number()  →  "073/131"
  ├─ _get_number_index()      →  {extNumber → [candidates]}  (cacheado por id(candidates))
  ├─ hits = index["073/131"]
  ├─ best_sim = max(token_sort_ratio(normalize(query_name), normalize(hit.name)) for hit)
  └─ best_sim ≥ 50%  →  score 85/95/100, confirmed
```

**Score por number match:**
- name_sim ≥ 85% → score 100 (auto-confirm)
- name_sim ≥ 70% → score 95 (auto-confirm)
- name_sim ≥ 50% → score 85 (auto-confirm)
- name_sim < 50% → no match, fallback a Fase 2

### Fase 2: Fuzzy por nombre (fallback)

```
process.cdist(norm_queries, keys, scorer=token_sort_ratio, workers=-1)
  │
  └─ Matriz N×62k scores, paralelo en todos los CPUs
     │
     └─ Top-K por fila → score ≥ 90 = confirmed, < 90 = review
```

**Caches:**
- `_key_cache`: normalized keys list (rebuilt cuando cambia id(candidates))
- `_num_index_cache`: number → candidates index (id-based)

### Normalización `normalize(text)`

1. Lowercase
2. Remover apostrofes `'` `'`
3. Remover código al final: `\d{1,4}/\d{1,4}` y bare `\d{1,3}`
4. Remover puntuación restante
5. Colapsar espacios

---

## Input batch — Parser y preprocesador

### `parse_batch_line(line)`
Separa la primera columna (card query) de metadata tab-separada:
```
"Raging Bolt ex 123/162\tIdioma\tEN\tRareza\tDouble Rare"
  → query="Raging Bolt ex 123/162", meta={"idioma":"EN","rareza":"Double Rare"}
```

### `_merge_multiline_input(text)`
Detecta el formato donde tabs → newlines (frecuente al pegar desde apps):
```
# 5 líneas separadas (tabs perdidos)  →  1 línea tab-separada
Raging Bolt ex 123/162              Raging Bolt ex 123/162\tIdioma\tEN\tRareza\tDouble Rare
Idioma                        →
EN
Rareza
Double Rare
```
**Detección:** si ≥ 15% de líneas son claves conocidas ("idioma", "rareza", etc.) → modo multi-línea. Grupos de 5 líneas consecutivas.

---

## Exportación CSV

**Encoding:** UTF-8 BOM (`utf-8-sig`) → compatible con Excel al doble clic.

**Columnas:** Input original, Estado, Idioma (input), Rareza (input), productId, Nombre oficial, Nombre limpio, Código, Rareza (DB), Tipo de carta, HP, Etapa, Set, Abreviación, Variante, Low/Mid/Market/Direct USD, Low/Mid/Market/Direct CLP, URL imagen, URL TCGplayer.

**Filas:** Una por (producto × variante de precio). Un producto con Normal + Holofoil genera 2 filas.

---

## Conversión USD→CLP

- API: `https://open.er-api.com/v6/latest/USD` (gratuita, sin clave)
- Caché en settings: `usd_clp_rate` + `usd_clp_updated_at`
- TTL: 60 minutos
- Fallback: si sin internet → usar última tasa guardada
- Fallback de último recurso: 900.0 CLP/USD (constante)

---

## Auto-actualización

Solo disponible en modo EXE (frozen). En modo script, muestra "usa git pull".

**Flujo:**
1. `GET {update_url}` → JSON `{version, download_url, release_notes}`
2. Comparar versiones (tuple comparison)
3. Si nueva versión → diálogo con release notes
4. Descargar EXE nuevo a `_TCGPriceManager_update.exe`
5. Crear `_update_launcher.bat` que: espera, reemplaza EXE, relanza
6. `subprocess.Popen(bat)` + `sys.exit(0)`

**URL por defecto:** `https://raw.githubusercontent.com/youruser/tcgpricemanager/main/version.json`
(Configurable en settings → `update_url`)

---

## Empaquetado EXE

```bash
pyinstaller build/TCGPriceManager.spec --clean --noconfirm
```

**Incluye:**
- Python runtime
- PyQt6 + Qt6 DLLs
- qtawesome fonts (Font Awesome 6)
- `tcg_app/assets/icon.ico`
- Todos los módulos del proyecto

**Excluye:** tkinter, matplotlib, scipy, pandas (reducen tamaño)

**Resultado:** `dist/TCG Price Manager.exe` (~62 MB, standalone)

**Paths en modo frozen:**
- DB: `%APPDATA%\TCGPriceManager\tcg.db`
- CSVs: `<exe_dir>/output_pokemon_tcg/`
- Imágenes: `<exe_dir>/downloads/`
- Assets: `sys._MEIPASS/assets/`

---

## Tests

```bash
.venv\Scripts\pytest tests/ -v
# 59 passed, 4 warnings
```

| Archivo | Cobertura |
|---|---|
| `test_normalize.py` (14) | Casos borde de normalize(): apostrofes, números, unicode |
| `test_fuzzy.py` (13) | search_single, batch_search, number extraction, scores |
| `test_database.py` (17) | Schema, upserts, búsquedas, precios, settings, DB stats |
| `test_sync.py` (9) | _import_csv_file, deduplicación, import_local_csvs integración |
| `test_export.py` (6) | Headers, UTF-8 BOM, múltiples variantes, CLP, not_found |

**Fixture:** `mem_conn` — SQLite en archivo temporal, tablas + datos FK pre-poblados.

---

## Diseño visual

**Tema:** Oscuro profesional (inspirado en GitHub Dark)

```python
BG      = "#0d1117"   # fondo principal
SURFACE = "#161b22"   # tarjetas, paneles
BORDER  = "#30363d"   # bordes
ACCENT  = "#58a6ff"   # botones primarios, links
SUCCESS = "#3fb950"   # ✓ confirmado
WARNING = "#d29922"   # ⚠ revisar
DANGER  = "#f85149"   # ✗ error
TEXT    = "#e6edf3"   # texto principal
MUTED   = "#7d8590"   # texto secundario
```

**Fuente:** Segoe UI (10pt body, 14pt títulos)  
**Íconos:** Font Awesome 6 Solid via qtawesome  
**Tablas:** Filas alternadas, row height 56px (para miniaturas en batch)

---

## Fuente de datos

- **TCGCSV** (`https://tcgcsv.com`) — caché diaria de TCGplayer API
- **Categorías soportadas:** Pokemon (id=3, inglés) + Pokemon Japan (id=85)
- **Volumen:** ~62k productos, ~78k precios, 262 grupos activos
- **Actualización:** 1× al día (~20:00 UTC)
- **Rate limit:** máx. 10,000 requests/24h, 250ms entre requests, User-Agent obligatorio

Ver documentación completa de la API en [tcgcsv_api_docs.md](tcgcsv_api_docs.md).
