"""Shared helpers: spec loading, placeholder filling, formatting, inline markup."""
import json
import re
import sqlite3
import unicodedata
from datetime import date, datetime
from pathlib import Path

WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print(f"  ! {msg}")


def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        raise FileNotFoundError(p)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def slugify(text, sep="-"):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", sep, text).strip(sep).lower()
    return text or "item"


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*#%\x00-\x1f]', "", str(name)).strip().rstrip(".")
    return re.sub(r"\s+", " ", name)[:120] or "Untitled"


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def fmt_value(v, fmt=None):
    if v is None:
        return ""
    try:
        if fmt == "gbp":
            return f"£{float(v):,.0f}"
        if fmt == "gbp2":
            return f"£{float(v):,.2f}"
        if fmt == "pct":
            f = float(v)
            return f"{f * 100:.1f}%" if abs(f) <= 1 else f"{f:.1f}%"
        if fmt == "int":
            return f"{int(round(float(v))):,}"
        if fmt == "num":
            return f"{float(v):,.1f}"
        if fmt == "date":
            return uk_date(v)
    except (TypeError, ValueError):
        pass
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return str(v)


def parse_date(v):
    if isinstance(v, (date, datetime)):
        return v
    s = str(v)
    for f in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if "T" in s or " " in s else s[:10], f)
        except ValueError:
            continue
    return None


def uk_date(v, with_time=False):
    d = parse_date(v)
    if not d:
        return str(v)
    if with_time and isinstance(d, datetime):
        return d.strftime("%d/%m/%Y %H:%M")
    return d.strftime("%d/%m/%Y")


def long_date(v):
    d = parse_date(v)
    return f"{d.day} {d.strftime('%B %Y')}" if d else str(v)


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")


def inline_runs(text):
    """Split '**bold** and *italic*' into [(text, bold, italic)]."""
    out = []
    for part in INLINE_RE.split(str(text)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append((part[2:-2], True, False))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append((part[1:-1], False, True))
        else:
            out.append((part, False, False))
    return out


def inline_html(text):
    import html
    s = html.escape(str(text))
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    return s


class Context:
    """Everything a renderer needs: company world model, db, facts, brand assets, paths."""

    def __init__(self, company, db, facts, out_root, brand_assets):
        self.company = company
        self.db = db
        self.facts = facts  # id -> fact dict (with 'answer')
        self.out_root = Path(out_root)
        self.brand = company.get("brand", {})
        self.brand_assets = brand_assets
        self.people = {p["id"]: p for p in company.get("people", [])}
        self.departments = {d["id"]: d for d in company.get("departments", [])}
        self.items = {}  # content id -> item (after render: has 'out_path')
        self.row = None

    # ---- placeholders -------------------------------------------------
    PH = re.compile(r"\{\{\s*(.+?)\s*\}\}")

    def fill(self, text, row=None):
        if not isinstance(text, str) or "{{" not in text:
            return text
        row = row if row is not None else self.row

        def rep(m):
            key = m.group(1)
            try:
                return self._resolve(key, row)
            except Exception as e:  # noqa
                warn(f"placeholder '{{{{{key}}}}}' unresolved: {e}")
                return m.group(0)

        return self.PH.sub(rep, text)

    def _resolve(self, key, row):
        fmt = None
        head, sep, tail = key.rpartition("|")
        if sep and tail.strip() in ("gbp", "gbp2", "pct", "int", "num", "date"):  # so SQL's || still works
            key, fmt = head.strip(), tail.strip()
        if key == "today":
            return long_date(self.company.get("as_of", date.today().isoformat()))
        if key.startswith("fact:"):
            f = self.facts[key[5:]]
            return fmt_value(f.get("raw", f["answer"]), fmt) if fmt else str(f["answer"])
        if key.startswith("row."):
            return fmt_value(row[key[4:]], fmt)
        if key.startswith("sql:"):
            r = self.db.execute(key[4:]).fetchone()
            return fmt_value(r[0] if r else None, fmt)
        if key.startswith("person:"):
            pid, _, field = key[7:].partition(".")
            return str(self.people[pid].get(field or "name", ""))
        if key.startswith("company."):
            cur = self.company
            for part in key[8:].split("."):
                cur = cur[int(part)] if isinstance(cur, list) else cur[part]
            return fmt_value(cur, fmt)
        raise KeyError(key)

    def fill_deep(self, obj, row=None):
        if isinstance(obj, str):
            return self.fill(obj, row)
        if isinstance(obj, list):
            return [self.fill_deep(o, row) for o in obj]
        if isinstance(obj, dict):
            return {k: self.fill_deep(v, row) for k, v in obj.items()}
        return obj

    # ---- data ---------------------------------------------------------
    def query(self, sql):
        cur = self.db.execute(sql)
        cols = [c[0] for c in cur.description]
        return cols, [list(r) for r in cur.fetchall()]

    def resolve_table(self, t):
        """A table block -> (columns, rows[str]). Supports inline rows or sql."""
        fmts = t.get("format", {})
        if "sql" in t:
            cols, rows = self.query(self.fill(t["sql"]))
            if t.get("columns"):
                cols = t["columns"]
        else:
            cols, rows = t.get("columns", []), t.get("rows", [])
        out = []
        for r in rows:
            out.append([self.fill(fmt_value(v, fmts.get(c)) if not isinstance(v, str) or c in fmts else v)
                        for c, v in zip(cols, r)])
        return cols, out

    def resolve_chart(self, ch):
        """Chart spec -> (categories, [(name, values)])."""
        if "sql" in ch:
            cols, rows = self.query(self.fill(ch["sql"]))
            cats = [str(r[0]) for r in rows]
            series = [(cols[i], [float(r[i] or 0) for r in rows]) for i in range(1, len(cols))]
            return cats, series
        return ch["categories"], [(s["name"], s["values"]) for s in ch["series"]]

    def person(self, pid):
        if not pid:
            return {}
        p = self.people.get(pid)
        if not p:
            warn(f"unknown person id {pid}")
            return {"name": pid, "title": "", "email": ""}
        return p

    def person_label(self, pid):
        p = self.person(pid)
        return f"{p.get('name', '')}, {p.get('title', '')}".strip(", ")


def open_db(path):
    conn = sqlite3.connect(path)
    return conn
