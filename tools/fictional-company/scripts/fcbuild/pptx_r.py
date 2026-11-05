"""Render a deck spec to a branded 16:9 .pptx using drawn layouts (no template dependency)."""
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from .common import hex_to_rgb, inline_runs, parse_date

W, H = Inches(13.333), Inches(7.5)


def C(h):
    return RGBColor(*hex_to_rgb(h))


def _rect(sl, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE):
    s = sl.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = C(fill)
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def _text(sl, x, y, w, h, text, size=18, color="#222222", bold=False, align=PP_ALIGN.LEFT,
          anchor=MSO_ANCHOR.TOP, font=None):
    tb = sl.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for t, b, it in inline_runs(line):
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size)
            r.font.bold = bold or b
            r.font.italic = it
            r.font.color.rgb = C(color)
            if font:
                r.font.name = font
    return tb


def _bullets(sl, x, y, w, h, items, brand, size=18):
    tb = sl.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for it in items:
        lvl = 1 if str(it).startswith("  ") else 0
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.level = lvl
        p.space_after = Pt(8)
        bullet = p.add_run()
        bullet.text = ("–  " if lvl else "■  ")
        bullet.font.size = Pt(size - 6 if not lvl else size - 4)
        bullet.font.color.rgb = C(brand["secondary"] if not lvl else "#888888")
        for t, b, i in inline_runs(str(it).strip()):
            r = p.add_run()
            r.text = t
            r.font.size = Pt(size - (3 if lvl else 0))
            r.font.bold = b
            r.font.italic = i
            r.font.color.rgb = C(brand["dark"] if not lvl else "#444444")
    return tb


def _chrome(sl, ctx, item, n, title=None):
    brand = ctx.brand
    _rect(sl, 0, 0, W, Inches(0.12), brand["primary"])
    if title:
        _text(sl, Inches(0.6), Inches(0.35), Inches(10.5), Inches(0.9), title, 28, brand["primary"], True,
              font=brand.get("font_heading"))
        _rect(sl, Inches(0.6), Inches(1.2), Inches(1.2), Inches(0.06), brand["accent"])
    sl.shapes.add_picture(ctx.brand_assets["logo_png"], Inches(11.2), Inches(0.35), height=Inches(0.42))
    _text(sl, Inches(0.6), Inches(7.0), Inches(9), Inches(0.35),
          f"{ctx.company['fictional_name']}  |  {ctx.fill(item['title'])}  |  {item.get('classification', 'Internal')}",
          9, "#888888")
    _text(sl, Inches(12.2), Inches(7.0), Inches(0.6), Inches(0.35), str(n), 9, "#888888", align=PP_ALIGN.RIGHT)


