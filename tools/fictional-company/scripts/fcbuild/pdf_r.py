"""Render a document spec to a branded PDF (letterhead style) with reportlab."""
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from .common import uk_date


def _md(text):
    s = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)


def render_pdf(item, ctx, path):
    b = ctx.brand
    P, S, A, D, L = (colors.HexColor(b[k]) for k in ("primary", "secondary", "accent", "dark", "light"))
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11)
    h = {1: ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=15, textColor=P, spaceBefore=12, spaceAfter=6),
         2: ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=12.5, textColor=P, spaceBefore=10, spaceAfter=4),
         3: ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold", fontSize=11, textColor=D, spaceBefore=8, spaceAfter=3)}
    title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=P, spaceAfter=4)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    cellh = ParagraphStyle("cellh", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)

    def table(cols, rows, kv=False):
        data = ([] if kv else [[Paragraph(_md(c), cellh) for c in cols]]) + \
               [[Paragraph(_md("" if v is None else v), cell) for v in r[:len(cols) if cols else None]] for r in rows]
        width = 16.6 * cm
        cw = [5 * cm, width - 5 * cm] if kv else [width / max(len(cols), 1)] * len(cols)
        t = Table(data, colWidths=cw, repeatRows=0 if kv else 1)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
                 ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if kv:
            style.append(("BACKGROUND", (0, 0), (0, -1), L))
        else:
            style.append(("BACKGROUND", (0, 0), (-1, 0), P))
            style += [("BACKGROUND", (0, i), (-1, i), L) for i in range(2, len(data), 2)]
        t.setStyle(TableStyle(style))
        return [t, Spacer(1, 8)]

    story = [Paragraph(_md(ctx.fill(item.get("doc_type_label", item.get("category", ""))).upper()),
                       ParagraphStyle("lbl", parent=small, textColor=S, fontName="Helvetica-Bold")),
             Paragraph(_md(ctx.fill(item["title"])), title)]
    if item.get("subtitle"):
        story.append(Paragraph(_md(ctx.fill(item["subtitle"])), ParagraphStyle("st", parent=body, fontSize=12, textColor=colors.HexColor("#555555"))))
    story.append(Spacer(1, 8))
    for blk in item.get("blocks", []):
        blk = ctx.fill_deep(blk)
        if "h1" in blk or "h2" in blk or "h3" in blk:
            lvl = 1 if "h1" in blk else 2 if "h2" in blk else 3
            story.append(Paragraph(_md(blk[f"h{lvl}"]), h[lvl]))
        elif "p" in blk:
            story.append(Paragraph(_md(blk["p"]), body))
        elif "bullets" in blk or "numbered" in blk:
            items = blk.get("bullets") or blk.get("numbered")
            story.append(ListFlowable([ListItem(Paragraph(_md(str(x).strip()), body), leftIndent=12) for x in items],
                                      bulletType="1" if "numbered" in blk else "bullet", start=None if "numbered" in blk else "•",
                                      leftIndent=14))
        elif "table" in blk:
            cols, rows = ctx.resolve_table(blk["table"])
            if blk["table"].get("caption"):
                story.append(Paragraph(f"<b>{_md(blk['table']['caption'])}</b>", small))
            story += table(cols, rows)
        elif "kv" in blk:
            story += table(None, [[k, v] for k, v in blk["kv"]], kv=True)
        elif "callout" in blk:
            t = Table([[Paragraph((f"<b>{_md(blk['title'])}</b><br/>" if blk.get("title") else "") + _md(blk["callout"]), body)]],
                      colWidths=[16.6 * cm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), L), ("LINEBEFORE", (0, 0), (0, -1), 3, S),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            story += [t, Spacer(1, 8)]
        elif "signature" in blk:
            p = ctx.person(blk["signature"])
            story.append(KeepTogether([Spacer(1, 16), Paragraph("Signed: ______________________", body),
                                       Paragraph(f"<b>{_md(p.get('name', ''))}</b>, {_md(p.get('title', ''))}", body),
                                       Paragraph(f"Date: {uk_date(blk.get('date', ctx.company.get('as_of')))}", body)]))
        elif "actions" in blk:
            rows = [[str(i), a.get("action", ""), ctx.people.get(a.get("owner"), {}).get("name", a.get("owner", "")),
                     uk_date(a["due"]) if a.get("due") else "", a.get("status", "Open")] for i, a in enumerate(blk["actions"], 1)]
            story += table(["#", "Action", "Owner", "Due", "Status"], rows)
        elif blk.get("pagebreak"):
            story.append(PageBreak())

    co = ctx.company
    addr = co.get("hq", {})
    addr_line = ", ".join(x for x in [addr.get("line1"), addr.get("city"), addr.get("postcode")] if x)

    def page(c, d):
        c.saveState()
        c.setFillColor(P)
        c.rect(0, A4[1] - 0.25 * cm, A4[0], 0.25 * cm, fill=1, stroke=0)
        c.drawImage(ctx.brand_assets["logo_png"], 2.2 * cm, A4[1] - 2.0 * cm, height=1.0 * cm, width=3.6 * cm,
                    preserveAspectRatio=True, mask="auto", anchor="w")
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(S)
        c.drawRightString(A4[0] - 2.2 * cm, A4[1] - 1.5 * cm, item.get("classification", "Internal").upper())
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#777777"))
        reg = str(co.get("company_number", "00000000"))
        reg = f"Registered in England & Wales No. {reg}" if reg.replace(" ", "").isdigit() else reg.split(" · ")[0]  # e.g. a society number
        c.drawString(2.2 * cm, 1.2 * cm, f"{co['legal_name']}  •  {addr_line}  •  {reg}")
        c.drawRightString(A4[0] - 2.2 * cm, 1.2 * cm, f"Page {d.page}")
        c.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2.8 * cm,
                            bottomMargin=2.0 * cm, title=ctx.fill(item["title"]),
                            author=ctx.person(item.get("author")).get("name", co["fictional_name"]),
                            subject=ctx.fill(item.get("summary", ""))[:200], creator=co["fictional_name"],
                            keywords=", ".join(item.get("tags", [])))
    doc.build(story, onFirstPage=page, onLaterPages=page)
