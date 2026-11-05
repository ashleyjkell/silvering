"""Generate linked tabular datasets from a declarative spec -> SQLite + CSV + XLSX."""
import csv
import math
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from faker import Faker

from .common import parse_date, warn


def _rand_date(rng, start, end, weekdays=False):
    s, e = parse_date(start), parse_date(end)
    span = max((e - s).days, 0)
    for _ in range(20):
        d = s + timedelta(days=rng.randint(0, span))
        if not weekdays or d.weekday() < 5:
            break
    return d.date().isoformat() if isinstance(d, datetime) else d.isoformat()


class Generator:
    def __init__(self, spec, company):
        seed = spec.get("seed", 42)
        self.rng = random.Random(seed)
        self.fake = Faker(spec.get("locale", "en_GB"))
        self.fake.seed_instance(seed)
        self.company = company
        self.tables = {}  # name -> list[dict]
        self.columns = {}  # name -> list[str]
        self.as_of = company.get("as_of", date.today().isoformat())

    def env(self, row):
        e = {"rnd": self.rng, "math": math, "date": date, "datetime": datetime, "timedelta": timedelta,
             "d": lambda v: parse_date(v), "fake": self.fake, "as_of": parse_date(self.as_of),
             "tables": self.tables, "round": round, "min": min, "max": max, "int": int, "float": float,
             "str": str, "len": len, "abs": abs, "sum": sum, "choice": self.rng.choice,
             "company": self.company, "base": row.get("_base", {}), "item": row.get("_item")}
        e.update(row)
        e["row"] = row
        return e

    def gen_value(self, c, row, i):
        g = c.get("gen", "const")
        rng = self.rng
        if "when" in c and not eval(c["when"], self.env(row)):
            return c.get("else")
        if c.get("null_rate") and rng.random() < c["null_rate"]:
            return None
        if g == "seq":
            n = c.get("start", 1) + i * c.get("step", 1)
            return f"{c.get('prefix', '')}{str(n).zfill(c.get('pad', 0))}" if c.get("prefix") or c.get("pad") else n
        if g == "const":
            return c.get("value")
        if g == "base":  # field from the parent row when the table is built with from_table
            return row["_base"].get(c.get("field", c["name"]))
        if g == "carried":  # value already set by an earlier fk/people 'carry'
            return row.get(c["name"])
        if g == "faker":
            return getattr(self.fake, c["provider"])(**c.get("args", {}))
        if g == "choice":
            return rng.choices(c["values"], weights=c.get("weights"))[0]
        if g == "int":
            if "mean" in c:
                v = int(round(rng.gauss(c["mean"], c.get("sd", 1))))
                return max(c.get("min", v), min(c.get("max", v), v))
            return rng.randint(c["min"], c["max"])
        if g == "float":
            if "mean" in c:
                v = rng.gauss(c["mean"], c.get("sd", 1))
                v = max(c.get("min", v), min(c.get("max", v), v))
            else:
                v = rng.uniform(c["min"], c["max"])
            return round(v, c.get("digits", 2))
        if g == "bool":
            return rng.random() < c.get("p", 0.5)
        if g == "date":
            return _rand_date(rng, c.get("start"), c.get("end", self.as_of), c.get("weekdays", False))
        if g == "datetime":
            dd = _rand_date(rng, c.get("start"), c.get("end", self.as_of), c.get("weekdays", True))
            h = rng.randint(c.get("hour_min", 8), c.get("hour_max", 17))
            return f"{dd}T{h:02d}:{rng.choice([0, 15, 30, 45]):02d}:00"
        if g == "date_offset":
            base = parse_date(row.get(c["from"]))
            if not base:
                return None
            d = base + timedelta(days=rng.randint(c.get("days_min", 0), c.get("days_max", 0)))
            if c.get("cap_as_of") and d > parse_date(self.as_of):
                return None if c.get("cap_as_of") == "null" else self.as_of
            return d.date().isoformat()
        if g == "fk":
            src = self.tables.get(c["table"])
            if not src:
                raise ValueError(f"fk to unknown/earlier table {c['table']}")
            pool = src
            if "filter" in c:
                pool = [r for r in src if eval(c["filter"], self.env({**row, "ref": r}))] or src
            weights = [float(r.get(c["weight_col"]) or 1) for r in pool] if c.get("weight_col") else None
            ref = rng.choices(pool, weights=weights)[0]
            for new, old in c.get("carry", {}).items():
                row[new] = ref.get(old)
            return ref.get(c.get("column"))
        if g == "people":
            pool = self.company.get("people", [])
            if c.get("department"):
                deps = c["department"] if isinstance(c["department"], list) else [c["department"]]
                pool = [p for p in pool if p.get("department") in deps]
            if c.get("title_contains"):
                pool = [p for p in pool if c["title_contains"].lower() in p.get("title", "").lower()] or pool
            if not pool:
                warn(f"people gen for {c['name']} found no matching people")
                return None
            p = rng.choice(pool)
            for new, old in c.get("carry", {}).items():
                row[new] = p.get(old)
            return p.get(c.get("field", "id"))
        if g == "template":
            v = c["template"].format(**{k: ("" if val is None else val) for k, val in row.items()})
            return v.lower().replace(" ", "") if c.get("lower") else v
        if g == "expr":
            return eval(c["expr"], self.env(row))
        raise ValueError(f"unknown gen '{g}'")

    def build_table(self, t):
        name = t["name"]
        if "data" in t:
            cols = [c if isinstance(c, str) else c["name"] for c in t["columns"]]
            rows = [dict(zip(cols, r)) for r in t["data"]]
        elif "from_company" in t:
            src = self.company.get(t["from_company"], [])
            cols = t.get("columns") or sorted({k for r in src for k in r if not isinstance(r[k], (list, dict))})
            cols = [c if isinstance(c, str) else c["name"] for c in cols]
            rows = [{c: (r.get(c) if not isinstance(r.get(c), (list, dict)) else None) for c in cols} for r in src]
        else:
            specs = t["columns"]
            cols = [c["name"] for c in specs]
            seeds = [dict(r) for r in t.get("seed_rows", [])]
            if t.get("seed_from_company"):
                m = t.get("map", {})
                for r in self.company.get(t["seed_from_company"], []):
                    seeds.append({col: r.get(src) for col, src in m.items()})
            bases = [None] * t.get("rows", 0)
            if t.get("from_table"):
                src = self.tables[t["from_table"]]
                bases = [r for r in src if not t.get("where") or eval(t["where"], self.env(dict(r)))]
            plan = [(s_, None, None) for s_ in seeds]
            for b in bases:
                if t.get("explode"):  # expr returning a list -> one row per element (available as `item`)
                    plan += [({}, b, it) for it in eval(t["explode"], self.env(dict(b)))]
                else:
                    plan.append(({}, b, None))
            rows = []
            for i, (seed, base, item) in enumerate(plan):
                row = dict(seed)
                if base is not None:
                    row["_base"] = base
                    row["_item"] = item
                for c in specs:
                    if c["name"] in seed:
                        continue
                    try:
                        row[c["name"]] = self.gen_value(c, row, i)
                    except Exception as e:
                        raise ValueError(f"{name}.{c['name']} (row {i}): {e}") from e
                rows.append({k: row.get(k) for k in cols})
            if t.get("sort_by"):
                rows.sort(key=lambda r: (r.get(t["sort_by"]) is None, r.get(t["sort_by"])))
        self.tables[name] = rows
        self.columns[name] = cols
        return rows

    def run(self, spec):
        for t in spec.get("tables", []):
            rows = self.build_table(t)
            print(f"  table {t['name']}: {len(rows)} rows")
        # optional post-processing: SQL statements run after load (e.g. derived updates)
        return self.tables