def _table(sl, x, y, w, cols, rows, brand, size=12):
    rows = rows[:14]
    shp = sl.shapes.add_table(len(rows) + 1, len(cols), x, y, w, Inches(0.4) * (len(rows) + 1))
    t = shp.table
    for i, c in enumerate(cols):
        cell = t.cell(0, i)
        cell.text = str(c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C(brand["primary"])
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.color.rgb = Pt(size), True, C("#FFFFFF")
    for ri, r in enumerate(rows, 1):
        for ci, v in enumerate(r[:len(cols)]):
            cell = t.cell(ri, ci)
            cell.text = "" if v is None else str(v)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C(brand.get("light", "#F4F6F8") if ri % 2 == 0 else "#FFFFFF")
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size, run.font.color.rgb = Pt(size - 1), C("#222222")


CHARTS = {"bar": XL_CHART_TYPE.BAR_CLUSTERED, "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
          "stacked": XL_CHART_TYPE.COLUMN_STACKED, "line": XL_CHART_TYPE.LINE_MARKERS,
          "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT}


def _chart(sl, x, y, w, h, ch, ctx):
    brand = ctx.brand
    cats, series = ctx.resolve_chart(ch)
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    kind = ch.get("type", "column")
    gf = sl.shapes.add_chart(CHARTS.get(kind, XL_CHART_TYPE.COLUMN_CLUSTERED), x, y, w, h, cd)
    chart = gf.chart
    palette = [brand["primary"], brand["secondary"], brand["accent"], "#7F8C8D", brand["dark"], "#A3C4DC"]
    chart.has_legend = len(series) > 1 or kind in ("pie", "doughnut")
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(11)
    if kind in ("pie", "doughnut"):
        for i, pt in enumerate(chart.plots[0].series[0].points):
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = C(palette[i % len(palette)])
    else:
        for i, s in enumerate(chart.plots[0].series):
            if kind == "line":
                s.format.line.color.rgb = C(palette[i % len(palette)])
                s.format.line.width = Pt(2.5)
                s.marker.format.fill.solid()
                s.marker.format.fill.fore_color.rgb = C(palette[i % len(palette)])
                s.marker.format.line.color.rgb = C(palette[i % len(palette)])
            else:
                s.format.fill.solid()
                s.format.fill.fore_color.rgb = C(palette[i % len(palette)])
        chart.value_axis.has_major_gridlines = True
        chart.value_axis.major_gridlines.format.line.color.rgb = C("#E3E3E3")
        chart.value_axis.tick_labels.font.size = Pt(11)
        chart.category_axis.tick_labels.font.size = Pt(11)
        if ch.get("number_format"):
            chart.value_axis.tick_labels.number_format = ch["number_format"]
            chart.value_axis.tick_labels.number_format_is_linked = False
    if ch.get("labels"):
        pl = chart.plots[0]
        pl.has_data_labels = True
        pl.data_labels.font.size = Pt(10)
        if ch.get("number_format"):
            pl.data_labels.number_format = ch["number_format"]
            pl.data_labels.number_format_is_linked = False
    if ch.get("title"):
        chart.has_title = True
        chart.chart_title.text_frame.text = ch["title"]
        chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
    else:
        chart.has_title = False


def render_pptx(item, ctx, path):
    brand = ctx.brand
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]
    for n, s in enumerate(item.get("slides", []), 1):
        s = ctx.fill_deep(s)
        sl = prs.slides.add_slide(blank)
        lay = s.get("layout", "bullets")
        title = s.get("title", "")
        if lay == "title":
            _rect(sl, 0, 0, W, H, brand["primary"])
            _rect(sl, 0, H - Inches(0.35), W, Inches(0.35), brand["accent"])
            sl.shapes.add_picture(ctx.brand_assets["logo_white_png"], Inches(0.8), Inches(0.7), height=Inches(0.7))
            _text(sl, Inches(0.8), Inches(2.4), Inches(11.5), Inches(1.8), title, 44, "#FFFFFF", True,
                  anchor=MSO_ANCHOR.BOTTOM, font=brand.get("font_heading"))
            _text(sl, Inches(0.8), Inches(4.3), Inches(11.5), Inches(1.0), s.get("subtitle", ""), 22, "#FFFFFF")
            meta = s.get("meta") or " | ".join(x for x in [ctx.person_label(item.get("author")),
                                                           parse_date(item.get("created")).strftime("%B %Y") if item.get("created") else ""] if x)
            _text(sl, Inches(0.8), Inches(6.0), Inches(11), Inches(0.5), meta, 14, "#FFFFFF")
        elif lay == "section":
            _rect(sl, 0, 0, W, H, brand["dark"])
            _rect(sl, Inches(0.8), Inches(3.0), Inches(0.12), Inches(1.5), brand["accent"])
            _text(sl, Inches(1.2), Inches(2.9), Inches(11), Inches(1.0), title, 40, "#FFFFFF", True,
                  font=brand.get("font_heading"))
            _text(sl, Inches(1.2), Inches(3.9), Inches(11), Inches(0.8), s.get("subtitle", ""), 20, "#DDDDDD")
            _text(sl, Inches(12.2), Inches(7.0), Inches(0.6), Inches(0.35), str(n), 9, "#AAAAAA", align=PP_ALIGN.RIGHT)
        else:
            _chrome(sl, ctx, item, n, title)
            top = Inches(1.55)
            if s.get("subtitle"):
                _text(sl, Inches(0.6), Inches(1.3), Inches(12), Inches(0.5), s["subtitle"], 15, "#666666")
                top = Inches(1.9)
            body_h = Inches(6.8) - top
            if lay == "bullets":
                _bullets(sl, Inches(0.7), top, Inches(12), body_h, s.get("bullets", []), brand)
            elif lay == "two_column":
                for k, x in (("left", Inches(0.7)), ("right", Inches(6.9))):
                    col = s.get(k, {})
                    if isinstance(col, list):
                        col = {"bullets": col}
                    y = top
                    if col.get("heading"):
                        _rect(sl, x, y, Inches(5.8), Inches(0.5), brand["light"])
                        _text(sl, x + Inches(0.15), y, Inches(5.5), Inches(0.5), col["heading"], 16, brand["primary"], True,
                              anchor=MSO_ANCHOR.MIDDLE)
                        y += Inches(0.65)
                    if col.get("chart"):
                        _chart(sl, x, y, Inches(5.8), Inches(6.7) - y, col["chart"], ctx)
                    else:
                        _bullets(sl, x, y, Inches(5.8), Inches(6.7) - y, col.get("bullets", []), brand, 16)
            elif lay == "table":
                cols, rows = ctx.resolve_table(s["table"])
                _table(sl, Inches(0.7), top, Inches(11.9), cols, rows, brand, s["table"].get("size", 12))
            elif lay == "chart":
                if s.get("bullets"):
                    _chart(sl, Inches(0.6), top, Inches(8.0), body_h, s["chart"], ctx)
                    _bullets(sl, Inches(8.9), top + Inches(0.2), Inches(3.9), body_h, s["bullets"], brand, 15)
                else:
                    _chart(sl, Inches(0.8), top, Inches(11.7), body_h, s["chart"], ctx)
            elif lay == "kpis":
                kp = s.get("kpis", [])[:6]
                per_row = 3 if len(kp) > 4 else len(kp) or 1
                bw = (Inches(11.9) - Inches(0.3) * (per_row - 1)) / per_row
                for i, k in enumerate(kp):
                    r, c = divmod(i, per_row)
                    x = Inches(0.7) + c * (bw + Inches(0.3))
                    y = top + r * Inches(2.4)
                    _rect(sl, x, y, bw, Inches(2.1), brand["light"], MSO_SHAPE.ROUNDED_RECTANGLE).adjustments[0] = 0.08
                    _rect(sl, x, y, Inches(0.1), Inches(2.1), brand["secondary"])
                    _text(sl, x + Inches(0.35), y + Inches(0.25), bw - Inches(0.5), Inches(1.0), str(k.get("value", "")), 36,
                          brand["primary"], True)
                    _text(sl, x + Inches(0.35), y + Inches(1.15), bw - Inches(0.5), Inches(0.5), k.get("label", ""), 15,
                          brand["dark"], True)
                    if k.get("note"):
                        _text(sl, x + Inches(0.35), y + Inches(1.55), bw - Inches(0.5), Inches(0.5), k["note"], 12, "#666666")
            elif lay == "steps":
                st = s.get("steps", [])[:6]
                bw = (Inches(11.9) - Inches(0.15) * (len(st) - 1)) / max(len(st), 1)
                for i, step in enumerate(st):
                    x = Inches(0.7) + i * (bw + Inches(0.15))
                    shp = _rect(sl, x, top + Inches(0.2), bw, Inches(1.0),
                                [brand["primary"], brand["secondary"]][i % 2], MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON)
                    tf = shp.text_frame
                    tf.word_wrap = True
                    tf.margin_left = tf.margin_right = Inches(0.25)
                    label = step.get("label", "")
                    tf.text = label
                    longest = max([len(w) for w in label.split()] + [1])
                    size = 14 if len(st) <= 4 and longest <= 10 else 12 if longest <= 9 else 10
                    for r in tf.paragraphs[0].runs:
                        r.font.size, r.font.bold, r.font.color.rgb = Pt(size), True, C("#FFFFFF")
                    _text(sl, x + Inches(0.1), top + Inches(1.45), bw - Inches(0.2), Inches(3.5), step.get("text", ""), 13, "#333333")
            elif lay == "quote":
                _text(sl, Inches(1.2), top + Inches(0.6), Inches(10.9), Inches(3), f"“{s.get('quote', '')}”", 30,
                      brand["primary"], False, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
                _text(sl, Inches(1.2), top + Inches(3.8), Inches(10.9), Inches(0.6), s.get("by", ""), 16, "#666666",
                      align=PP_ALIGN.CENTER)
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = s["notes"]
    cp = prs.core_properties
    cp.title = ctx.fill(item["title"])
    cp.author = ctx.person(item.get("author")).get("name", ctx.company["fictional_name"])
    cp.subject = ctx.fill(item.get("summary", ""))[:250]
    cp.keywords = ", ".join(item.get("tags", []))
    cp.comments = "Fictional training data. Not a real organisation."
    for k in ("created", "modified"):
        d = parse_date(item.get(k)) if item.get(k) else None
        if d:
            setattr(cp, k, d)
    prs.save(path)
