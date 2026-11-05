"""Render a document spec (blocks) to a branded .docx."""
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .common import hex_to_rgb, inline_runs, parse_date, uk_date


def _rgb(h):
    return RGBColor(*hex_to_rgb(h))


def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill.lstrip("#"))
    tcPr.append(shd)


def _field(run, instr):
    for tag, text in (("begin", None), ("instr", instr), ("separate", None), ("end", None)):
        if tag == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        run._r.append(el)


def add_runs(par, text, size=None, color=None, bold=None):
    for t, b, i in inline_runs(text):
        r = par.add_run(t)
        r.bold = b or bold
        r.italic = i
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = _rgb(color)
    return par


def _table(doc, cols, rows, brand, widths=None, header=True):
    t = doc.add_table(rows=1 if header else 0, cols=len(cols))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if header:
        for i, c in enumerate(cols):
            cell = t.rows[0].cells[i]
            cell.text = ""
            add_runs(cell.paragraphs[0], str(c), size=9.5, color="#FFFFFF", bold=True)
            _shade(cell, brand["primary"])
    for ri, r in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(r[:len(cols)]):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], "" if v is None else str(v), size=9.5)
            if ri % 2 == 1:
                _shade(cells[i], brand.get("light", "#F4F6F8"))
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def setup_styles(doc, brand):
    st = doc.styles
    st["Normal"].font.name = brand.get("font_body", "Segoe UI")
    st["Normal"].font.size = Pt(10.5)
    st["Normal"].paragraph_format.space_after = Pt(6)
    st["Normal"].paragraph_format.line_spacing = 1.15
    for lvl, size, col in ((1, 16, brand["primary"]), (2, 13, brand["primary"]), (3, 11.5, brand["dark"])):
        s = st[f"Heading {lvl}"]
        s.font.name = brand.get("font_heading", "Segoe UI Semibold")
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.color.rgb = _rgb(col)
        s.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
        s.paragraph_format.space_after = Pt(4)
        rpr = s.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for a in ("w:ascii", "w:hAnsi", "w:cs"):
            rfonts.set(qn(a), s.font.name)
    for name in ("Title", "Subtitle"):
        st[name].font.name = brand.get("font_heading", "Segoe UI Semibold")


def render_blocks(doc, blocks, ctx):
    brand = ctx.brand
    for b in blocks:
        b = ctx.fill_deep(b)
        if "h1" in b:
            doc.add_heading(b["h1"], 1)
        elif "h2" in b:
            doc.add_heading(b["h2"], 2)
        elif "h3" in b:
            doc.add_heading(b["h3"], 3)
        elif "p" in b:
            add_runs(doc.add_paragraph(), b["p"])
        elif "bullets" in b:
            for x in b["bullets"]:
                lvl2 = isinstance(x, str) and x.startswith("  ")
                add_runs(doc.add_paragraph(style="List Bullet 2" if lvl2 else "List Bullet"), str(x).strip())
        elif "numbered" in b:
            for x in b["numbered"]:
                add_runs(doc.add_paragraph(style="List Number"), x)
        elif "table" in b:
            cols, rows = ctx.resolve_table(b["table"])
            if b["table"].get("caption"):
                p = doc.add_paragraph()
                add_runs(p, b["table"]["caption"], size=9, color="#555555", bold=True)
            _table(doc, cols, rows, brand, b["table"].get("widths"))
        elif "kv" in b:
            t = doc.add_table(rows=0, cols=2)
            t.style = "Table Grid"
            for k, v in b["kv"]:
                c = t.add_row().cells
                c[0].text = ""
                add_runs(c[0].paragraphs[0], str(k), size=9.5, bold=True)
                _shade(c[0], brand.get("light", "#F4F6F8"))
                c[0].width = Cm(5)
                c[1].text = ""
                add_runs(c[1].paragraphs[0], str(v), size=9.5)
                c[1].width = Cm(11.5)
            doc.add_paragraph()
        elif "callout" in b:
            t = doc.add_table(rows=1, cols=1)
            c = t.rows[0].cells[0]
            c.text = ""
            if b.get("title"):
                add_runs(c.paragraphs[0], b["title"], bold=True, color=brand["primary"])
                add_runs(c.add_paragraph(), b["callout"])
            else:
                add_runs(c.paragraphs[0], b["callout"])
            _shade(c, brand.get("light", "#F4F6F8"))
            doc.add_paragraph()
        elif "quote" in b:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1)
            add_runs(p, f"“{b['quote']}”", color=brand["primary"])
            if b.get("by"):
                add_runs(doc.add_paragraph(), f"— {b['by']}", size=9)
        elif "signature" in b:
            p = ctx.person(b["signature"])
            doc.add_paragraph()
            add_runs(doc.add_paragraph(), "Signed: ______________________")
            add_runs(doc.add_paragraph(), f"**{p.get('name', '')}**, {p.get('title', '')}")
            add_runs(doc.add_paragraph(), f"Date: {uk_date(b.get('date', ctx.company.get('as_of')))}")
        elif "actions" in b:
            cols = ["#", "Action", "Owner", "Due", "Status"]
            rows = []
            for i, a in enumerate(b["actions"], 1):
                own = ctx.person(a.get("owner")).get("name", a.get("owner", "")) if a.get("owner") in ctx.people else a.get("owner", "")
                rows.append([str(i), a.get("action", ""), own, uk_date(a["due"]) if a.get("due") else "", a.get("status", "Open")])
            _table(doc, cols, rows, brand)
        elif b.get("pagebreak"):
            doc.add_page_break()


