"""Render workbook specs to branded .xlsx (data as Excel Tables so Copilot in Excel can use them)."""
import re

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from .common import parse_date

NUMFMT = {"gbp": '"£"#,##0', "gbp2": '"£"#,##0.00', "pct": "0.0%", "int": "#,##0", "num": "#,##0.0",
          "date": "dd/mm/yyyy", "datetime": "dd/mm/yyyy hh:mm"}
_used_names = set()


def _tname(name):
    base = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not base or not base[0].isalpha():
        base = "T_" + base
    n, i = base[:240], 2
    while n.lower() in _used_names:
        n, i = f"{base[:236]}_{i}", i + 1
    _used_names.add(n.lower())
    return n


def _guess_fmt(col, vals):
    c = col.lower()
    if any(k in c for k in ("£", "gbp", "cost", "value", "revenue", "budget", "amount", "price", "salary", "spend", "fee", "invoice_total", "forecast", "actual")):
        if all(isinstance(v, (int, float)) or v is None for v in vals):
            return "gbp"
    if any(k in c for k in ("rate", "pct", "percent", "%")) and all(isinstance(v, (int, float)) and abs(v) <= 1 or v is None for v in vals):
        return "pct"
    if all(isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in vals if v) and any(vals):
        return "date"
    if all(isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?", v) for v in vals if v) and any(vals):
        return "datetime"
    return None


def _write_sheet(ws, cols, rows, brand, fmts=None, as_table=True, table_name=None, start_row=1):
    fmts = dict(fmts or {})
    hdr_fill = PatternFill("solid", fgColor=brand["primary"].lstrip("#"))
    thin = Side(style="thin", color="D9D9D9")
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row=start_row, column=i, value=c)
        cell.font = Font(bold=True, color="FFFFFF", name="Calibri")
        cell.fill = hdr_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for ci, c in enumerate(cols):
        if c not in fmts:
            g = _guess_fmt(c, [r[ci] for r in rows[:200] if ci < len(r)])
            if g:
                fmts[c] = g
    for ri, r in enumerate(rows, start_row + 1):
        for ci, v in enumerate(r, 1):
            col = cols[ci - 1] if ci - 1 < len(cols) else None
            f = fmts.get(col)
            if f in ("date", "datetime") and isinstance(v, str) and v:
                v = parse_date(v) or v
            if isinstance(v, bool):
                v = "Yes" if v else "No"
            cell = ws.cell(row=ri, column=ci, value=v)
            cell.border = Border(bottom=thin)
            if f in NUMFMT:
                cell.number_format = NUMFMT[f]
            elif f:
                cell.number_format = f
    # widths
    for ci, c in enumerate(cols, 1):
        sample = [len(str(c))] + [len(str(r[ci - 1])) for r in rows[:300] if ci - 1 < len(r) and r[ci - 1] is not None]
        ws.column_dimensions[get_column_letter(ci)].width = min(max(sample) + 3, 60)
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    if as_table and rows and not any(isinstance(v, str) and v.startswith("=") for r in rows for v in r):
        ref = f"A{start_row}:{get_column_letter(len(cols))}{start_row + len(rows)}"
        t = Table(displayName=_tname(table_name or ws.title), ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(t)
    elif rows:
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(cols))}{start_row + len(rows)}"
    return start_row + len(rows)


def _add_chart(ws, ch, header_row, last_row, cols):
    kind = ch.get("type", "bar")
    chart = {"line": LineChart, "pie": PieChart}.get(kind, BarChart)()
    if kind == "bar":
        chart.type = "bar" if ch.get("horizontal") else "col"
    chart.title = ch.get("title")
    chart.height, chart.width = 8, 16
    cat_idx = cols.index(ch["cat_col"]) + 1
    for vc in ch["val_cols"]:
        vi = cols.index(vc) + 1
        data = Reference(ws, min_col=vi, min_row=header_row, max_row=last_row)
        chart.add_data(data, titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=cat_idx, min_row=header_row + 1, max_row=last_row))
    ws.add_chart(chart, ch.get("anchor", f"{get_column_letter(len(cols) + 2)}2"))


def render_xlsx(item, ctx, path):
    brand = ctx.brand
    wb = Workbook()
    wb.remove(wb.active)
    for sh in item.get("sheets", []):
        sh = ctx.fill_deep(sh)
        ws = wb.create_sheet(sh.get("name", "Sheet")[:31])
        if sh.get("text"):  # README / notes sheet
            ws.column_dimensions["A"].width = 110
            ws["A1"] = sh.get("heading", item["title"])
            ws["A1"].font = Font(bold=True, size=16, color=brand["primary"].lstrip("#"))
            for i, line in enumerate(sh["text"], 3):
                ws.cell(row=i, column=1, value=line).alignment = Alignment(wrap_text=True)
            continue
        if "sql" in sh:
            cols, rows = ctx.query(sh["sql"])
            if sh.get("columns"):
                cols = sh["columns"]
        else:
            cols, rows = sh.get("columns", []), [list(r) for r in sh.get("rows", [])]
        last = _write_sheet(ws, cols, rows, brand, sh.get("format"), sh.get("as_table", True),
                            f"{item.get('id', 'wb')}_{sh.get('name', 'Sheet')}")
        if sh.get("totals"):
            r = last + 1
            ws.cell(row=r, column=1, value="Total").font = Font(bold=True)
            for c in sh["totals"]:
                ci = cols.index(c) + 1
                L = get_column_letter(ci)
                cell = ws.cell(row=r, column=ci, value=f"=SUBTOTAL(109,{L}2:{L}{last})")
                cell.font = Font(bold=True)
                cell.number_format = ws.cell(row=2, column=ci).number_format
        if sh.get("chart"):
            _add_chart(ws, sh["chart"], 1, last, cols)
    wb.properties.title = ctx.fill(item["title"])
    wb.properties.creator = ctx.person(item.get("author")).get("name", ctx.company["fictional_name"])
    wb.properties.subject = ctx.fill(item.get("summary", ""))[:250]
    wb.properties.keywords = ", ".join(item.get("tags", []))
    wb.properties.description = "Fictional training data. Not a real organisation."
    if item.get("created"):
        wb.properties.created = parse_date(item["created"])
    if item.get("modified"):
        wb.properties.modified = parse_date(item["modified"])
    wb.save(path)


def write_tables_workbook(conn, meta, path, brand):
    wb = Workbook()
    ws = wb.active
    ws.title = "Index"
    _write_sheet(ws, ["Table", "Title", "Rows", "Owner", "System", "Description"],
                 [[m["name"], m["title"], m["row_count"], m["owner_department"], m["system"], m["description"]] for m in meta],
                 brand, as_table=True, table_name="Index_of_tables")
    for m in meta:
        cur = conn.execute(f'SELECT * FROM "{m["name"]}"')
        cols = [c[0] for c in cur.description]
        _write_sheet(wb.create_sheet(m["name"][:31]), cols, [list(r) for r in cur.fetchall()], brand,
                     table_name=m["name"])
    wb.save(path)
