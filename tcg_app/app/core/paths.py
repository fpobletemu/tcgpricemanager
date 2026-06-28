"""
Centralized path resolution — works in both script mode and PyInstaller EXE mode.
"""
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def exe_dir() -> Path:
    """tcg_app/ (script) or folder containing the .exe (frozen)."""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent   # tcg_app/


def project_root() -> Path:
    """busquedastcgcsv/ (script) or exe_dir() (frozen)."""
    if is_frozen():
        return exe_dir()
    return exe_dir().parent


def data_dir() -> Path:
    """%APPDATA%\\TCGPriceManager (frozen) or tcg_app/data/ (script)."""
    if is_frozen():
        d = Path(os.environ.get("APPDATA", Path.home())) / "TCGPriceManager"
    else:
        d = exe_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def csv_dir() -> Path:
    """output_pokemon_tcg/ relative to project root."""
    return project_root() / "output_pokemon_tcg"


def downloads_dir() -> Path:
    """downloads/ relative to project root."""
    d = project_root() / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def assets_dir() -> Path:
    """tcg_app/assets/ or sys._MEIPASS/assets/ (frozen)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", exe_dir())) / "assets"
    return exe_dir() / "assets"
