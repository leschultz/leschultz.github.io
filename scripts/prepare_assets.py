#!/usr/bin/env python3
"""Regenerate image derivatives. Requires Pillow and local TrueType fonts.

Use --fetch-font to download the pinned, Latin-only Source Serif 4 WOFF2.
All assets are committed; this script is only needed when changing originals.
"""

import argparse
from pathlib import Path
import subprocess
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT_URL = "https://fonts.gstatic.com/s/sourceserif4/v15/vEFy2_tTDB4M7-auWDN0ahZJW3IX2ih5nk3AucvUHf6OAVIJmeUDygwjihdqnhtdDg.woff2"


def load_font(family, size, path=None):
    if path:
        return ImageFont.truetype(str(path), size)
    try:
        return ImageFont.truetype("DejaVuSerif.ttf" if family == "serif" else "DejaVuSans.ttf", size)
    except OSError:
        try:
            result = subprocess.run(["fc-match", "-f", "%{file}", family], capture_output=True, text=True, check=True)
            return ImageFont.truetype(result.stdout, size)
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError("Install DejaVu fonts/fontconfig, or pass --serif-font and --sans-font paths.") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-font", action="store_true")
    parser.add_argument("--serif-font", type=Path)
    parser.add_argument("--sans-font", type=Path)
    args = parser.parse_args()
    assets = ROOT / "assets/img"
    if args.fetch_font:
        with urlopen(FONT_URL, timeout=30) as response:
            font = response.read()
        if not font.startswith(b"wOF2"):
            raise ValueError("Expected a WOFF2 font")
        (ROOT / "assets/fonts/source-serif-4-latin-400.woff2").write_bytes(font)

    with Image.open(ROOT / "img/profile.png") as portrait:
        for width in (480, 800):
            resized = portrait.convert("RGB").resize((width, round(width * portrait.height / portrait.width)), Image.Resampling.LANCZOS)
            resized.save(assets / f"profile-{width}.webp", quality=84, method=6)
    with Image.open(ROOT / "img/metallic_glass.png") as image:
        image.save(assets / "metallic-glass.webp", lossless=True, method=6)

    icon = Image.new("RGB", (192, 192), "#172e36")
    draw = ImageDraw.Draw(icon)
    draw.line([(48, 48), (48, 144), (87, 144)], fill="#eaf0e9", width=12)
    draw.line([(144, 54), (108, 54), (99, 66), (99, 84), (108, 96), (126, 96), (138, 108), (138, 126), (126, 138), (96, 138)], fill="#eaf0e9", width=12)
    draw.ellipse((141, 135, 159, 153), fill="#83b6a2")
    icon.resize((64, 64), Image.Resampling.LANCZOS).save(assets / "favicon.png")

    image = Image.new("RGB", (1200, 630), "#f6f5ef")
    draw = ImageDraw.Draw(image)
    serif = load_font("serif", 78, args.serif_font)
    sans = load_font("sans-serif", 25, args.sans_font)
    small = load_font("sans-serif", 17, args.sans_font)
    draw.rectangle((0, 0, 1200, 8), fill="#17666a")
    draw.text((62, 64), "MATERIALS SCIENCE × MACHINE LEARNING", font=small, fill="#17666a")
    draw.text((57, 125), "Lane Enrique\nSchultz.", font=serif, spacing=0, fill="#172e36")
    draw.text((62, 350), "Connecting structure, models,\nand materials discovery.", font=sans, spacing=10, fill="#53666b")
    draw.line((62, 518, 1138, 518), fill="#d4dcd5", width=2)
    draw.text((62, 550), "LANE E. SCHULTZ, Ph.D.", font=small, fill="#17666a")
    draw.text((906, 550), "leschultz.github.io", font=small, fill="#17666a")
    points = [(915, 90), (1045, 165), (1045, 315), (915, 390), (785, 315), (785, 165), (915, 240)]
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0), (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6)):
        draw.line((*points[a], *points[b]), fill="#80a591", width=3)
    for index, (x, y) in enumerate(points):
        radius = 23 if index == 6 else 14
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#ae7941" if index == 6 else "#17666a")
    image.save(assets / "social-card.png", optimize=True)
    print("Prepared responsive portraits, research figure, icons, and social preview.")


if __name__ == "__main__":
    main()
