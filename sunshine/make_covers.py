#!/usr/bin/env python3
"""Gera as capas (460x690) dos apps do Sunshine no estilo das de /usr/share/sunshine.
Uso: python3 make_covers.py [pasta]   (padrão: ~/.config/sunshine/covers)"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/TTF/DejaVuSans"
MOBILE = ((26, 26, 80), (255, 204, 77))
DESKTOP = ((45, 27, 78), (128, 200, 255))
COVERS = [
    ("3120x1440", 120, "S26 ULTRA", MOBILE),
    ("2340x1080", 120, "S26 ULTRA", MOBILE),
    ("1560x720", 120, "S26 ULTRA", MOBILE),
    ("2960x1848", 90, "TAB S9 ULTRA", MOBILE),
    ("2560x1600", 120, "TAB S9 ULTRA", MOBILE),
    ("3840x2160", 30, "DESKTOP", DESKTOP),
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.config/sunshine/covers")
    os.makedirs(out, exist_ok=True)
    big = ImageFont.truetype(FONT + "-Bold.ttf", 46)
    mid = ImageFont.truetype(FONT + ".ttf", 28)
    tag = ImageFont.truetype(FONT + "-Bold.ttf", 20)
    for res, fps, label, (bg, fg) in COVERS:
        im = Image.new("RGB", (460, 690), bg)
        d = ImageDraw.Draw(im)
        d.text((230, 265), res, font=big, fill=(255, 255, 255), anchor="mm")
        d.text((230, 335), f"{fps} fps", font=mid, fill=(180, 180, 190), anchor="mm")
        d.text((230, 405), label, font=tag, fill=fg, anchor="mm")
        path = os.path.join(out, f"{res.replace('x', '_')}_{fps}.png")
        im.save(path)
        print(path)


if __name__ == "__main__":
    main()