def _sql_type(vals):
    vals = [v for v in vals if v is not None]
    if vals and all(isinstance(v, bool) for v in vals):
        return "INTEGER"
    if vals and all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
        return "INTEGER"
    if vals and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return "REAL"
    return "TEXT"


def write_outputs(gen, spec, db_path, csv_dir, xlsx_path, brand):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    meta = []
    for t in spec.get("tables", []):
        name, rows, cols = t["name"], gen.tables[t["name"]], gen.columns[t["name"]]
        types = {c: _sql_type([r.get(c) for r in rows]) for c in cols}
        conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        conn.execute(f'CREATE TABLE "{name}" (' + ", ".join(f'"{c}" {types[c]}' for c in cols) + ")")
        conn.executemany(f'INSERT INTO "{name}" VALUES (' + ",".join("?" * len(cols)) + ")",
                         [[(int(r.get(c)) if isinstance(r.get(c), bool) else r.get(c)) for c in cols] for r in rows])
        meta.append({"name": name, "title": t.get("title", name.replace("_", " ").title()),
                     "description": t.get("description", ""), "system": t.get("system", ""),
                     "owner_department": t.get("department", ""), "columns": cols, "types": types,
                     "row_count": len(rows), "sharepoint_list": t.get("sharepoint_list", False),
                     "list_title": t.get("list_title", t.get("title", name.replace("_", " ").title())),
                     "site": t.get("department", ""), "list_rows": t.get("list_rows", 300)})
    for sql in spec.get("post_sql", []):
        conn.execute(sql)
    for m in meta:  # post_sql may insert/delete rows
        m["row_count"] = conn.execute(f'SELECT COUNT(*) FROM "{m["name"]}"').fetchone()[0]
    for dt in spec.get("derived", []):
        dn = dt["name"]
        conn.execute(f'DROP TABLE IF EXISTS "{dn}"')
        conn.execute(f'CREATE TABLE "{dn}" AS {dt["sql"]}')
        cur = conn.execute(f'SELECT * FROM "{dn}"')
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        types = {c: _sql_type([r[i] for r in rows]) for i, c in enumerate(cols)}
        meta.append({"name": dt["name"], "title": dt.get("title", dt["name"].replace("_", " ").title()),
                     "description": dt.get("description", ""), "system": dt.get("system", ""),
                     "owner_department": dt.get("department", ""), "columns": cols, "types": types,
                     "row_count": len(rows), "sharepoint_list": dt.get("sharepoint_list", False),
                     "list_title": dt.get("list_title", dt.get("title", dt["name"])), "site": dt.get("department", ""),
                     "list_rows": dt.get("list_rows", 300)})
        print(f"  derived {dt['name']}: {len(rows)} rows")
    conn.commit()

    # CSV export from the db (post_sql may have changed values)
    csv_dir = Path(csv_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)
    for m in meta:
        cur = conn.execute(f'SELECT * FROM "{m["name"]}"')
        with open(csv_dir / f"{m['name']}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            w.writerows(cur.fetchall())

    # one workbook with every table as an Excel Table
    from .xlsx_r import write_tables_workbook
    write_tables_workbook(conn, meta, xlsx_path, brand)
    return conn, meta
