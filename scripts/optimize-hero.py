"""Regenerate original hero layers for local web delivery (requires Pillow)."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1] / "accounts/static/accounts/landing"
for name, widths, quality in [
    ("landscape-rwanda", (640, 960, 1440), 80),
    ("tractor-3d", (640, 960, 1440), 80),
    ("foreground-crops", (640, 960, 1440), 78),
    ("tractor-dust", (960,), 65),
]:
    with Image.open(root / f"{name}.png") as image:
        for width in widths:
            size = (width, round(image.height * width / image.width))
            image.resize(size, Image.Resampling.LANCZOS).save(
                root / f"{name}-{width}.webp", "WEBP", quality=quality, method=6
            )
