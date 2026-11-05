#!/usr/bin/env python3
"""Fast validation of content/facts/scenario specs against an already-built database (no rendering).

Usage:
    python check_content.py <workspace> --schema            # print tables, columns and sample values
    python check_content.py <workspace> [content files...]  # validate (defaults to all spec/content/*.json)

Requires one prior build (python build_pack.py <workspace> --no-zip) so the SQLite DB exists.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fcbuild import common  # noqa: E402
from fcbuild.build import expand_series, load_content, validate  # noqa: E402
from fcbuild.common import Context, fmt_value, load_json  # noqa: E402
from fcbuild.preview import preview  # noqa: E402


def find_db(ws):
    dbs = list((ws / "build").glob("*/Databases/*.sqlite"))
    if not dbs:
        sys.exit("No built database found - run build_pack.py <workspace> --no-zip first")
    return dbs[0]


def main():
    ws = Path(sys.argv[1]).resolve()
    conn = sqlite3.connect(find_db(ws))
    if "--schema" in sys.argv:
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            cur = conn.execute(f'SELECT * FROM "{t}" LIMIT 1')
            cols = [c[0] for c in cur.description]
            row = cur.fetchone() or []
            print(f"\n## {t} ({n} rows)")
            for c, v in zip(cols, row):
                distinct = conn.execute(f'SELECT COUNT(DISTINCT "{c}") FROM "{t}"').fetchone()[0]
                extra = ""
                if distinct <= 12:
                    vals = [r[0] for r in conn.execute(f'SELECT DISTINCT "{c}" FROM "{t}" LIMIT 12')]
                    extra = f"  values: {vals}"
                print(f"  - {c}  e.g. {v!r}{extra}")
        return
    spec = ws / "spec"
    company = load_json(spec / "company.json")
    company.setdefault("as_of", "2026-01-01")
    facts = load_json(spec / "facts.json", []) + [f for p in sorted((spec / "facts").glob("*.json")) for f in load_json(p)]
    scenarios = load_json(spec / "scenarios.json", []) + [s for p in sorted((spec / "scenarios").glob("*.json")) for s in load_json(p)]
    fm = {}
    for f in facts:
        if "sql" in f:
            try:
                r = conn.execute(f["sql"]).fetchall()
                f["raw"] = r[0][0] if r else None
                f["answer"] = fmt_value(f["raw"], f.get("format"))
            except Exception as e:
                common.warn(f"fact {f['id']} sql failed: {e}")
                f["answer"] = "(error)"
        fm[f["id"]] = f
    ctx = Context(company, conn, fm, ws / "build", {"logo_png": "", "logo_white_png": ""})
    files = [Path(a) for a in sys.argv[2:] if not a.startswith("--")]
    if files:
        items = []
        for p in files:
            if p.resolve().parent.name in ("facts", "scenarios") or p.name in ("facts.json", "scenarios.json"):
                continue  # facts and scenarios are always loaded and checked; nothing item-level to do
            for it in load_json(p):
                it["_src"] = p.name
                items.append(it)
    else:
        items = load_content(spec)
    all_items = load_content(spec)
    items = expand_series(items, ctx)
    for it in expand_series(all_items, ctx):
        ctx.items[it["id"]] = it
    validate(company, items if files else list(ctx.items.values()), facts, scenarios,
             {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
    deps = {d["id"]: {l["name"] for l in d.get("libraries", [])} for d in company["departments"]}
    for it in items:
        if it["type"] in ("docx", "pdf", "pptx", "xlsx", "scan", "image") and it.get("library") and it["library"] not in deps.get(it.get("site"), set()):
            common.warn(f"{it['id']}: library '{it['library']}' not defined on site '{it.get('site')}' (will be auto-created)")
        try:
            if it["type"] in ("scan", "image"):  # raster content is cheap enough to render for real
                import tempfile
                from fcbuild.image_r import image_ext, render_image, render_scan
                with tempfile.TemporaryDirectory() as td:
                    ctx.out_root = Path(td)
                    (render_scan if it["type"] == "scan" else render_image)(it, ctx, Path(td) / ("x" + image_ext(it)))
            if it["type"] == "meeting":
                from fcbuild import meet_r
                meet_r.start_end(it), meet_r.recap_blocks(it, ctx), meet_r.transcript_blocks(it, ctx)
            preview(it, ctx)
        except Exception as e:
            common.warn(f"{it['id']}: {type(e).__name__}: {e}")
    print(f"\nChecked {len(items)} items, {len(facts)} facts, {len(scenarios)} scenarios: "
          f"{len(common.WARNINGS)} warning(s)")
    for f in facts:
        if f.get("answer") in ("(error)", None, ""):
            print(f"  fact {f['id']} has no answer")
    sys.exit(1 if common.WARNINGS else 0)


if __name__ == "__main__":
    main()
