"""Render app/static/icon.svg's design to the PNG home-screen icons for phones.

The drawing below mirrors icon.svg shape for shape, so after changing the SVG,
make the same change here and rerun:

    python3 make_icons.py            # writes into app/static/
    python3 make_icons.py OUT_DIR

Needs Pillow (`pip install pillow` or `sudo apt install python3-pil`); the
server itself does not. The PNGs are full-bleed squares because phones apply
their own rounded mask.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "app" / "static"
SS = 8  # supersampling factor


def render(size):
    k = size * SS / 64  # SVG viewBox is 64 units
    s = lambda *v: [round(x * k) for x in v]
    img = Image.new("RGB", (size * SS, size * SS), "#2563eb")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(s(15, 12, 49, 54), radius=5 * k, fill="#ffffff")
    d.rounded_rectangle(s(24, 8, 40, 17), radius=3 * k, fill="#1e3a8a")
    w = round(4 * k)
    for y in (28, 42):
        pts = [tuple(s(20, y)), tuple(s(24, y + 4)), tuple(s(31, y - 4))]
        d.line(pts, fill="#16a34a", width=w, joint="curve")
        for p in (pts[0], pts[2]):  # round line caps
            d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill="#16a34a")
        d.rounded_rectangle(s(34, y - 2, 44, y + 2), radius=2 * k, fill="#94a3b8")
    return img.resize((size, size), Image.LANCZOS)


for name, size in [("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)]:
    render(size).save(OUT / name, optimize=True)
    print(name, size)
