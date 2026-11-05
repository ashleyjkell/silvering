"""Raster content: scanned documents (image-only PDF/JPG) and images (whiteboard / sticky-note photos, receipts, charts).

Scans deliberately have no text layer, so learners meet the real-world case where Copilot can't read a file
until it has been OCR'd or re-keyed."""
import hashlib
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .brand import font
from .common import hex_to_rgb, parse_date, uk_date

FONT_DIR = Path(__file__).parent / "fonts"
INK = {"blue": (28, 52, 140), "black": (30, 30, 34), "red": (186, 32, 36), "green": (22, 120, 60)}
MONO = ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc"]
NOTE_COLOURS = [(255, 236, 120), (255, 179, 199), (176, 230, 160), (160, 210, 250), (255, 200, 130)]


def hand(size, weight=500):
    f = ImageFont.truetype(str(FONT_DIR / "Caveat.ttf"), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def mono(size):
    for p in MONO:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def plain(s):
    return re.sub(r"\*\*?([^*]+)\*\*?", r"\1", str(s))


def rng(item):
    return random.Random(int(hashlib.md5(item["id"].encode()).hexdigest()[:8], 16))


def wrap(d, text, f, width):
    lines = []
    for para in plain(text).split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= width or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def line_h(f, k=1.35):
    a, b = f.getmetrics()
    return int((a + b) * k)


def _rotated_paste(base, layer, xy, angle):
    r = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(r, (int(xy[0] - (r.width - layer.width) / 2), int(xy[1] - (r.height - layer.height) / 2)))


def _save(img, path, fmt, quality=72):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
    if fmt == "png":
        img.save(path, "PNG", optimize=True)
    else:
        img.save(path, "JPEG", quality=quality, optimize=True)


def _preview(ctx, item, imgs):
    """Small JPEGs under 'Dashboard Assets/' so the dashboard can show raster content (incl. scanned PDFs)."""
    out = []
    d = ctx.out_root / "Dashboard Assets"
    d.mkdir(exist_ok=True)
    for n, im in enumerate(imgs, 1):
        p = d / f"{item['id']}-{n}.jpg"
        im = im.convert("RGB")
        im.thumbnail((1000, 1400))
        im.save(p, "JPEG", quality=70, optimize=True)
        out.append(p.relative_to(ctx.out_root).as_posix())
    item["_previews"] = out


# ------------------------------------------------------------------ scans
class _Page:
    W, H, M = 1240, 1754, 105

    def __init__(self, ctx, item, first):
        self.img = Image.new("RGBA", (self.W, self.H), (255, 255, 255, 255))
        self.d = ImageDraw.Draw(self.img)
        self.y = self.M
        if item.get("letterhead", True) and first:
            self._letterhead(ctx)

    def _letterhead(self, ctx):
        try:
            logo = Image.open(ctx.brand_assets["logo_png"]).convert("RGBA")
            logo.thumbnail((360, 70))
            self.img.alpha_composite(logo, (self.M, self.y))
        except Exception:
            pass
        c = ctx.company
        addr = [c.get("legal_name", c["fictional_name"])] + [v for v in (c.get("hq") or {}).values() if v] + [c.get("domain", "")]
        f = font("regular", 15)
        for i, t in enumerate(addr[:5]):
            self.d.text((self.W - self.M, self.y + i * 19), t, font=f, fill=(90, 90, 90), anchor="ra")
        self.y += 110
        self.d.line([(self.M, self.y), (self.W - self.M, self.y)], fill=hex_to_rgb(ctx.brand.get("primary", "#333333")), width=3)
        self.y += 30

    def room(self, h):
        return self.y + h < self.H - self.M - 30


def _scan_pages(item, ctx):
    r = rng(item)
    pages = [_Page(ctx, item, True)]
    W, M = _Page.W, _Page.M
    tw = W - 2 * M

    def pg():
        if not pages[-1].room(0):
            pages.append(_Page(ctx, item, False))
        return pages[-1]

    def need(h):
        if not pages[-1].room(h):
            pages.append(_Page(ctx, item, False))
        return pages[-1]

    def text_block(t, f, fill=(25, 25, 25), indent=0, prefix="", k=1.38):
        p = pg()
        lines = wrap(p.d, t, f, tw - indent - 28)
        for i, ln in enumerate(lines):
            p = need(line_h(f, k))
            if prefix and i == 0:
                p.d.text((M + indent, p.y), prefix, font=f, fill=fill)
            p.d.text((M + indent + (28 if prefix else 0), p.y), ln, font=f, fill=fill)
            p.y += line_h(f, k)

    def handwrite(p, xy, t, size=34, ink="blue"):
        f = hand(size)
        layer = Image.new("RGBA", (int(p.d.textlength(t, font=f)) + 20, size + 24), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((10, 4), t, font=f, fill=INK.get(ink, INK["blue"]) + (235,))
        _rotated_paste(p.img, layer, xy, r.uniform(-1.6, 1.2))

    if item.get("show_title", True):
        text_block(ctx.fill(item["title"]), font("bold", 32), k=1.25)
        pg().y += 14
    for b in item.get("blocks", []):
        b = ctx.fill_deep(b)
        if "h1" in b or "h2" in b or "h3" in b:
            k = "h1" if "h1" in b else "h2" if "h2" in b else "h3"
            need(80).y += 10
            text_block(b[k], font("bold", {"h1": 28, "h2": 24, "h3": 20}[k]))
            pg().y += 4
        elif "p" in b:
            text_block(b["p"], font("regular", 19))
            pg().y += 10
        elif "bullets" in b or "numbered" in b:
            for i, x in enumerate(b.get("bullets") or b.get("numbered"), 1):
                text_block(str(x).strip(), font("regular", 19), indent=18, prefix="•" if "bullets" in b else f"{i}.")
            pg().y += 10
        elif "kv" in b:
            fb, fr = font("bold", 18), font("regular", 18)
            for k_, v in b["kv"]:
                p = need(34)
                p.d.text((M, p.y), plain(k_), font=fb, fill=(40, 40, 40))
                lines = wrap(p.d, v, fr, tw - 300)
                for ln in lines:
                    p = need(28)
                    p.d.text((M + 300, p.y), ln, font=fr, fill=(25, 25, 25))
                    p.y += 28
                p.y += 6
            pg().y += 10
        elif "form" in b:
            fl = font("regular", 15)
            for fld in b["form"]:
                label, val = fld[0], fld[1] if len(fld) > 1 else ""
                tall = 56 if len(str(val)) < 70 else 56 + 36 * (len(str(val)) // 70)
                p = need(tall + 30)
                p.d.text((M, p.y), plain(label).upper(), font=fl, fill=(70, 70, 70))
                p.y += 20
                p.d.rectangle([M, p.y, W - M, p.y + tall], outline=(60, 60, 60), width=2)
                if val:
                    vl = wrap(p.d, val, hand(34), tw - 40)
                    for j, ln in enumerate(vl):
                        handwrite(p, (M + 14, p.y + 4 + j * 36), ln, ink=b.get("ink", "blue"))
                p.y += tall + 16
        elif "checks" in b:
            f = font("regular", 18)
            for label, on in b["checks"]:
                p = need(36)
                p.d.rectangle([M, p.y + 2, M + 22, p.y + 24], outline=(50, 50, 50), width=2)
                if on:
                    ink = INK[b.get("ink", "blue")]
                    p.d.line([(M + 3, p.y + 12), (M + 10, p.y + 22), (M + 28, p.y - 6)], fill=ink, width=4)
                p.d.text((M + 36, p.y), plain(label), font=f, fill=(25, 25, 25))
                p.y += 36
            pg().y += 8
        elif "table" in b:
            cols, rows = ctx.resolve_table(b["table"])
            f, fb = font("regular", 15), font("bold", 15)
            lens = [max([len(str(c))] + [len(str(rw[i])) for rw in rows[:40]]) + 3 for i, c in enumerate(cols)]
            ws = [tw * x / sum(lens) for x in lens]
            for ri, row in enumerate([cols] + [list(rw) for rw in rows]):
                cells = [wrap(pg().d, "" if v is None else v, fb if ri == 0 else f, w - 12) for v, w in zip(row, ws)]
                h = max(len(c) for c in cells) * 21 + 12
                p = need(h)
                x = M
                for c, w in zip(cells, ws):
                    p.d.rectangle([x, p.y, x + w, p.y + h], outline=(80, 80, 80), width=1,
                                  fill=(232, 232, 232) if ri == 0 else None)
                    for j, ln in enumerate(c):
                        p.d.text((x + 6, p.y + 6 + j * 21), ln, font=fb if ri == 0 else f, fill=(20, 20, 20))
                    x += w
                p.y += h
            pg().y += 18
        elif "signature" in b:
            pid = b["signature"]
            pe = ctx.person(pid) if isinstance(pid, str) else pid
            p = need(150)
            p.y += 20
            handwrite(p, (M + 10, p.y - 4), pe.get("name", ""), size=58, ink=b.get("ink", "blue"))
            p.y += 66
            p.d.line([(M, p.y), (M + 420, p.y)], fill=(60, 60, 60), width=2)
            p.d.text((M, p.y + 8), plain(f"{pe.get('name', '')}{', ' + pe['title'] if pe.get('title') else ''}"),
                     font=font("regular", 16), fill=(40, 40, 40))
            if b.get("date"):
                p.d.text((M + 520, p.y - 34), "Date:", font=font("regular", 16), fill=(40, 40, 40))
                handwrite(p, (M + 580, p.y - 52), uk_date(b["date"]), size=36, ink=b.get("ink", "blue"))
            p.y += 50
        elif "stamp" in b:
            p = pg()
            txt = [plain(b["stamp"]).upper()] + ([uk_date(b["date"]).upper()] if b.get("date") else [])
            fs = font("bold", 30)
            w = int(max(p.d.textlength(t, font=fs) for t in txt)) + 50
            h = 44 * len(txt) + 30
            red = INK["red"] if b.get("colour", "red") == "red" else INK["blue"]
            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.rectangle([2, 2, w - 3, h - 3], outline=red + (200,), width=4)
            ld.rectangle([9, 9, w - 10, h - 10], outline=red + (170,), width=2)
            for i, t in enumerate(txt):
                ld.text((w / 2, 20 + i * 44), t, font=fs, fill=red + (190,), anchor="ma")
            pos = (W - M - w - r.randint(0, 60), max(M, p.y - h - r.randint(0, 40))) if b.get("float", True) else (M, p.y)
            _rotated_paste(p.img, layer, pos, r.uniform(-9, 6))
            if not b.get("float", True):
                p.y += h + 10
        elif "hand" in b:
            p = need(60)
            for ln in wrap(p.d, b["hand"], hand(36), tw - 60):
                p = need(44)
                handwrite(p, (M + b.get("indent", 30), p.y), ln, size=36, ink=b.get("ink", "red"))
                p.y += 42
            p.y += 8
        elif "spacer" in b:
            pg().y += int(b["spacer"])
        elif "pagebreak" in b:
            pages.append(_Page(ctx, item, False))
    n = len(pages)
    if n > 1 or item.get("page_numbers"):
        for i, p in enumerate(pages, 1):
            p.d.text((W / 2, p.H - 70), f"Page {i} of {n}", font=font("regular", 14), fill=(110, 110, 110), anchor="ma")
    return [p.img for p in pages], r


def _degrade(img, r, colour=False, quality="good"):
    img = img.convert("RGB")
    if not colour:
        img = ImageOps.grayscale(img).convert("RGB")
    else:
        img = Image.blend(img, Image.new("RGB", img.size, (250, 244, 228)), 0.12)
    poor = quality == "poor"
    img = img.rotate(r.uniform(-2.2, 2.2) if poor else r.uniform(-0.9, 0.9), resample=Image.BICUBIC,
                     fillcolor=(226, 226, 222), translate=(r.randint(-8, 8), r.randint(-8, 8)))
    noise = Image.effect_noise(img.size, 38 if poor else 22).convert("RGB")
    img = Image.blend(img, ImageEnhance.Brightness(noise).enhance(1.0), 0.07 if poor else 0.04)
    d = ImageDraw.Draw(img)
    for _ in range(900 if poor else 260):
        x, y = r.randint(0, img.width - 1), r.randint(0, img.height - 1)
        g = r.randint(80, 170)
        d.point((x, y), fill=(g, g, g))
    shade = Image.linear_gradient("L").rotate(90).resize((40, img.height))  # scanner-lid shadow on the left edge
    img.paste(Image.new("RGB", (40, img.height), (150, 150, 150)), (0, 0), ImageOps.invert(shade).point(lambda v: v // 3))
    img = img.filter(ImageFilter.GaussianBlur(0.9 if poor else 0.55))
    img = ImageEnhance.Contrast(img).enhance(1.25 if poor else 1.1)
    if not colour:
        img = ImageOps.grayscale(img)
    return img


def render_scan(item, ctx, path):
    pages, r = _scan_pages(item, ctx)
    out = [_degrade(p, r, item.get("colour", False), item.get("quality", "good")) for p in pages]
    fmt = path.suffix.lower().lstrip(".")
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "pdf":
        rgb = [o.convert("RGB") for o in out]
        rgb[0].save(path, "PDF", resolution=150, save_all=True, append_images=rgb[1:],
                    title=item["title"], author=ctx.company["fictional_name"], subject="Fictional training data - scanned copy")
    else:
        _save(out[0], path, "png" if fmt == "png" else "jpg", 68)
    _preview(ctx, item, out)


# ------------------------------------------------------------------ images
def _photo_finish(img, r, vignette=0.35):
    """Phone-camera look: slight perspective, vignette, noise."""
    w, h = img.size
    j = lambda: r.randint(-int(w * 0.02), int(w * 0.02))
    img = img.transform((w, h), Image.QUAD, (j(), j(), j(), h + j(), w + j(), h + j(), w + j(), j()),
                        resample=Image.BICUBIC, fillcolor=(90, 88, 84))
    mask = Image.radial_gradient("L").resize((w, h))
    dark = Image.new("RGB", (w, h), (20, 20, 20))
    img = Image.composite(dark, img, mask.point(lambda v: int(max(0, v - 120) * vignette)))
    img = Image.blend(img, Image.effect_noise((w, h), 30).convert("RGB"), 0.035)
    return img.filter(ImageFilter.GaussianBlur(0.6))


def _whiteboard(item, ctx, r):
    W, H = 1800, 1200
    img = Image.new("RGBA", (W, H), (178, 172, 160, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([60, 50, W - 60, H - 110], fill=(165, 168, 172))
    d.rectangle([80, 70, W - 80, H - 130], fill=(246, 247, 244))
    glare = Image.radial_gradient("L").resize((1100, 700)).point(lambda v: max(0, 255 - v) // 5)
    img.paste(Image.new("RGBA", glare.size, (255, 255, 255, 255)), (W - 1150, 40), glare)
    for _ in range(6):  # faint ghosts of erased writing
        d.text((r.randint(120, W - 500), r.randint(120, H - 260)), r.choice(["Q3 plan", "->", "actions", "TBC", "ideas"]),
               font=hand(r.randint(40, 70)), fill=(236, 237, 235))
    title = ctx.fill(item.get("heading") or item["title"])
    tf = hand(84, 700)
    d.text((130, 100), title, font=tf, fill=INK["blue"])
    tl = d.textlength(title, font=tf)
    d.line([(130 + i * tl / 8, 195 + r.randint(-3, 3)) for i in range(9)], fill=INK["blue"], width=5)
    cols = item.get("columns") or [{"items": item.get("bullets", [])}]
    cw = (W - 260) / len(cols)
    inks = ["black", "blue", "green", "red"]
    for ci, c in enumerate(cols):
        c = ctx.fill_deep(c)
        x, y = 130 + ci * cw, 240
        ink = INK[c.get("ink", inks[ci % 3])]
        if c.get("heading"):
            hf = hand(58, 700)
            d.text((x, y), c["heading"], font=hf, fill=ink)
            hw = d.textlength(c["heading"], font=hf)
            d.rounded_rectangle([x - 14, y - 6, x + hw + 14, y + 74], radius=18, outline=ink, width=4)
            y += 100
        f = hand(44)
        for it in c.get("items", []):
            it = str(it)
            red, strike = it.startswith("!"), it.startswith("~")
            it = it.lstrip("!~").strip()
            for li, ln in enumerate(wrap(d, it, f, cw - 70)):
                xx, yy = x + (0 if li == 0 else 30) + r.randint(-3, 3), y + r.randint(-3, 3)
                d.text((xx, yy), ("- " if li == 0 else "") + ln, font=f, fill=INK["red"] if red else ink)
                if strike:
                    lw = d.textlength("- " + ln, font=f)
                    d.line([(xx, yy + 30), (xx + lw, yy + 26)], fill=ink, width=4)
                if red:
                    lw = d.textlength("- " + ln, font=f)
                    d.line([(xx + 30, yy + 58), (xx + lw, yy + 56)], fill=INK["red"], width=3)
                y += 54
            y += 8
    if item.get("footer"):
        d.text((130, H - 210), ctx.fill(item["footer"]), font=hand(40), fill=INK["red"])
    d.rectangle([300, H - 128, W - 300, H - 100], fill=(150, 152, 156))  # marker tray
    for i, col in enumerate([INK["black"], INK["blue"], INK["red"], INK["green"]]):
        d.rounded_rectangle([420 + i * 190, H - 140, 580 + i * 190, H - 112], radius=10, fill=col)
    return _photo_finish(img.convert("RGB"), r)


def _sticky(item, ctx, r):
    W, H = 1800, 1200
    img = Image.new("RGBA", (W, H), (226, 226, 222, 255))
    d = ImageDraw.Draw(img)
    d.text((80, 50), ctx.fill(item.get("heading") or item["title"]), font=hand(76, 700), fill=INK["black"])
    cols = ctx.fill_deep(item.get("columns", []))
    cw = (W - 160) / max(1, len(cols))
    most = max([len(c.get("notes", [])) for c in cols] + [1])
    per_col = 2 if cw > 520 else 1
    rows = -(-most // per_col)
    size = int(min((cw - 30 * per_col) / per_col, (H - 300) / rows - 24, 300))
    for ci, c in enumerate(cols):
        x0 = 80 + ci * cw
        d.text((x0, 160), c.get("heading", ""), font=hand(54, 700), fill=INK["blue"])
        d.line([(x0, 225), (x0 + cw - 40, 225)], fill=(160, 160, 160), width=3)
        colour = NOTE_COLOURS[ci % len(NOTE_COLOURS)] if not c.get("colour") else hex_to_rgb(c["colour"])
        for ni, note in enumerate(c.get("notes", [])):
            note = ctx.fill(note)
            layer = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.rectangle([10, 12, size + 10, size + 12], fill=(0, 0, 0, 50))
            ld.rectangle([0, 0, size, size], fill=colour + (255,))
            ld.rectangle([0, 0, size, 26], fill=tuple(max(0, v - 18) for v in colour) + (255,))
            fs = 40 if size > 230 else 32
            lines = wrap(ld, note, hand(fs), size - 30)
            while len(lines) * (fs + 4) > size - 50 and fs > 22:
                fs -= 3
                lines = wrap(ld, note, hand(fs), size - 30)
            for li, ln in enumerate(lines):
                ld.text((16, 36 + li * (fs + 4)), ln, font=hand(fs), fill=INK["black"])
            col_i, row_i = ni % per_col, ni // per_col
            _rotated_paste(img, layer, (x0 + col_i * (size + 26), 250 + row_i * (size + 24)), r.uniform(-4, 4))
    return _photo_finish(img.convert("RGB"), r, 0.25)


def _receipt(item, ctx, r):
    f, fb = mono(24), mono(30)
    rc = ctx.fill_deep(item.get("receipt", item))
    w, cw = 560, 36
    lines = [("C", rc.get("merchant", "Shop").upper(), fb)]
    lines += [("C", part, f) for a in rc.get("address", []) for part in str(a).split(", ")]
    if rc.get("vat_no"):
        lines.append(("C", f"VAT No: {rc['vat_no']}", f))
    lines.append(("L", "-" * cw, f))
    dt = parse_date(rc.get("date"))
    lines.append(("L", f"{uk_date(dt) if dt else ''}  {rc.get('time', '')}".strip(), f))
    if rc.get("ref"):
        lines.append(("L", f"Ref: {rc['ref']}", f))
    lines.append(("L", "-" * cw, f))
    total = 0.0
    rows = rc.get("items", [])
    if isinstance(rows, str):  # e.g. "{{row.lines}}" from a dataset column holding a list literal
        import ast
        rows = ast.literal_eval(rows)
    for row in rows:
        desc, qty, price = (row[0], 1, row[1]) if len(row) == 2 else row
        amt = float(qty) * float(price)
        total += amt
        label = f"{qty} x {desc}" if float(qty) != 1 else str(desc)
        lines.append(("R", (label[:cw - 10], f"£{amt:,.2f}"), f))
    if rc.get("service"):
        sv = round(total * float(rc["service"]), 2)
        total += sv
        lines.append(("R", (f"Service {float(rc['service']) * 100:g}%", f"£{sv:,.2f}"), f))
    lines.append(("L", "-" * cw, f))
    lines.append(("R", ("TOTAL", f"£{total:,.2f}"), fb))
    if rc.get("vat", True):
        lines.append(("R", ("incl. VAT @ 20%", f"£{total / 6:,.2f}"), f))
    lines.append(("L", "", f))
    lines.append(("L", rc.get("payment", "VISA CONTACTLESS ****" + str(r.randint(1000, 9999))), f))
    lines.append(("L", f"AUTH CODE: {r.randint(100000, 999999)}", f))
    lines.append(("L", "", f))
    lines += [("C", t, f) for t in rc.get("footer", ["Thank you for your visit"])]
    h = 80 + sum(line_h(x[2], 1.25) for x in lines) + 60
    paper = Image.new("RGBA", (w, h), (250, 249, 244, 255))
    d = ImageDraw.Draw(paper)
    y = 50
    for al, txt, ff in lines:
        if al == "C":
            d.text((w / 2, y), txt, font=ff, fill=(45, 45, 50), anchor="ma")
        elif al == "R":
            d.text((26, y), txt[0], font=ff, fill=(45, 45, 50))
            d.text((w - 26, y), txt[1], font=ff, fill=(45, 45, 50), anchor="ra")
        else:
            d.text((26, y), txt, font=ff, fill=(45, 45, 50))
        y += line_h(ff, 1.25)
    for x in range(0, w, 14):  # torn edge
        d.polygon([(x, h), (x + 7, h - r.randint(4, 12)), (x + 14, h)], fill=(0, 0, 0, 0))
    fade = Image.linear_gradient("L").resize((w, h)).point(lambda v: v // 7)
    paper.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (w, h), (255, 255, 255)).split(), fade)))
    W, H = 1200, max(1500, h + 300)
    desk = Image.new("RGBA", (W, H), (96, 70, 48, 255))
    dd = ImageDraw.Draw(desk)
    for i in range(0, H, 6):  # wood grain
        g = r.randint(-8, 8)
        dd.line([(0, i), (W, i + r.randint(-6, 6))], fill=(96 + g, 70 + g, 48 + g), width=4)
    shadow = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([20, 24, w + 20, h + 24], fill=(0, 0, 0, 110))
    ang = r.uniform(-6, 6)
    _rotated_paste(desk, shadow.filter(ImageFilter.GaussianBlur(10)), ((W - w) / 2 - 10, (H - h) / 2), ang)
    _rotated_paste(desk, paper, ((W - w) / 2, (H - h) / 2), ang)
    return _photo_finish(desk.convert("RGB"), r, 0.4)


def _chart(item, ctx, r):
    ch = item["chart"]
    cats, series = ctx.resolve_chart(ch)
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    b = ctx.brand
    pal = [hex_to_rgb(b.get(k, "#444444")) for k in ("primary", "secondary", "accent", "dark")]
    d.text((70, 40), ctx.fill(ch.get("title") or item["title"]), font=font("bold", 40), fill=pal[0])
    if ch.get("subtitle"):
        d.text((70, 96), ctx.fill(ch["subtitle"]), font=font("regular", 24), fill=(100, 100, 100))
    L, T, R, B = 150, 160, W - 60, H - 150
    vals = [v for _, vs in series for v in vs] or [1]
    raw = (max(vals + [0]) - min(vals + [0])) or 1
    mag = 10 ** len(str(int(raw / 5))) / 10 if raw >= 5 else 0.1
    tick = next(m * mag for m in (1, 2, 2.5, 5, 10, 20) if raw / (m * mag) <= 6)
    mx, mn = tick * -(-max(vals + [0]) // tick), tick * (min(vals + [0]) // tick)
    span = (mx - mn) or 1
    fy = lambda v: B - (v - mn) / span * (B - T)
    fs = font("regular", 20)
    for i in range(int(round(span / tick)) + 1):
        v = mn + tick * i
        y = fy(v)
        d.line([(L, y), (R, y)], fill=(230, 230, 230), width=1)
        lab = f"{v:,.0f}" if span > 20 else f"{v:,.1f}"
        d.text((L - 12, y), lab, font=fs, fill=(110, 110, 110), anchor="rm")
    n = max(1, len(cats))
    step = (R - L) / n
    kind = ch.get("type", "column")
    for si, (name, vs) in enumerate(series):
        col = pal[si % len(pal)]
        if kind == "line":
            pts = [(L + step * (i + 0.5), fy(v)) for i, v in enumerate(vs)]
            d.line(pts, fill=col, width=5, joint="curve")
            for p in pts:
                d.ellipse([p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7], fill=col)
        else:
            bw = step * 0.7 / len(series)
            for i, v in enumerate(vs):
                x = L + step * i + step * 0.15 + si * bw
                d.rectangle([x, min(fy(v), fy(0)), x + bw - 4, max(fy(v), fy(0))], fill=col)
    for i, c in enumerate(cats):
        lab = str(c)
        if len(lab) > 14:
            lab = lab[:13] + "…"
        d.text((L + step * (i + 0.5), B + 14), lab, font=font("regular", 18 if n > 10 else 20), fill=(70, 70, 70), anchor="ma")
    if len(series) > 1:
        x = L
        for si, (name, _) in enumerate(series):
            d.rectangle([x, H - 60, x + 24, H - 36], fill=pal[si % len(pal)])
            d.text((x + 34, H - 62), str(name), font=fs, fill=(60, 60, 60))
            x += 60 + d.textlength(str(name), font=fs)
    d.text((W - 60, H - 40), f"Source: {ctx.fill(ch.get('source', ctx.company['fictional_name']))}", font=font("regular", 16),
           fill=(140, 140, 140), anchor="rm")
    return img


KINDS = {"whiteboard": _whiteboard, "sticky_notes": _sticky, "receipt": _receipt, "chart": _chart}


def render_image(item, ctx, path):
    img = KINDS[item.get("kind", "whiteboard")](item, ctx, rng(item))
    fmt = path.suffix.lower().lstrip(".")
    _save(img, path, "png" if fmt == "png" else "jpg", 80)
    _preview(ctx, item, [img])


def image_ext(item):
    if item["type"] == "scan":
        return "." + item.get("format", "pdf")
    return "." + item.get("format", "png" if item.get("kind") == "chart" else "jpg")
