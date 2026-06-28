# TCGCSV API — Documentación

> Fuente oficial: https://tcgcsv.com/docs  
> Actualización: una vez al día (build diario)

---

## Índice

1. [Guía de Uso](#guía-de-uso)
2. [Formato de Respuesta General](#formato-de-respuesta-general)
3. [Endpoints JSON](#endpoints-json)
   - [last-updated.txt](#last-updatedtxt)
   - [Categories Collection](#categories-collection)
   - [Groups Collection](#groups-collection)
   - [Products Collection](#products-collection)
   - [Market Prices Collection](#market-prices-collection)
4. [Endpoints CSV](#endpoints-csv)
   - [Categories.csv](#categoriesscsv)
   - [Groups.csv](#groupscsv)
   - [ProductsAndPrices.csv](#productsandpricesscsv)
5. [Notas sobre Campos](#notas-sobre-campos)
6. [Historial de Precios (Archivo)](#historial-de-precios-archivo)
7. [FAQ — Preguntas Frecuentes](#faq--preguntas-frecuentes)

---

## Guía de Uso

- TCGCSV se actualiza **exactamente una vez al día**.
- Antes de hacer un sync completo, consultar primero `last-updated.txt` y comparar el timestamp con el último pull exitoso.
- Limitar las solicitudes a **una vez cada 24 horas**.
- Un sync completo no debería requerir más de **10.000 requests**. Superar ese número puede resultar en un baneo.

### Headers requeridos

```
User-Agent: YourApplication/X.Y.Z
```
Ejemplo: `User-Agent: CatalogBuilder/1.2.0`  
Las requests con User-Agent genérico o ausente pueden ser bloqueadas.

### Rate limiting

- Incluir un `sleep(100ms)` entre requests en el loop de actualización.
- Exceder el umbral de requests por segundo resulta en **throttling de 10 minutos** de la IP.

### CORS

TCGCSV tiene una **política CORS restrictiva**. Las requests desde el navegador (fetch / XHR del lado del cliente) fallarán. Este servicio está diseñado para ser consumido desde **back-end o scripts server-side**.

---

## Formato de Respuesta General

Casi todos los endpoints devuelven el siguiente formato:

```json
{
    "totalItems": 440,
    "success": true,
    "errors": [],
    "results": [
        // ...
    ]
}
```

| Campo        | Tipo     | Descripción                                              |
|--------------|----------|----------------------------------------------------------|
| `totalItems` | int32    | Total de objetos en `results`. Ausente en Market Prices. |
| `success`    | boolean  | Indica si la request fue exitosa.                        |
| `errors`     | list     | Lista de descripciones de error si `success` es false.  |
| `results`    | list     | Array de objetos JSON con los datos.                     |

---

## Endpoints JSON

### last-updated.txt

Contiene un único timestamp de la última build. Usarlo para evitar syncs innecesarios.

```
GET https://tcgcsv.com/last-updated.txt
```

---

### Categories Collection

Las categorías equivalen aproximadamente a un juego de cartas o colección de mercancía (ej: Pokémon, Magic: The Gathering).

```
GET https://tcgcsv.com/tcgplayer/categories
```

**Ejemplo:** https://tcgcsv.com/tcgplayer/categories

#### Ejemplo de respuesta

```json
{
    "totalItems": 89,
    "success": true,
    "errors": [],
    "results": [
        {
            "categoryId": 3,
            "name": "Pokemon",
            "modifiedOn": "2025-11-19T15:58:35.27",
            "displayName": "Pokemon",
            "seoCategoryName": "Pokemon",
            "categoryDescription": "...",
            "categoryPageTitle": "TCGplayer - Buy Pokémon TCG Cards, Singles, and Pack",
            "sealedLabel": "Sealed Products",
            "nonSealedLabel": "Single Cards",
            "conditionGuideUrl": "https://store.tcgplayer.com/help/cardconditionguide",
            "isScannable": true,
            "popularity": 576635,
            "isDirect": true
        }
    ]
}
```

#### Campos

| Campo                | Tipo              | Descripción                                                                                   |
|----------------------|-------------------|-----------------------------------------------------------------------------------------------|
| `categoryId`         | int32             | ID único incremental. Seguro como primary key.                                                |
| `name`               | string            | Nombre interno. A veces abreviado (ej: "Magic" en lugar de "Magic: The Gathering").           |
| `modifiedOn`         | string            | Timestamp de última actualización. Zona horaria desconocida.                                  |
| `displayName`        | string            | Nombre para mostrar al usuario.                                                               |
| `seoCategoryName`    | string            | Nombre para SEO. Puede expandir siglas o reemplazar "&" por "and".                           |
| `categoryDescription`| string (nullable) | Texto de marketing que describe la categoría.                                                 |
| `categoryPageTitle`  | string (nullable) | Título de la página de TCGplayer para la categoría.                                           |
| `sealedLabel`        | string (nullable) | Valores posibles: `"Sealed Product"`, `"Sealed Products"`, `"Bulk Lot"`, `null`              |
| `nonSealedLabel`     | string (nullable) | Múltiples valores posibles: `"Single Cards"`, `"Singles"`, `"Products"`, etc.                |
| `conditionGuideUrl`  | string            | URL a la guía de condición de la categoría.                                                   |
| `isScannable`        | boolean           | Si los productos pueden escanearse con la app de TCGplayer.                                   |
| `popularity`         | int32             | Valor relativo de popularidad/ranking.                                                        |
| `isDirect`           | boolean           | Si los productos pueden comprarse via TCGplayer Direct.                                       |

---

### Groups Collection

Los grupos representan colecciones de productos dentro de una categoría. Equivalen aproximadamente a una **expansión o set** de un juego.

```
GET https://tcgcsv.com/tcgplayer/{categoryId}/groups
```

**Ejemplo:** https://tcgcsv.com/tcgplayer/3/groups  
_(categoryId 3 = Pokémon)_

#### Ejemplo de respuesta

```json
{
    "totalItems": 212,
    "success": true,
    "errors": [],
    "results": [
        {
            "groupId": 3170,
            "name": "SWSH12: Silver Tempest",
            "abbreviation": "SWSH12",
            "isSupplemental": false,
            "publishedOn": "2022-11-11T00:00:00",
            "modifiedOn": "2025-12-12T22:37:34.34",
            "categoryId": 3
        }
    ]
}
```

#### Campos

| Campo            | Tipo    | Descripción                                                                                                     |
|------------------|---------|-----------------------------------------------------------------------------------------------------------------|
| `groupId`        | int32   | ID único incremental. Seguro como primary key.                                                                  |
| `name`           | string  | Nombre del grupo/set.                                                                                           |
| `abbreviation`   | string  | Abreviación del set. Usable para búsquedas de Mass Entry.                                                      |
| `isSupplemental` | boolean | Indica si es un grupo "suplementario". TCGplayer aplica este valor de forma inconsistente. Se recomienda ignorar.|
| `publishedOn`    | string  | Timestamp de creación del grupo. Zona horaria desconocida.                                                      |
| `modifiedOn`     | string  | Timestamp de última actualización. Se actualiza cuando se agregan/eliminan productos.                           |
| `categoryId`     | int32   | Referencia a la categoría padre.                                                                                |

---

### Products Collection

Los productos representan cartas individuales, cajas selladas, packs, code cards, etc. Incluyen `extendedData` con información específica de cada categoría (rareza, número de carta, texto, etc.).

```
GET https://tcgcsv.com/tcgplayer/{categoryId}/{groupId}/products
```

**Ejemplo:** https://tcgcsv.com/tcgplayer/3/3170/products

> Internamente consulta el endpoint de TCGplayer con `getExtendedFields=true`.

#### Ejemplo de respuesta

```json
{
    "totalItems": 254,
    "success": true,
    "errors": [],
    "results": [
        {
            "productId": 451396,
            "name": "Lugia VSTAR",
            "cleanName": "Lugia VSTAR",
            "imageUrl": "https://tcgplayer-cdn.tcgplayer.com/product/451396_200w.jpg",
            "categoryId": 3,
            "groupId": 3170,
            "url": "https://www.tcgplayer.com/product/451396/pokemon-swsh12-silver-tempest-lugia-vstar",
            "modifiedOn": "2025-12-04T15:00:29.8",
            "imageCount": 1,
            "presaleInfo": {
                "isPresale": false,
                "releasedOn": null,
                "note": null
            },
            "extendedData": [
                { "name": "Number",    "displayName": "Card Number", "value": "139/195" },
                { "name": "Rarity",    "displayName": "Rarity",      "value": "Ultra Rare" },
                { "name": "Card Type", "displayName": "Card Type",   "value": "Colorless" },
                { "name": "HP",        "displayName": "HP",          "value": "280" },
                { "name": "Stage",     "displayName": "Stage",       "value": "VSTAR" },
                { "name": "CardText",  "displayName": "Card Text",   "value": "..." },
                { "name": "Attack 1",  "displayName": "Attack 1",    "value": "[4] Tempest Dive (220)..." },
                { "name": "Weakness",  "displayName": "Weakness",    "value": "Lx2" },
                { "name": "Resistance","displayName": "Resistance",  "value": "F-30" },
                { "name": "RetreatCost","displayName": "Retreat Cost","value": "2" }
            ]
        }
    ]
}
```

#### Campos principales

| Campo         | Tipo              | Descripción                                                                                          |
|---------------|-------------------|------------------------------------------------------------------------------------------------------|
| `productId`   | int32             | ID único incremental. Seguro como primary key.                                                       |
| `name`        | string            | Nombre del producto o carta.                                                                         |
| `cleanName`   | string (nullable) | Nombre sin caracteres especiales `()[]&-'!?/:` etc.                                                 |
| `imageUrl`    | string            | URL a la CDN de imágenes. Reemplazar `_200w` por `_in_1000x1000` para mayor resolución.             |
| `categoryId`  | int32             | Referencia a la categoría.                                                                           |
| `groupId`     | int32             | Referencia al grupo/set.                                                                             |
| `url`         | string            | URL a la página del producto en TCGplayer.                                                           |
| `modifiedOn`  | string            | Timestamp de última actualización. Zona horaria desconocida.                                         |
| `imageCount`  | int32             | Cantidad de imágenes disponibles. Generalmente entre 0 y 6.                                          |
| `presaleInfo` | object            | Ver subcampos abajo.                                                                                 |
| `extendedData`| list              | Array de pares key-value con información adicional específica de categoría.                          |

#### Subcampos de `presaleInfo`

| Campo        | Tipo              | Descripción                                                              |
|--------------|-------------------|--------------------------------------------------------------------------|
| `isPresale`  | boolean           | Si el producto aún no está disponible para entrega inmediata.            |
| `releasedOn` | string (nullable) | Timestamp estimado de lanzamiento (zona horaria desconocida).           |
| `note`       | string (nullable) | Nota sobre fechas de envío estimadas.                                    |

#### Subcampos de `extendedData`

| Campo         | Tipo   | Descripción                                           |
|---------------|--------|-------------------------------------------------------|
| `name`        | string | Clave de la propiedad.                                |
| `displayName` | string | Nombre legible para mostrar.                          |
| `value`       | string | Valor de la propiedad.                                |

> **Tip:** Para determinar si un producto es una carta (vs. producto sellado), verificar si `extendedData` contiene una propiedad `Rarity` o `Number`.

> **Nota:** No existe un meta-endpoint que liste qué `extendedData` se puede esperar por categoría. Es necesario muestrear productos para inspeccionarlos.

---

### Market Prices Collection

Precios de mercado por producto. Un producto puede tener **múltiples objetos de precio** (uno por variante/foil). Necesita unirse con la colección de Productos via `productId`.

```
GET https://tcgcsv.com/tcgplayer/{categoryId}/{groupId}/prices
```

**Ejemplo:** https://tcgcsv.com/tcgplayer/3/3170/prices

> Internamente consulta el endpoint `Product Prices by Group` de TCGplayer.

#### Ejemplo de respuesta

```json
{
    "success": true,
    "errors": [],
    "results": [
        {
            "productId": 451784,
            "lowPrice": 0.10,
            "midPrice": 0.51,
            "highPrice": 25.51,
            "marketPrice": 0.53,
            "directLowPrice": 0.44,
            "subTypeName": "Holofoil"
        },
        {
            "productId": 451784,
            "lowPrice": 0.35,
            "midPrice": 0.70,
            "highPrice": 2.99,
            "marketPrice": 0.74,
            "directLowPrice": null,
            "subTypeName": "Reverse Holofoil"
        }
    ]
}
```

> **Nota:** Esta colección **no incluye** el campo `totalItems`.  
> Todos los precios están en **USD (dólares estadounidenses)**.

#### Campos

| Campo            | Tipo              | Descripción                                                                                                                                    |
|------------------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `productId`      | int32             | ID del producto. **No es seguro como primary key solo**. Usar como clave compuesta con `subTypeName`.                                         |
| `lowPrice`       | double            | Precio más bajo listado, sin contar condición ni envío.                                                                                        |
| `midPrice`       | double            | Precio mediano de los listings. La diferencia entre `midPrice` y `marketPrice` suele ser el dato más relevante.                               |
| `highPrice`      | double            | Precio más alto listado. Generalmente poco útil debido al "price parking" (listados artificialmente altos).                                    |
| `marketPrice`    | double (nullable) | Precio al que la carta **ha estado vendiéndose** recientemente. Puede ser null en cartas con muy bajo volumen de ventas.                       |
| `directLowPrice` | double (nullable) | Precio más bajo disponible a través del programa TCGplayer Direct. Incluye un pequeño premium por el servicio de envío unificado.             |
| `subTypeName`    | string            | Nombre de la variante/impresión. Necesario cuando un producto tiene múltiples precios. Ejemplos: `Normal`, `Holofoil`, `Reverse Holofoil`.    |

---

## Notas sobre Campos

- **Timestamps (`modifiedOn`, `publishedOn`):** La zona horaria es desconocida. Los timestamps de `modifiedOn` se actualizan con frecuencia, posiblemente al agregar/eliminar productos.
- **`marketPrice`:** Refleja el precio de venta reciente. En cartas nuevas tiende a centrarse en condición NM/LP. En cartas antiguas puede incluir condiciones HP.
- **`highPrice`:** Poco confiable debido a "price parking" (vendedores que listan a precios irreales sin intención de vender).
- **Primary keys recomendadas:**
  - `categoryId` → Categories
  - `groupId` → Groups
  - `productId` → Products
  - `(productId, subTypeName)` → Prices (clave compuesta)

---

---

## Endpoints CSV

Además del formato JSON, TCGCSV ofrece archivos **CSV pre-generados** para descarga directa. Estos son la razón del nombre del sitio. Los CSVs se regeneran una vez al día junto al resto del contenido.

> **Importante:** Los nombres de los archivos son **case-sensitive** (mayúsculas obligatorias en la primera letra).

### Categories.csv

```
GET https://tcgcsv.com/tcgplayer/Categories.csv
```

Equivalente CSV del endpoint `/tcgplayer/categories`. Contiene todas las categorías disponibles.

---

### Groups.csv

```
GET https://tcgcsv.com/tcgplayer/{categoryId}/Groups.csv
```

**Ejemplo:** https://tcgcsv.com/tcgplayer/3/Groups.csv  
El archivo descargado se llama `{CategoryName}Groups.csv` (ej: `PokemonGroups.csv`).

Equivalente CSV del endpoint `/tcgplayer/{categoryId}/groups`.

---

### ProductsAndPrices.csv

```
GET https://tcgcsv.com/tcgplayer/{categoryId}/{groupId}/ProductsAndPrices.csv
```

**Ejemplo:** https://tcgcsv.com/tcgplayer/3/3170/ProductsAndPrices.csv  
El archivo descargado se llama `{GroupName}ProductsAndPrices.csv` (ej: `SWSH12SilverTempestProductsAndPrices.csv`).

Este es el CSV más importante: **combina productos y precios en una sola tabla**. Los campos de `extendedData` del JSON se aplanan como columnas individuales con el prefijo `ext`.

> **Nota:** No existen `Products.csv` ni `Prices.csv` por separado. El CSV combinado es el único disponible a nivel de grupo.

#### Columnas de ProductsAndPrices.csv

| Columna           | Fuente          | Descripción                                              |
|-------------------|-----------------|----------------------------------------------------------|
| `productId`       | Products        | ID único del producto                                    |
| `name`            | Products        | Nombre del producto                                      |
| `cleanName`       | Products        | Nombre sin caracteres especiales                         |
| `imageUrl`        | Products        | URL de la imagen en la CDN de TCGplayer                  |
| `categoryId`      | Products        | ID de la categoría                                       |
| `groupId`         | Products        | ID del grupo/set                                         |
| `url`             | Products        | URL del producto en TCGplayer                            |
| `modifiedOn`      | Products        | Timestamp de última modificación                         |
| `imageCount`      | Products        | Número de imágenes disponibles                           |
| `lowPrice`        | Prices          | Precio más bajo listado (USD)                            |
| `midPrice`        | Prices          | Precio mediano (USD)                                     |
| `highPrice`       | Prices          | Precio más alto listado (USD)                            |
| `marketPrice`     | Prices          | Precio de mercado real (USD), puede ser vacío            |
| `directLowPrice`  | Prices          | Precio más bajo via TCGplayer Direct (USD)               |
| `subTypeName`     | Prices          | Variante del producto (Normal, Holofoil, etc.)           |
| `extCardText`     | extendedData    | Texto de la carta (puede incluir HTML)                   |
| `extUPC`          | extendedData    | Código de barras UPC (principalmente en productos sellados)|
| `extRarity`       | extendedData    | Rareza de la carta                                       |
| `extNumber`       | extendedData    | Número de carta en el set (ej: `139/195`)                |
| `extCardType`     | extendedData    | Tipo de energía/carta (ej: Colorless, Fire)              |
| `extHP`           | extendedData    | Puntos de vida de la carta                               |
| `extStage`        | extendedData    | Etapa de evolución (Basic, Stage 1, VSTAR, etc.)         |
| `extAttack1`      | extendedData    | Primer ataque                                            |
| `extAttack2`      | extendedData    | Segundo ataque                                           |
| `extWeakness`     | extendedData    | Debilidad                                                |
| `extResistance`   | extendedData    | Resistencia                                              |
| `extRetreatCost`  | extendedData    | Costo de retirada                                        |

> Los campos `ext*` disponibles varían según la categoría. Los listados arriba corresponden a Pokémon (categoryId=3). Otras categorías tendrán columnas `ext*` diferentes.

---

## Historial de Precios (Archivo)

TCGCSV mantiene un **archivo histórico de precios** en formato comprimido desde el **8 de febrero de 2024**.

### URL del archivo

```
https://tcgcsv.com/archive/tcgplayer/prices-{YYYY-MM-DD}.ppmd.7z
```

**Ejemplos:**
- https://tcgcsv.com/archive/tcgplayer/prices-2024-02-08.ppmd.7z
- https://tcgcsv.com/archive/tcgplayer/prices-2024-02-09.ppmd.7z

### Cómo extraer

Requiere [7-Zip](https://www.7-zip.org/download.html).

```bash
# Descargar el archivo de una fecha específica
curl -O https://tcgcsv.com/archive/tcgplayer/prices-2024-02-08.ppmd.7z

# Extraer
7z x prices-2024-02-08.ppmd.7z

# Acceder a los precios (estructura: {fecha}/{categoryId}/{groupId}/prices)
cat 2024-02-08/3/3170/prices
```

> **Nota:** No existe información anterior al 8 de febrero de 2024. TCGplayer **no ofrece** historial de precios en su API directa.

---

## FAQ — Preguntas Frecuentes

### ¿Puedo hacer scraping del sitio?

Sí. Si los CSV premade no son suficientes, se puede procesar directamente los JSON cacheados. Ejemplo en Python:

```python
import requests
import time

session = requests.Session()
session.headers.update({'User-Agent': 'YourApplication/X.Y.Z'})

pokemon_category = '3'

r = session.get(f"https://tcgcsv.com/tcgplayer/{pokemon_category}/groups")
all_groups = r.json()['results']

for group in all_groups:
    group_id = group['groupId']

    r = session.get(f"https://tcgcsv.com/tcgplayer/{pokemon_category}/{group_id}/products")
    products = r.json()['results']
    for product in products:
        print(f"{product['productId']} - {product['name']}")

    r = session.get(f"https://tcgcsv.com/tcgplayer/{pokemon_category}/{group_id}/prices")
    prices = r.json()['results']
    for price in prices:
        print(f"{price['productId']} - {price['subTypeName']} - {price['midPrice']}")

    time.sleep(0.25)
```

---

### Categorías a omitir: 21, 69 y 70

Se recomienda **saltar** estas categorías al procesar el listado completo:

| categoryId | Motivo                                                                           |
|------------|---------------------------------------------------------------------------------|
| 21         | My Little Pony sin grupos activos. La categoría correcta es la 28.              |
| 69         | TCGplayer intentó categorizar cómics y abandonó. Miles de grupos, todos vacíos. |
| 70         | Igual que 69. No tiene productos disponibles.                                   |

```python
for category in all_categories:
    category_id = category['categoryId']
    if category_id in [21, 69, 70]:
        continue
    # procesar normalmente...
    time.sleep(0.25)
```

---

### ¿Puedo ver listings individuales o historial de ventas?

No. La API de TCGplayer no permite acceder a listings individuales. El campo `lowPrice` es la mejor aproximación disponible al precio más bajo listado. Con acceso directo a la API de TCGplayer se puede obtener datos a nivel SKU, pero no mucho más que promedios.

---

### ¿Por qué algunos `highPrice` son absurdos?

Fenómeno llamado **"Price Parking"**: vendedores que ponen precios altísimos (miles de dólares) para que nadie compre la carta, manteniendo el listing activo sin intención de vender. Por eso `highPrice` no es un dato confiable en general.

---

### ¿Cómo migrar de TCGCSV a la API directa de TCGplayer?

Los archivos cacheados provienen directamente de la API de TCGplayer (con hasta 24 horas de retraso), por lo que la migración es directa. Consideraciones:

- TCGplayer pagina los resultados de a **100 items por página** — hay que iterar sobre las páginas.
- El endpoint de productos devuelve `404` cuando un grupo está vacío — hay que normalizar ese edge case.
- TCGplayer **no ofrece** historial de precios.

---

### ¿Hay datos de Cardmarket?

Aún no. El mantenedor contactó a Cardmarket en junio de 2024, sin respuesta. Cardmarket ofrece exports de datos en su sitio web pero carecen de información detallada por set/carta y son difíciles de parsear.

---

## Links de interés

- [Repositorio GitHub](https://github.com/CptSpaceToaster/tcgcsv)
- [Discord](https://discord.gg/bydv2BNV25)
- [FAQ](https://tcgcsv.com/faq)
- [Documentación TCGplayer - Categories](https://docs.tcgplayer.com/reference/catalog_getcategories-1)
- [Documentación TCGplayer - Groups](https://docs.tcgplayer.com/reference/catalog_getcategorygroups-1)
- [Documentación TCGplayer - Products](https://docs.tcgplayer.com/reference/catalog_getproducts-1)
- [Documentación TCGplayer - Prices](https://docs.tcgplayer.com/reference/pricing_getgroupprices)