def render_docx(item, ctx, path):
    brand = ctx.brand
    doc = Document()
    setup_styles(doc, brand)
    sec = doc.sections[0]
    if item.get("landscape"):
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin"):
        setattr(sec, side, Cm(2.2))
    sec.top_margin, sec.bottom_margin = Cm(2.4), Cm(2)

    # header: logo + classification
    hp = sec.header.paragraphs[0]
    hp.add_run().add_picture(ctx.brand_assets["logo_png"], height=Cm(0.9))
    hp.add_run("\t\t")
    cr = hp.add_run(item.get("classification", "Internal").upper())
    cr.font.size, cr.bold = Pt(8), True
    cr.font.color.rgb = _rgb(brand["secondary"])
    # footer
    fp = sec.footer.paragraphs[0]
    fr = fp.add_run(f"{ctx.company['legal_name']}  •  {ctx.fill(item['title'])}  •  v{item.get('version', '1.0')}  •  Page ")
    fr.font.size = Pt(8)
    fr.font.color.rgb = _rgb("#666666")
    pr = fp.add_run()
    pr.font.size = Pt(8)
    _field(pr, "PAGE")
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # title block
    p = doc.add_paragraph()
    add_runs(p, ctx.fill(item.get("doc_type_label", item.get("category", ""))).upper(), size=9, color=brand["secondary"], bold=True)
    p.paragraph_format.space_after = Pt(0)
    p = doc.add_paragraph()
    add_runs(p, ctx.fill(item["title"]), size=24, color=brand["primary"], bold=True)
    p.paragraph_format.space_after = Pt(2)
    if item.get("subtitle"):
        add_runs(doc.add_paragraph(), ctx.fill(item["subtitle"]), size=12, color="#555555")

    if item.get("doc_control", item.get("category") in ("Policy", "Procedure", "SOP", "Standard", "Plan", "Report", "Strategy", "Framework")):
        owner = ctx.person(item.get("owner") or item.get("author"))
        kv = [("Document owner", f"{owner.get('name', '')}, {owner.get('title', '')}"),
              ("Version", item.get("version", "1.0")),
              ("Status", item.get("status", "Approved")),
              ("Last updated", uk_date(item.get("modified", item.get("created", ctx.company.get("as_of"))))),
              ("Classification", item.get("classification", "Internal"))]
        if item.get("review_date"):
            kv.append(("Next review", uk_date(item["review_date"])))
        if item.get("approved_by"):
            kv.append(("Approved by", ctx.person_label(item["approved_by"])))
        render_blocks(doc, [{"kv": kv}], ctx)

    render_blocks(doc, item.get("blocks", []), ctx)

    if item.get("version_history"):
        doc.add_heading("Version history", 2)
        rows = [[v.get("version", ""), uk_date(v.get("date", "")), ctx.person(v.get("by")).get("name", v.get("by", "")),
                 v.get("change", "")] for v in item["version_history"]]
        _table(doc, ["Version", "Date", "Author", "Change"], rows, brand)

    cp = doc.core_properties
    cp.title = ctx.fill(item["title"])
    cp.author = ctx.person(item.get("author")).get("name", ctx.company["fictional_name"])
    cp.last_modified_by = ctx.person(item.get("modified_by") or item.get("author")).get("name", "")
    cp.subject = ctx.fill(item.get("summary", ""))[:250]
    cp.keywords = ", ".join(item.get("tags", []))
    cp.category = item.get("category", "")
    cp.comments = "Fictional training data. Not a real organisation."
    for k in ("created", "modified"):
        d = parse_date(item.get(k)) if item.get(k) else None
        if d:
            setattr(cp, k, d)
    doc.save(path)
