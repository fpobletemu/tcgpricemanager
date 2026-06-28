"""
Generates tcg_app/assets/icon.ico using Pillow.
Run once: python generate_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZES = [256, 128, 64, 48, 32, 16]
OUT   = Path(__file__).parent / "tcg_app" / "assets" / "icon.ico"

# Theme colors
BG     = (13, 17, 23)       # #0d1117
CARD   = (22, 27, 34)       # #161b22
ACCENT = (88, 166, 255)     # #58a6ff
TEXT   = (230, 237, 243)    # #e6edf3
BORDER = (48, 54, 61, 255)  # #30363d


def make_frame(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = size // 5

    # Background rounded square
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)

    # Card shape (portrait rectangle, centered)
    margin = max(3, size // 9)
    cw = size - 2 * margin
    ch = int(cw * 1.38)
    cx = margin
    cy = (size - ch) // 2
    cr = max(2, size // 16)

    draw.rounded_rectangle(
        [cx, cy, cx + cw, cy + ch],
        radius=cr,
        fill=CARD,
        outline=ACCENT,
        width=max(1, size // 28),
    )

    # Accent bar at top of card
    bar_h = max(2, size // 18)
    draw.rounded_rectangle(
        [cx + 2, cy + 2, cx + cw - 2, cy + bar_h],
        radius=cr,
        fill=ACCENT,
    )

    # "TCG" text label — only for larger sizes
    if size >= 48:
        font_size = max(7, size // 7)
        font = None
        for fname in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
            try:
                font = ImageFont.truetype(fname, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        label = "TCG"
        bbox  = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = cx + (cw - tw) // 2
        ty = cy + bar_h + (ch - bar_h - th) // 2
        draw.text((tx, ty), label, fill=TEXT, font=font)

    # Small accent dot at bottom of card
    dot_r = max(2, size // 20)
    dot_cx = cx + cw // 2
    dot_cy = cy + ch - dot_r - max(2, size // 20)
    draw.ellipse(
        [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
        fill=ACCENT,
    )

    return img


def generate():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames = [make_frame(s) for s in SIZES]
    frames[0].save(
        str(OUT),
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[1:],
    )
    print(f"Icon generated: {OUT}")


if __name__ == "__main__":
    generate()
