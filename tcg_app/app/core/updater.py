"""
Self-update mechanism for TCG Price Manager.

Version endpoint must serve a JSON file like:
{
  "version": "1.1.0",
  "download_url": "https://example.com/TCGPriceManager.exe",
  "release_notes": "Bug fixes and new features."
}

In script mode (not frozen) the update flow is disabled — use git pull instead.
"""
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import requests

from version import __version__

DEFAULT_VERSION_URL = (
    "https://raw.githubusercontent.com/fpobletemu/tcgpricemanager/main/version.json"
)


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except ValueError:
        return (0,)


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def check_for_update(version_url: str) -> dict | None:
    """
    Fetch version.json. Returns the update dict if a newer version is available,
    or None if up-to-date, offline, or if running in script (non-frozen) mode.
    """
    if not is_frozen():
        return None
    try:
        resp = requests.get(version_url, timeout=10)
        resp.raise_for_status()
        info = resp.json()
        if _version_tuple(info["version"]) > _version_tuple(__version__):
            return info
        return None
    except Exception:
        return None


def download_and_install(
    download_url    : str,
    progress_cb     : Callable[[int, int], None] | None = None,
) -> None:
    """
    Download the new EXE to a temp file, then write a batch script that:
      1. Waits for this process to exit
      2. Replaces the current EXE with the downloaded one
      3. Relaunches the updated EXE

    Raises RuntimeError on any failure.
    """
    if not is_frozen():
        raise RuntimeError("La auto-actualización solo funciona en modo EXE.")

    current_exe = Path(sys.executable)
    tmp_dir     = current_exe.parent
    new_exe     = tmp_dir / "_TCGPriceManager_update.exe"

    # Download
    try:
        resp = requests.get(download_url, stream=True, timeout=60)
        resp.raise_for_status()
        total    = int(resp.headers.get("Content-Length", 0))
        received = 0
        with open(new_exe, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                received += len(chunk)
                if progress_cb and total:
                    progress_cb(received, total)
    except Exception as e:
        raise RuntimeError(f"Error al descargar: {e}") from e

    # Write update launcher batch
    bat_path = tmp_dir / "_update_launcher.bat"
    bat_path.write_text(
        f"@echo off\n"
        f"ping -n 3 127.0.0.1 > nul\n"
        f"move /y \"{new_exe}\" \"{current_exe}\"\n"
        f"start \"\" \"{current_exe}\"\n"
        f"del \"%~f0\"\n",
        encoding="utf-8",
    )

    subprocess.Popen(
        ["cmd", "/c", str(bat_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)
