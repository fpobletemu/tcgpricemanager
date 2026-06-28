# TCG Price Manager — Guía de Instalación y Distribución

---

## Opción A: EXE standalone (recomendado para compartir)

El `.exe` incluye Python y todas las dependencias. La otra persona **no necesita instalar nada**.

### Paso 1 — Compilar el EXE (solo tú, en tu PC)

```bash
build\build.bat
```

Genera: `dist\TCG Price Manager.exe` (~62 MB)

### Paso 2 — Qué enviarle a la otra persona

```
📦 Carpeta a compartir:
    TCG Price Manager.exe    ← el único archivo necesario
```

Puedes subirlo a Google Drive, OneDrive, WeTransfer o GitHub Releases.

### Paso 3 — Instrucciones para quien recibe el EXE

1. Copiar `TCG Price Manager.exe` a cualquier carpeta
   (ej: `C:\Users\TuNombre\Documentos\TCGManager\`)

2. Doble clic para abrir

3. **Primera vez:** Windows puede mostrar:
   > "Windows protegió su equipo"
   → Click en **"Más información"** → **"Ejecutar de todas formas"**

4. En el tab **"Sincronización"** → click **"Sync desde API"**
   - Descarga ~62k productos (requiere internet, ~5 minutos)
   - Solo necesario la primera vez

5. ¡Listo! La app funciona **sin internet** una vez sincronizada.

---

## Opción B: Instalación desde código fuente (requiere Python)

### Requisitos
- Windows 10/11 (64-bit)
- [Python 3.11+](https://www.python.org/downloads/) — marcar "Add to PATH" al instalar

### Pasos

```bash
# 1. Descomprimir o clonar el proyecto
cd busquedastcgcsv

# 2. Crear entorno virtual
python -m venv .venv

# 3. Instalar dependencias
.venv\Scripts\pip install -r requirements.txt

# 4. Generar ícono
.venv\Scripts\python generate_icon.py

# 5. Crear acceso directo en el escritorio
.venv\Scripts\python setup_shortcut.py

# 6. (Primera vez) Descargar datos de cartas
.venv\Scripts\python explorar_pokemon_tcg.py

# 7. Iniciar la app
.venv\Scripts\python tcg_app\main.py
```

---

## Datos de cartas — Primera sincronización

La app necesita descargar el catálogo de cartas antes de usarse.

### Opción 1: Desde la app (recomendado)
Tab **"Sincronización"** → **"Sync desde API"**

### Opción 2: Script de descarga (más rápido para la primera vez)
```bash
.venv\Scripts\python explorar_pokemon_tcg.py
```
Descarga ~262 CSV files a `output_pokemon_tcg/`, luego en la app click **"Importar CSVs locales"**.

### Opción 3: Compartir los datos ya descargados
Si quieres que la otra persona no tenga que descargar nada:
1. Comprimir la carpeta `output_pokemon_tcg/` (~100 MB)
2. Entregar junto con el EXE
3. Colocar `output_pokemon_tcg/` en la misma carpeta que el EXE
4. Usar **"Importar CSVs locales"** en lugar de "Sync desde API"

---

## Actualizaciones

### Actualizar datos de cartas (cualquier día)
Tab **"Sincronización"** → **"Sync desde API"**
> Los datos se actualizan una vez al día en TCGCSV (~20:00 UTC)

### Actualizar la aplicación
Tab **"Configuración"** → **"Buscar actualizaciones"**
> Requiere que el desarrollador haya publicado una nueva versión en la URL configurada

---

## Solución de problemas

| Problema | Causa | Solución |
|---|---|---|
| La app no abre | SmartScreen bloqueó el EXE | Click "Más información" → "Ejecutar de todas formas" |
| "Sin datos" en búsqueda | DB vacía | Tab Sync → "Sync desde API" |
| Error de red en sync | Sin internet | Usar los datos ya descargados con "Importar CSVs locales" |
| Tasa CLP no actualiza | Sin internet | Se usa la última tasa guardada automáticamente |
| La app se cierra sola | Error no manejado | Reiniciar; si persiste, ejecutar desde terminal para ver el error |
| Imágenes no cargan | Sin internet o URL inválida | Los precios siguen funcionando; imágenes son opcionales |

---

## Estructura de carpetas (modo EXE)

Al ejecutar el `.exe`, la app crea automáticamente:

```
<carpeta del EXE>/
    TCG Price Manager.exe
    output_pokemon_tcg/          ← CSVs de cartas (si los tienes)
    downloads/                   ← Imágenes descargadas

%APPDATA%\TCGPriceManager\
    tcg.db                       ← Base de datos SQLite (persiste entre versiones)
```

---

## Requisitos del sistema

| Componente | Mínimo |
|---|---|
| OS | Windows 10 (64-bit) |
| RAM | 512 MB libres |
| Disco | 500 MB (app + datos) |
| Internet | Solo para sincronizar datos e imágenes |
| Python | No requerido si usas el EXE |
