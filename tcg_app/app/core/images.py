"""
Card image downloader.
Downloads high-resolution images from TCGplayer CDN to a local folder.
"""
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

import requests

DOWNLOAD_DIR    = Path(__file__).resolve().parent.parent.parent.parent / "downloads"
HIGH_RES_SUFFIX = "_in_1000x1000"
LOW_RES_SUFFIX  = "_200w"
USER_AGENT      = "TCGPriceManager/1.0.0"


def _safe_name(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text or "").strip()
    return re.sub(r"\s+", "_", text)[:50]


def get_high_res_url(image_url: str) -> str:
    if not image_url:
        return image_url
    return image_url.replace(LOW_RES_SUFFIX, HIGH_RES_SUFFIX)


def download_image(
    product_id: int,
    image_url : str,
    clean_name: str = "",
    dest_dir  : Path | None = None,
) -> Path | None:
    """
    Download one card image to dest_dir.
    Skips if already exists. Falls back to low-res if high-res fails.
    Returns the saved Path or None on failure.
    """
    target_dir = dest_dir or DOWNLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    safe = _safe_name(clean_name or str(product_id))
    dest = target_dir / f"{product_id}_{safe}.jpg"

    if dest.exists() and dest.stat().st_size > 1_000:
        return dest

    headers = {"User-Agent": USER_AGENT}

    for url in (get_high_res_url(image_url), image_url):
        if not url:
            continue
        try:
            resp = requests.get(url, timeout=20, headers=headers)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return dest
        except Exception:
            continue

    return None


def download_batch(
    items      : list[dict],
    dest_dir   : Path,
    progress_cb: Callable[[int, int], None] | None = None,
    max_workers: int = 4,
) -> list[Path]:
    """
    Download images for multiple products concurrently.
    Each item dict must have: productId, imageUrl, cleanName.
    Returns list of successfully saved Paths.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved : list[Path] = []
    total = len(items)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                download_image,
                item["productId"],
                item.get("imageUrl", ""),
                item.get("cleanName", ""),
                dest_dir,
            ): item
            for item in items
        }
        for done_count, future in enumerate(as_completed(future_map), 1):
            if progress_cb:
                progress_cb(done_count, total)
            result = future.result()
            if result:
                saved.append(result)

    return saved
