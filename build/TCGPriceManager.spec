# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for TCG Price Manager.
Run from the project root:
    pyinstaller build/TCGPriceManager.spec --clean --noconfirm
"""
import sys
import certifi
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent   # busquedastcgcsv/

block_cipher = None

# Collect qtawesome fonts (required for FA6 icons)
qtawesome_datas = collect_data_files("qtawesome")

a = Analysis(
    [str(ROOT / "tcg_app" / "main.py")],
    pathex=[str(ROOT / "tcg_app")],
    binaries=[],
    datas=[
        # App icon
        (str(ROOT / "tcg_app" / "assets" / "icon.ico"), "assets"),
        # qtawesome fonts
        *qtawesome_datas,
        # certifi CA bundle — required for SSL verification in frozen EXE
        (certifi.where(), "certifi"),
    ],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        "qtawesome",
        "qtpy",
        "rapidfuzz",
        "rapidfuzz.fuzz",
        "rapidfuzz.process",
        "rapidfuzz.process_cpp",
        "numpy",
        "requests",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "certifi",
        "charset_normalizer",
        "idna",
        "urllib3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TCG Price Manager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "tcg_app" / "assets" / "icon.ico"),
    version_file=None,
    uac_admin=False,
)
