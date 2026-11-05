"""Fictional brand kit: logo (PNG + SVG, light & dark variants) and palette."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import hex_to_rgb

FONT_CANDIDATES = {
    "bold": ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "regular": ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def font(weight, size):
    for p in FONT_CANDIDATES[weight]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


# ---- emblem shapes: each returns SVG markup for a 100x100 box, and draws on PIL ----------
def _emblem_svg(shape, c1, c2):
    if shape == "leaf":
        return (f'<path d="M50 6 C78 18 90 46 76 72 C66 90 40 96 24 84 C10 72 12 44 26 28 C34 18 42 10 50 6Z" fill="{c1}"/>'
                f'<path d="M28 82 C40 62 52 46 70 26" stroke="{c2}" stroke-width="6" fill="none" stroke-linecap="round"/>')
    if shape == "hexagon":
        pts = " ".join(f"{50 + 44 * math.cos(math.radians(60 * i - 30)):.1f},{50 + 44 * math.sin(math.radians(60 * i - 30)):.1f}" for i in range(6))
        return f'<polygon points="{pts}" fill="{c1}"/><circle cx="50" cy="50" r="16" fill="{c2}"/>'
    if shape == "chevrons":
        return (f'<rect x="4" y="4" width="92" height="92" rx="22" fill="{c1}"/>'
                f'<path d="M28 30 L50 50 L28 70" stroke="{c2}" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="M52 30 L74 50 L52 70" stroke="{c2}" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity=".6"/>')
    if shape == "rings":
        return (f'<circle cx="38" cy="50" r="30" fill="none" stroke="{c1}" stroke-width="10"/>'
                f'<circle cx="62" cy="50" r="30" fill="none" stroke="{c2}" stroke-width="10"/>')
    if shape == "acorn":
        return (f'<path d="M18 44 C18 26 34 16 50 16 C66 16 82 26 82 44 Z" fill="{c2}"/>'
                f'<rect x="47" y="4" width="6" height="14" rx="3" fill="{c2}"/>'
                f'<path d="M24 46 L76 46 C76 70 64 92 50 96 C36 92 24 70 24 46 Z" fill="{c1}"/>')
    # default: monogram tile
    return f'<rect x="4" y="4" width="92" height="92" rx="22" fill="{c1}"/>'


def _draw_emblem(d, shape, x, y, s, c1, c2, letter):
    k = s / 100.0

    def P(px, py):
        return (x + px * k, y + py * k)

    if shape == "leaf":
        pts = []
        for t in range(0, 101):
            a = 2 * math.pi * t / 100
            pts.append(P(50 + 34 * math.sin(a) * (1 + 0.25 * math.cos(a)), 50 - 42 * math.cos(a)))
        d.polygon(pts, fill=c1)
        d.line([P(30, 80), P(50, 52), P(70, 26)], fill=c2, width=max(2, int(6 * k)), joint="curve")
    elif shape == "hexagon":
        d.polygon([P(50 + 44 * math.cos(math.radians(60 * i - 30)), 50 + 44 * math.sin(math.radians(60 * i - 30))) for i in range(6)], fill=c1)
        d.ellipse([P(34, 34), P(66, 66)], fill=c2)
    elif shape == "chevrons":
        d.rounded_rectangle([P(4, 4), P(96, 96)], radius=22 * k, fill=c1)
        w = max(3, int(10 * k))
        d.line([P(28, 30), P(50, 50), P(28, 70)], fill=c2, width=w, joint="curve")
        d.line([P(52, 30), P(74, 50), P(52, 70)], fill=c2, width=w, joint="curve")
    elif shape == "rings":
        w = max(3, int(10 * k))
        d.ellipse([P(8, 20), P(68, 80)], outline=c1, width=w)
        d.ellipse([P(32, 20), P(92, 80)], outline=c2, width=w)
    elif shape == "acorn":
        d.pieslice([P(18, 16), P(82, 72)], 180, 360, fill=c2)
        d.rounded_rectangle([P(47, 4), P(53, 18)], radius=3 * k, fill=c2)
        d.polygon([P(24, 46), P(76, 46), P(70, 74), P(50, 96), P(30, 74)], fill=c1)
    else:
        d.rounded_rectangle([P(4, 4), P(96, 96)], radius=22 * k, fill=c1)
        f = font("bold", int(58 * k))
        d.text(P(50, 52), letter, font=f, fill=c2, anchor="mm")


def build_brand(company, out_dir):
    b = company.setdefault("brand", {})
    b.setdefault("primary", "#1F4E79")
    b.setdefault("secondary", "#2E8B57")
    b.setdefault("accent", "#F2A900")
    b.setdefault("dark", "#1B1B1F")
    b.setdefault("light", "#F4F6F8")
    b.setdefault("font_heading", "Segoe UI Semibold")
    b.setdefault("font_body", "Segoe UI")
    shape = b.get("logo_shape", "monogram")
    word = b.get("logo_text", company["fictional_name"])
    letter = (b.get("monogram") or company["fictional_name"][0]).upper()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assets = {}

    for variant, text_col, c1, c2 in [("logo", b["dark"], b["primary"], b["secondary"] if shape not in ("monogram", "chevrons", "hexagon") else "#FFFFFF"),
                                      ("logo-white", "#FFFFFF", "#FFFFFF", b["accent"])]:
        if variant == "logo-white" and shape in ("monogram", "chevrons"):
            c2 = b["primary"]
        H = 240
        f = font("bold", 120)
        tmp = Image.new("RGBA", (10, 10))
        tw = ImageDraw.Draw(tmp).textlength(word, font=f)
        W = int(H + 40 + tw + 30)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        _draw_emblem(d, shape, 10, 20, 200, c1, c2, letter)
        d.text((H + 20, H / 2 + 4), word, font=f, fill=text_col, anchor="lm")
        p = out / f"{variant}.png"
        img.save(p)
        assets[variant.replace("-", "_") + "_png"] = str(p)
        # emblem-only (square) for favicons / app tiles
        em = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        _draw_emblem(ImageDraw.Draw(em), shape, 16, 16, 224, c1, c2, letter)
        ep = out / f"{variant}-emblem.png"
        em.save(ep)
        assets[variant.replace("-", "_") + "_emblem_png"] = str(ep)

        mono = "" if shape != "monogram" else (
            f'<text x="50" y="52" font-family="Segoe UI, Arial, sans-serif" font-weight="700" font-size="58" '
            f'fill="{c2}" text-anchor="middle" dominant-baseline="central">{letter}</text>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(100 + 30 + len(word) * 30)} 100" height="100">'
               f'{_emblem_svg(shape, c1, c2)}{mono}'
               f'<text x="118" y="54" font-family="Segoe UI, Arial, sans-serif" font-weight="700" font-size="50" '
               f'fill="{text_col}" dominant-baseline="central">{word}</text></svg>')
        (out / f"{variant}.svg").write_text(svg, encoding="utf-8")
        assets[variant.replace("-", "_") + "_svg"] = svg
        assets[variant.replace("-", "_") + "_emblem_svg"] = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{_emblem_svg(shape, c1, c2)}{mono}</svg>')

    (out / "palette.json").write_text(json.dumps({k: v for k, v in b.items()}, indent=2), encoding="utf-8")
    # swatch image
    keys = ["primary", "secondary", "accent", "dark", "light"]
    sw = Image.new("RGB", (len(keys) * 220, 260), "white")
    d = ImageDraw.Draw(sw)
    for i, k in enumerate(keys):
        d.rectangle([i * 220 + 10, 10, i * 220 + 210, 190], fill=hex_to_rgb(b[k]), outline="#cccccc")
        d.text((i * 220 + 14, 200), k.title(), font=font("bold", 22), fill="#222")
        d.text((i * 220 + 14, 228), b[k].upper(), font=font("regular", 20), fill="#555")
    sw.save(out / "palette.png")
    assets["palette_png"] = str(out / "palette.png")
    return assets
