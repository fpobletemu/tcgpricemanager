# TCG Price Manager

Aplicación de escritorio para gestionar catálogos y precios de cartas Pokemon TCG (inglés y japonés).
Conecta con [TCGCSV](https://tcgcsv.com) — caché diaria de la API de TCGplayer.

---

## Características

| Feature | Descripción |
|---|---|
| **Sincronización** | Descarga y actualiza el catálogo completo desde TCGCSV (62k+ productos) |
| **Búsqueda individual** | Por nombre, código de carta o set, con precios en USD y CLP |
| **Búsqueda por lotes** | Pega una lista de cartas, matching automático con código exacto |
| **Matching inteligente** | Fase 1: código exacto → Fase 2: fuzzy por nombre. Distingue `Dragapult ex 073/131` de `Dragapult ex 160/217` |
| **Exportar CSV** | Lista confirmada con nombre oficial, código, rareza, set y precios USD/CLP |
| **Descargar imágenes** | Imágenes en alta resolución de las cartas de la lista |
| **Conversión USD→CLP** | Tasa en tiempo real desde `open.er-api.com` |
| **Funciona offline** | DB local SQLite — solo la sincronización requiere internet |

---

## Instalación rápida

### Requisitos
- Windows 10/11 (64-bit)
- Python 3.11 o superior

```bash
# 1. Clonar o descomprimir el proyecto
cd busquedastcgcsv

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 3. Generar ícono
python generate_icon.py

# 4. Crear acceso directo en el escritorio
python setup_shortcut.py

# 5. (Primera vez) Descargar datos de cartas
python explorar_pokemon_tcg.py
```

### Iniciar la app
- **Doble clic** en el ícono del escritorio **"TCG Price Manager"**
- O desde terminal: `.venv\Scripts\python tcg_app\main.py`

---

## Distribución como EXE (sin Python requerido)

```bash
build\build.bat
```
Genera `dist\TCG Price Manager.exe` (~62 MB, todo incluido).

Ver [INSTALL.md](INSTALL.md) para instrucciones completas de distribución.

---

## Uso

### Tab: Sincronización
- **"Importar CSVs locales"** → carga los CSVs ya descargados en `output_pokemon_tcg/`
- **"Sync desde API"** → descarga datos frescos desde TCGCSV y los importa

### Tab: Búsqueda
1. Escribir nombre, código o seleccionar set
2. Click en un resultado → panel derecho muestra imagen y precios por variante
3. **"Exportar CSV"** → guarda los resultados con todos los precios

### Tab: Por Lotes
1. Pegar lista de cartas (un ítem por línea):

```
Dragapult ex 160/217
Raging Bolt ex 123/162    Idioma    EN    Rareza    Double Rare
Lillie's Clefairy ex 076/217    Idioma    EN    Rareza    Double Rare
-----------------------------------
Charmander    idioma    ESP    rareza    Holo
```

> Acepta formato con tabs (desde Excel/hojas de cálculo) o con saltos de línea. Las líneas `---` se ignoran automáticamente.

2. Click **"Procesar lista"** (~1-2 segundos para 100 cartas)
3. Revisar los ítems marcados con ⚠ (score < 90)
4. **"Exportar CSV"** o **"Descargar imágenes"**

### Tab: Configuración
- Ver y actualizar tasa USD→CLP
- Estadísticas de la base de datos
- Buscar e instalar actualizaciones

---

## Formato de entrada por lotes

### Formatos soportados

| Formato | Ejemplo |
|---|---|
| Solo nombre | `Lugia VSTAR` |
| Nombre + código | `Lugia VSTAR 139/195` |
| Nombre + código abreviado | `Noctowl 141` |
| Con metadata (tabs) | `Raging Bolt ex 123/162⇥Idioma⇥EN⇥Rareza⇥Double Rare` |
| Con metadata (líneas) | Ver ejemplo arriba — 5 líneas por carta |

### Lógica de matching

El sistema usa matching en **2 fases**:

1. **Fase 1 — Código exacto:** Si el query tiene número (ej: `123/162`), busca primero la carta con ese extNumber exacto. `Dragapult ex 073/131` ≠ `Dragapult ex 160/217`.

2. **Fase 2 — Fuzzy por nombre:** Si no hay código o no se encontró, busca por similitud de nombre. Maneja typos, apostrofes y variaciones de capitalización.

### Score de confianza

| Score | Significado | Acción |
|---|---|---|
| ≥ 90 | Auto-confirmado | ✓ verde |
| 70–89 | Revisar | ⚠ amarillo |
| < 70 | Bajo | ✗ rojo |

---

## CSV exportado — columnas

| Columna | Descripción |
|---|---|
| Input original | Texto tal como lo ingresaste |
| Estado | Confirmado / Pendiente / No encontrado |
| Idioma (input) | Valor del campo Idioma de tu lista |
| Rareza (input) | Valor del campo Rareza de tu lista |
| Nombre oficial | Nombre normalizado en la DB |
| Código | extNumber (ej: `139/195`) |
| Rareza (DB) | Rareza oficial de TCGplayer |
| Set | Nombre del set/expansión |
| Variante | Normal / Holofoil / Reverse Holofoil / etc. |
| Low / Mid / Market / Direct USD | Precios en dólares |
| Low / Mid / Market / Direct CLP | Precios convertidos a pesos chilenos |
| URL imagen | Link a imagen en CDN de TCGplayer |
| URL TCGplayer | Link a la página del producto |

---

## Estructura del proyecto

```
busquedastcgcsv/
│
├── tcg_app/                    ← Aplicación principal
│   ├── main.py                 ← Entry point
│   ├── version.py              ← __version__ = "1.0.0"
│   ├── assets/icon.ico         ← Ícono de la app
│   └── app/
│       ├── db/database.py      ← SQLite: schema, queries
│       ├── api/
│       │   ├── exchange.py     ← Tasa USD→CLP (open.er-api.com)
│       │   └── tcgcsv.py       ← Cliente TCGCSV API
│       ├── core/
│       │   ├── fuzzy.py        ← Matching en 2 fases (número + nombre)
│       │   ├── sync.py         ← Importar CSVs → SQLite
│       │   ├── export.py       ← Exportar CSV
│       │   ├── images.py       ← Descargar imágenes
│       │   ├── updater.py      ← Auto-actualización
│       │   └── paths.py        ← Rutas (script vs EXE)
│       └── ui/
│           ├── theme.py        ← QSS dark theme
│           ├── main_window.py  ← Ventana principal
│           ├── tab_sync.py     ← Tab Sincronización
│           ├── tab_search.py   ← Tab Búsqueda
│           ├── tab_batch.py    ← Tab Por Lotes
│           ├── tab_settings.py ← Tab Configuración
│           └── dialogs.py      ← Diálogo de confirmación fuzzy
│
├── output_pokemon_tcg/         ← CSVs descargados de TCGCSV (~237 archivos)
├── downloads/                  ← Imágenes descargadas
├── tests/                      ← Tests pytest (59 tests)
├── build/                      ← Spec y script de compilación EXE
├── dist/                       ← EXE compilado
│
├── explorar_pokemon_tcg.py     ← Script de descarga inicial de CSVs
├── generate_icon.py            ← Genera icon.ico
├── setup_shortcut.py           ← Crea acceso directo en escritorio
├── requirements.txt            ← Dependencias Python
└── tcgcsv_api_docs.md          ← Documentación de la API de TCGCSV
```

---

## Dependencias

| Paquete | Versión | Uso |
|---|---|---|
| PyQt6 | ≥ 6.7 | Interfaz gráfica |
| rapidfuzz | ≥ 3.9 | Matching fuzzy paralelo |
| requests | ≥ 2.32 | HTTP (API, imágenes) |
| qtawesome | ≥ 1.3 | Íconos Font Awesome 6 |
| Pillow | ≥ 10.4 | Generación del ícono |
| numpy | ≥ 1.26 | Matriz de scores (process.cdist) |
| pyinstaller | ≥ 6.0 | Compilar EXE |

---

## Tests

```bash
.venv\Scripts\pytest tests/ -v
```

| Archivo | Tests | Qué cubre |
|---|---|---|
| `test_normalize.py` | 14 | Normalización de nombres (apostrofes, códigos, mayúsculas) |
| `test_fuzzy.py` | 13 | search_single, batch_search, scores |
| `test_database.py` | 17 | Schema, CRUD, búsquedas, precios, settings |
| `test_sync.py` | 9 | Importación CSV, deduplicación, integración |
| `test_export.py` | 6 | Exportación CSV, BOM, columnas, precios CLP |

---

## Datos soportados

| Categoría | ID | Grupos | Productos |
|---|---|---|---|
| Pokemon (inglés) | 3 | 217 | ~50k |
| Pokemon Japan | 85 | 45 activos | ~12k |
| **Total** | | **262** | **~62k** |

Fuente: [TCGCSV](https://tcgcsv.com) — actualización diaria desde la API de TCGplayer.
