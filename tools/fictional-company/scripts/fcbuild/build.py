"""Orchestrates a full pack build from a workspace's spec/ folder."""
import html
import json
import os
import re
import shutil
import time
from pathlib import Path

from . import common
from .brand import build_brand
from .common import Context, fmt_value, load_json, parse_date, safe_filename, slugify, warn
from .datasets import Generator, write_outputs
from .docx_r import render_docx
from .image_r import image_ext, render_image, render_scan
from .mail_r import render_chat, render_email_thread, thread_folder_name
from . import meet_r
from .pdf_r import render_pdf
from .pnp import lib_url, list_columns, write_pnp
from .pptx_r import render_pptx
from .preview import preview
from .welcome import welcome_items
from .xlsx_r import render_xlsx

EXT = {"docx": ".docx", "pptx": ".pptx", "xlsx": ".xlsx", "pdf": ".pdf"}
RENDER = {"docx": render_docx, "pptx": render_pptx, "xlsx": render_xlsx, "pdf": render_pdf,
          "scan": render_scan, "image": render_image}
COMMS = ("email", "chat", "meeting")


def ext_for(it):
    return EXT.get(it["type"]) or image_ext(it)
TABLE_EMBED_ROWS = 1000


def md_to_html(md):
    out, in_list = [], False
    for line in md.splitlines():
        s = line.rstrip()
        if re.match(r"^\s*[-*] ", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_md_inline(re.sub(r'^\s*[-*] ', '', s))}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        m = re.match(r"^(#{1,4}) (.*)", s)
        if m:
            lvl = len(m.group(1)) + 1
            out.append(f"<h{lvl}>{_md_inline(m.group(2))}</h{lvl}>")
        elif s.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", s):
            cells = [c.strip() for c in s.strip("|").split("|")]
            out.append("<table class='pv-kv'><tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in cells) + "</tr></table>")
        elif s and not re.match(r"^\|[\s:|-]+\|$", s):
            out.append(f"<p>{_md_inline(s)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out).replace("</table>\n<table class='pv-kv'>", "")


def _md_inline(s):
    s = html.escape(s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def load_content(spec_dir):
    items = []
    cdir = spec_dir / "content"
    for p in sorted(cdir.glob("*.json")) if cdir.exists() else []:
        data = load_json(p)
        for it in data if isinstance(data, list) else data.get("items", []):
            it["_src"] = p.name
            items.append(it)
    return items


def validate(company, items, facts, scenarios, tables):
    ids = set()
    people = {p["id"] for p in company.get("people", [])}
    deps = {d["id"] for d in company.get("departments", [])}
    for p in company.get("people", []):
        if p.get("manager") and p["manager"] not in people:
            warn(f"person {p['id']} manager {p['manager']} not found")
        if p.get("department") not in deps:
            warn(f"person {p['id']} department {p.get('department')} not a department id")
    for it in items:
        if it.get("id") in ids:
            warn(f"duplicate content id {it['id']}")
        ids.add(it.get("id"))
        for k in ("author", "owner", "modified_by", "approved_by"):
            if it.get(k) and it[k] not in people:
                warn(f"{it.get('id')}: {k} '{it[k]}' not a person id")
        if it["type"] == "meeting":
            for a in [it.get("organiser")] + it.get("attendees", []):
                if isinstance(a, str) and a not in people:
                    warn(f"{it.get('id')}: attendee/organiser '{a}' not a person id")
            if it.get("site") and it["site"] not in deps:
                warn(f"{it.get('id')}: site '{it.get('site')}' not a department id")
        elif it["type"] not in ("email", "chat", "series") and it.get("site") not in deps:
            warn(f"{it.get('id')}: site '{it.get('site')}' not a department id")
    for it in items:  # documents the builder derives from meetings / comms / series can be cited too
        if it.get("_series"):
            ids.add(it["_series"])
        if it["type"] == "meeting":
            ids.update(f"{it['id']}-{k}" for k in ("recap", "transcript") if it.get(k))
        elif (it["type"] in ("email", "chat") and it.get("sharepoint_copy") is not False and company.get("comms_sharepoint_copy", True)
              and (it.get("sharepoint_copy") or not it.get("mailbox"))):
            ids.add(f"{it['id']}-sp")
    for f in facts:
        for s in f.get("sources", []):
            if s not in ids and s not in tables:
                warn(f"fact {f['id']}: source '{s}' not a content id or table")
    for s in scenarios:
        for d in s.get("data_sources", []):
            if d not in ids and d not in tables:
                warn(f"scenario {s['id']}: data source '{d}' not a content id or table")
        if s.get("persona") and s["persona"] not in people:
            warn(f"scenario {s['id']}: persona '{s['persona']}' not a person id")


def expand_series(items, ctx):
    out = []
    for it in items:
        if it["type"] != "series":
            out.append(it)
            continue
        try:
            cols, rows = ctx.query(ctx.fill(it["sql"]))
        except Exception as e:
            warn(f"series {it['id']}: sql failed: {e}")
            continue
        tpl = it["template"]
        for n, r in enumerate(rows, 1):
            row = dict(zip(cols, r))
            new = json.loads(json.dumps(tpl))
            new = ctx.fill_deep(new, row)
            new.setdefault("site", it.get("site"))
            new.setdefault("library", it.get("library"))
            new.setdefault("folder", ctx.fill(it.get("folder", ""), row))
            new["id"] = f"{it['id']}-{n:03d}"
            new["_series"] = it["id"]
            for k in ("author", "owner", "classification", "category", "tags", "doc_type_label"):
                if k in it and k not in new:
                    new[k] = ctx.fill_deep(it[k], row)
            if it.get("filename"):
                new["filename"] = ctx.fill(it["filename"], row)
            out.append(new)
        print(f"  series {it['id']}: {len(rows)} documents")
    return out


def chat_to_blocks(item, ctx):
    blocks = [{"kv": [["Team", item.get("team", "")], ["Channel", item.get("channel", item["title"])],
                      ["Messages", str(len(item["messages"]))]]}]
    rows = [[common.uk_date(m["time"], True), ctx.person(m["from"]).get("name", ""), m["text"]] for m in item["messages"]]
    blocks.append({"table": {"columns": ["Time", "From", "Message"], "rows": rows}})
    return blocks


def email_to_blocks(item, ctx):
    from .mail_r import _addr

    def who(a):
        n, e = _addr(ctx, a)[:2]
        return f"{n} <{e}>" if n and e else (n or e)

    blocks = [{"p": f"Archived copy of the email thread **{ctx.fill(item['subject'])}** "
                    f"({len(item['messages'])} messages). The original .eml files are in the Communications folder."}]
    for i, m in enumerate(item["messages"], 1):
        kv = [["From", who(m["from"])], ["To", "; ".join(who(a) for a in m.get("to", []))]]
        if m.get("cc"):
            kv.append(["Cc", "; ".join(who(a) for a in m["cc"])])
        kv.append(["Sent", common.uk_date(m["date"], True)])
        atts = [a.get("filename") or a.get("title") if isinstance(a, dict) else
                (ctx.items[a].get("filename") or ctx.items[a].get("title")) if a in ctx.items else a
                for a in m.get("attachments", [])]
        if atts:
            kv.append(["Attachments", ", ".join(str(x) for x in atts)])
        blocks += [{"h2": f"{i}. {'RE: ' if i > 1 else ''}{ctx.fill(item['subject'])}"}, {"kv": kv}]
        blocks += [{"p": para.replace("\n", " ")} for para in m["body"].split("\n\n") if para.strip()]
    return blocks


def _comms_site(item, ctx, site_by):
    """Department site of the first internal participant (sender, then recipients); hub as fallback."""
    m = (item.get("messages") or [{}])[0]
    for a in [m.get("from")] + list(m.get("to", [])):
        if isinstance(a, str) and a in ctx.people and ctx.people[a].get("department") in site_by:
            return ctx.people[a]["department"]
    return next((k for k, v in site_by.items() if v["hub"]), next(iter(site_by)))


def _render_meeting(it, ctx, root, site_by, items, used):
    """.ics invite in Communications/Calendar; transcript (.vtt + Word) and recap (Word) in the site's Meeting Records."""
    name = meet_r.folder_name(it, ctx)
    ics = meet_r.render_ics(it, ctx, root / "Communications" / "Calendar" / f"{name}.ics")
    it["out_path"], it["filename"], it["_files"] = str(ics), ics.name, [str(ics)]
    org = it["organiser"]
    site = it.get("site") or (ctx.people[org]["department"] if isinstance(org, str) and org in ctx.people else None)
    site = site if site in site_by else next((k for k, v in site_by.items() if v["hub"]), next(iter(site_by)))
    it["site"] = site
    if not (it.get("transcript") or it.get("recap")):
        return
    s = site_by[site]
    lib = it.get("library", "Meeting Records")
    if lib not in [l["title"] for l in s["libraries"]]:
        s["libraries"].append({"title": lib, "url": lib_url(lib), "description": "Teams meeting recaps and transcripts"})
    title = ctx.fill(it["title"])
    d = root / "SharePoint" / s["folder"] / lib / name
    d.mkdir(parents=True, exist_ok=True)
    it["_docs"] = []
    for kind in ("recap", "transcript"):
        if not it.get(kind):
            continue
        doc = {"id": f"{it['id']}-{kind}", "type": "docx", "site": site, "library": lib, "folder": name,
               "title": f"{title} - {'Meeting Recap' if kind == 'recap' else 'Transcript'}",
               "doc_type_label": "Teams meeting recap" if kind == "recap" else "Teams meeting transcript",
               "category": "Meeting record", "doc_control": False, "author": org if isinstance(org, str) else None,
               "classification": it.get("classification", "Internal"), "created": str(it["start"])[:10],
               "modified": str(it["start"])[:10], "tags": list(it.get("tags", [])) + ["meeting", kind],
               "summary": it.get("summary", ""), "meeting": it["id"],
               "blocks": meet_r.recap_blocks(it, ctx) if kind == "recap" else meet_r.transcript_blocks(it, ctx)}
        p = d / (safe_filename(doc["title"]) + ".docx")
        render_docx(doc, ctx, p)
        doc["out_path"], doc["filename"] = str(p), p.name
        used.add(str(p).lower())
        items.append(doc)
        ctx.items[doc["id"]] = doc
        it["_docs"].append(doc["id"])
    if it.get("transcript"):
        vtt = meet_r.render_vtt(it, ctx, root / "Communications" / "Meetings" / name / f"{name}.vtt")
        it["_files"].append(str(vtt))


def build(workspace, make_zip=True):
    t0 = time.time()
    ws = Path(workspace).resolve()
    spec = ws / "spec"
    company = load_json(spec / "company.json")
    company.update(load_json(spec / "private.json", {}))  # git-ignored extras, e.g. {"real_company": "..."}
    company.setdefault("slug", slugify(company["fictional_name"]))
    company.setdefault("as_of", time.strftime("%Y-%m-%d"))
    dspec = load_json(spec / "datasets.json", {"tables": []})
    facts = load_json(spec / "facts.json", []) + [f for p in sorted((spec / "facts").glob("*.json")) for f in load_json(p)]
    scenarios = load_json(spec / "scenarios.json", []) + [s for p in sorted((spec / "scenarios").glob("*.json")) for s in load_json(p)]
    items = load_content(spec)
    if company.get("welcome", True) is not False:
        items += welcome_items(company, scenarios)
    brief_md = (ws / "research" / "brief.md").read_text(encoding="utf-8") if (ws / "research" / "brief.md").exists() else ""

    pack_name = safe_filename(company.get("pack_name", f"{company['fictional_name']} Training Pack"))
    root = ws / "build" / pack_name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    print(f"Building {pack_name} -> {root}")

    print("Brand kit...")
    assets = build_brand(company, root / "Brand Kit")

    print("Datasets...")
    db_file = f"{company['slug']}.sqlite"
    xlsx_file = f"{company['fictional_name']} - All Data.xlsx"
    # cache: datasets only depend on datasets.json + company.json, so reuse them when unchanged
    import hashlib
    key = hashlib.sha1(((spec / "datasets.json").read_bytes() if (spec / "datasets.json").exists() else b"")
                       + (spec / "company.json").read_bytes() + Path(__file__).with_name("datasets.py").read_bytes()).hexdigest()[:12]
    cache = ws / ".cache" / key
    if (cache / "meta.json").exists():
        print("  (reusing cached datasets)")
        shutil.copytree(cache / "Databases", root / "Databases")
        tmeta = load_json(cache / "meta.json")
        import sqlite3
        conn = sqlite3.connect(root / "Databases" / db_file)
    else:
        gen = Generator(dspec, company)
        gen.run(dspec)
        conn, tmeta = write_outputs(gen, dspec, root / "Databases" / db_file, root / "Databases" / "csv",
                                    root / "Databases" / xlsx_file, company["brand"])
        if (ws / ".cache").exists():
            shutil.rmtree(ws / ".cache", ignore_errors=True)
        shutil.copytree(root / "Databases", cache / "Databases")
        (cache / "meta.json").write_text(json.dumps(tmeta), encoding="utf-8")
    tables = {m["name"]: m for m in tmeta}

    print("Facts...")
    fact_map = {}
    for f in facts:
        if "sql" in f:
            try:
                cur = conn.execute(f["sql"])
                rows = cur.fetchall()
                if f.get("format") == "list":
                    f["raw"] = [r[0] for r in rows]
                    f["answer"] = ", ".join(str(r[0]) for r in rows)
                else:
                    f["raw"] = rows[0][0] if rows else None
                    f["answer"] = fmt_value(f["raw"], f.get("format"))
            except Exception as e:
                warn(f"fact {f['id']} sql failed: {e}")
                f["answer"] = "(error)"
        else:
            f.setdefault("raw", f.get("answer"))
        fact_map[f["id"]] = f

    ctx = Context(company, conn, fact_map, root, {
        "logo_png": assets["logo_png"], "logo_white_png": assets["logo_white_png"]})
    for f in facts:  # facts can reference company placeholders
        if isinstance(f.get("answer"), str):
            f["answer"] = ctx.fill(f["answer"])
        f["question"] = ctx.fill(f["question"])

    items = expand_series(items, ctx)
    validate(company, items, facts, scenarios, tables)
    real = [n for n in [company.get("real_company"), *company.get("real_company_aliases", [])] if n]
    if real:  # whole words, plus the squashed form that turns up in domains (realname.co.uk)
        pat = re.compile("|".join([rf"\b{re.escape(n)}\b" for n in real] +
                                  [re.escape(re.sub(r"[^a-z0-9]", "", n.lower())) for n in real]), re.I)
        blob = json.dumps([items, facts, scenarios, _public(company)], ensure_ascii=False, default=str)
        for m in list(pat.finditer(blob))[:10]:
            warn(f"real company name appears in content: …{blob[max(0, m.start() - 40):m.end() + 40]}...")
        if brief_md and pat.search(brief_md):
            warn("research/brief.md names the real company, so it is not published. Keep source research in "
                 "research/private/ and write research/brief.md about the fictional twin")
            brief_md = ""

    # ---- sites ----
    sites = []
    for d in company["departments"]:
        sites.append({"key": d["id"], "title": d.get("site_title", d["name"]), "alias": d.get("site_alias", slugify(d["name"], "")),
                      "description": d.get("description", ""), "head": d.get("head"), "hub": d.get("hub", False),
                      "folder": safe_filename(d.get("site_title", d["name"])),
                      "libraries": [{"title": l["name"], "url": lib_url(l["name"]), "description": l.get("description", "")}
                                    for l in d.get("libraries", [])]})
    site_by = {s["key"]: s for s in sites}

    # Word copies of every email thread / Teams chat in SharePoint so Copilot can search them (.eml isn't indexed)
    if company.get("comms_sharepoint_copy", True):
        for it in items:
            if it["type"] in ("email", "chat") and "sharepoint_copy" not in it and not it.get("mailbox"):
                it["sharepoint_copy"] = {"site": _comms_site(it, ctx, site_by), "library": "Communications Archive",
                                         "folder": "Email" if it["type"] == "email" else
                                         "Teams/" + safe_filename(it.get("channel") or it.get("title", "General"))}

    print(f"Rendering {len(items)} items...")
    used = set()
    for it in items:
        ctx.items[it["id"]] = it
    order = [i for i in items if i["type"] in RENDER] + [i for i in items if i["type"] in COMMS]
    for it in order:
        t = it["type"]
        try:
            if t in RENDER:
                s = site_by.get(it.get("site"))
                if not s:
                    warn(f"{it['id']}: unknown site; skipped")
                    continue
                lib = it.get("library") or (s["libraries"][0]["title"] if s["libraries"] else "Documents")
                if lib not in [l["title"] for l in s["libraries"]]:
                    s["libraries"].append({"title": lib, "url": lib_url(lib), "description": ""})
                it["library"] = lib
                folder = (it.get("folder") or "").strip("/")
                it["folder"] = folder
                fname = safe_filename(it.get("filename") or ctx.fill(it["title"]))
                ext = ext_for(it)
                if not fname.lower().endswith(ext):
                    fname += ext
                d = root / "SharePoint" / s["folder"] / lib / folder
                d.mkdir(parents=True, exist_ok=True)
                p = d / fname
                k = 2
                while str(p).lower() in used:
                    p = d / f"{Path(fname).stem} ({k}){ext}"
                    k += 1
                used.add(str(p).lower())
                RENDER[t](it, ctx, p)
                it["out_path"], it["filename"] = str(p), p.name
            elif t == "email":
                folder = (root / "Communications" / "Shared Mailboxes" / safe_filename(mailbox_name(company, it["mailbox"]))
                          if it.get("mailbox") else root / "Communications" / "Email") / thread_folder_name(it)
                files = render_email_thread(it, ctx, folder)
                it["out_path"], it["filename"] = str(folder), Path(folder).name
                it["_files"] = files
            elif t == "chat":
                folder = root / "Communications" / "Teams" / safe_filename(it.get("team", "General"))
                files = render_chat(it, ctx, folder)
                it["out_path"], it["filename"] = files[0], Path(files[0]).name
            elif t == "meeting":
                _render_meeting(it, ctx, root, site_by, items, used)
            mt = parse_date(it.get("modified") or it.get("created") or it.get("start") or (it.get("messages") or [{}])[-1].get("date")
                            or (it.get("messages") or [{}])[-1].get("time") or company["as_of"])
            if mt:
                ts = time.mktime(mt.timetuple())
                for f in it.get("_files", [it["out_path"]]):
                    os.utime(f, (ts, ts))
            # optional SharePoint copy of comms so Copilot can ground on them via SharePoint
            sc = it.get("sharepoint_copy")
            if sc and t in ("email", "chat"):
                s = site_by[sc["site"]]
                lib = sc.get("library", "Correspondence")
                if lib not in [l["title"] for l in s["libraries"]]:
                    desc = "Searchable Word copies of email threads and Teams chats" if lib == "Communications Archive" else ""
                    s["libraries"].append({"title": lib, "url": lib_url(lib), "description": desc})
                first = it["messages"][0]
                stamp = str(first.get("date") or first.get("time") or "")[:10]
                ctitle = ctx.fill(it.get("subject") or it.get("title"))
                copy = {"id": it["id"] + "-sp", "type": "docx", "title": ctitle,
                        "filename": safe_filename(f"{stamp} {ctitle}".strip()), "doc_control": False,
                        "tags": list(it.get("tags", [])) + ["email" if t == "email" else "teams"],
                        "site": sc["site"], "library": lib, "folder": sc.get("folder", ""),
                        "category": "Email record" if t == "email" else "Teams export",
                        "author": it["messages"][0]["from"] if isinstance(it["messages"][0]["from"], str) and it["messages"][0]["from"] in ctx.people else None,
                        "classification": it.get("classification", "Internal"), "modified": str(mt.date()) if mt else None,
                        "blocks": email_to_blocks(it, ctx) if t == "email" else chat_to_blocks(it, ctx),
                        "summary": it.get("summary", "")}
                d = root / "SharePoint" / s["folder"] / lib / copy["folder"]
                d.mkdir(parents=True, exist_ok=True)
                p = d / (copy["filename"] + ".docx")
                render_docx(copy, ctx, p)
                copy["out_path"], copy["filename"] = str(p), p.name
                items.append(copy)
                ctx.items[copy["id"]] = copy
        except Exception as e:
            warn(f"render failed for {it.get('id')} ({t}): {type(e).__name__}: {e}")

    for wid in ("welcome-deck", "welcome-onepager"):
        if ctx.items.get(wid, {}).get("out_path"):
            (root / "Learner Pack").mkdir(exist_ok=True)
            shutil.copy2(ctx.items[wid]["out_path"], root / "Learner Pack" / ctx.items[wid]["filename"])

    # ---- learning + trainer materials ----
    print("Trainer & learner packs...")
    _trainer_materials(root, ctx, facts, scenarios, brief_md, tables)
    _triage_key(root, ctx, items)

    # ---- PnP ----
    print("M365 provisioning script...")
    for s in sites:
        s["libraries"] = [l for l in s["libraries"]]
    lists = []
    for m in tmeta:
        if m["sharepoint_list"]:
            site_key = m["site"] if m["site"] in site_by else next((s["key"] for s in sites if s["hub"]), sites[0]["key"])
            lists.append({"site_alias": site_by[site_key]["alias"], "title": m["list_title"], "url": "Lists/" + lib_url(m["list_title"]),
                          "csv": f"{m['name']}.csv", "columns": list_columns(m)})
    prefix = company.get("site_prefix", re.sub(r"[^A-Z]", "", company["fictional_name"].upper())[:4] or "FC")
    write_pnp(sites, lists, root / "M365 Provisioning", company, prefix)

    # ---- dashboard ----
    print("Dashboard...")
    _dashboard(root, ctx, items, sites, tmeta, conn, facts, scenarios, brief_md, assets, db_file, xlsx_file)
    _readme(root, company, items, sites, tmeta, facts, scenarios)

    conn.close()
    counts = {}
    for it in items:
        if it.get("out_path"):
            counts[it["type"]] = counts.get(it["type"], 0) + 1
    nfiles = sum(1 for _ in root.rglob("*") if _.is_file())
    report = [f"Pack: {pack_name}", f"Files on disk: {nfiles}", f"Content items: {counts}",
              f"Tables: {[(m['name'], m['row_count']) for m in tmeta]}", f"Facts: {len(facts)}  Scenarios: {len(scenarios)}",
              f"Warnings ({len(common.WARNINGS)}):"] + [f"  - {w}" for w in common.WARNINGS]
    (ws / "build" / "build_report.txt").write_text("\n".join(report), encoding="utf-8")
    zip_path = None
    if make_zip:
        print("Zipping...")
        zip_path = shutil.make_archive(str(ws / pack_name.replace(" ", "_")), "zip", root.parent, pack_name)
    print("\n".join(report))
    print(f"Done in {time.time() - t0:.1f}s" + (f" -> {zip_path}" if zip_path else ""))
    return root, zip_path


def _public(company):
    """company.json minus the private fields that must never be rendered."""
    return {k: v for k, v in company.items() if k not in ("real_company", "real_company_aliases")}


def mailbox_name(company, address):
    mb = next((m for m in company.get("mailboxes", []) if m.get("address") == address), None)
    return mb.get("name", address) if mb else address


def _triage_key(root, ctx, items):
    """Ground truth for inbox-triage exercises: one row per shared-mailbox email that has a 'triage' block."""
    from .mail_r import _addr
    rows = []
    for it in sorted((i for i in items if i["type"] == "email" and i.get("mailbox") and i.get("triage")),
                     key=lambda i: (i["mailbox"], str(i["messages"][0]["date"]))):
        m, tr = it["messages"][0], it["triage"]
        fn, fe = _addr(ctx, m["from"])
        route = tr.get("route_to", "")
        route = ctx.person_label(route) if route in ctx.people else ctx.departments.get(route, {}).get("name", route)
        rows.append([it["id"], mailbox_name(ctx.company, it["mailbox"]), common.uk_date(m["date"], True), f"{fn} <{fe}>",
                     ctx.fill(it["subject"]), tr.get("category", ""), tr.get("priority", ""), route,
                     tr.get("action", ""), tr.get("sla", ""), "; ".join(tr.get("flags", [])), tr.get("notes", "")])
    if rows:
        render_xlsx({"id": "triagekey", "title": "Inbox Triage Key", "sheets": [{
            "name": "Triage Key", "columns": ["ID", "Mailbox", "Received", "From", "Subject", "Category", "Priority",
                                             "Route to", "Expected action", "Respond within", "Flags", "Notes"],
            "rows": rows}]}, ctx, root / "Trainer Pack" / "Inbox Triage Key.xlsx")


def _trainer_materials(root, ctx, facts, scenarios, brief_md, tables):
    tdir, ldir = root / "Trainer Pack", root / "Learner Pack"
    tdir.mkdir(exist_ok=True)
    ldir.mkdir(exist_ok=True)

    def src_label(s):
        it = ctx.items.get(s)
        if it:
            return it.get("filename") or it.get("title")
        return f"[table] {tables[s]['title']}" if s in tables else s

    render_xlsx({"id": "answerkey", "title": "Answer Key", "sheets": [{
        "name": "Answer Key", "columns": ["ID", "Category", "Question", "Answer", "Sources", "Notes"],
        "rows": [[f["id"], f.get("category", ""), f["question"], str(f.get("answer", "")),
                  "; ".join(src_label(s) for s in f.get("sources", [])), f.get("notes", "")] for f in facts]}]},
        ctx, tdir / "Answer Key.xlsx")

    blocks = []
    for s in scenarios:
        blocks += [{"h1": f"{s['id']}: {s['title']}"},
                   {"kv": [["Level", s.get("level", "")], ["Module", s.get("module", "")],
                           ["Persona", ctx.person_label(s["persona"]) if s.get("persona") else "—"]]},
                   {"p": s.get("context", "")}, {"p": f"**Goal:** {s.get('goal', '')}"}]
        if s.get("task_steps"):
            blocks += [{"h3": "Steps"}, {"numbered": s["task_steps"]}]
        if s.get("sample_prompts"):
            blocks += [{"h3": "Example prompts"}, {"bullets": s["sample_prompts"]}]
        if s.get("success_criteria"):
            blocks += [{"h3": "Success criteria"}, {"bullets": s["success_criteria"]}]
        if s.get("data_sources"):
            blocks += [{"h3": "Data sources"}, {"bullets": [src_label(d) for d in s["data_sources"]]}]
        blocks.append({"pagebreak": True})
    card = {"title": f"{ctx.company['fictional_name']} — Scenario Cards", "category": "Learner Guide",
            "classification": "Public", "doc_control": False, "blocks": blocks}
    render_docx(card, ctx, ldir / "Scenario Cards.docx")

    tblocks = []
    for s in scenarios:
        tblocks += [{"h1": f"{s['id']}: {s['title']}"}, {"p": s.get("goal", "")}]
        if s.get("agent_instructions"):
            tblocks += [{"h3": "Reference agent instructions"}, {"callout": s["agent_instructions"]}]
        if s.get("trainer_notes"):
            tblocks += [{"h3": "Trainer notes"}, {"p": s["trainer_notes"]}]
        fl = [fact_by for fact_by in facts if fact_by["id"] in s.get("fact_ids", [])]
        if fl:
            tblocks += [{"h3": "Expected answers"},
                        {"table": {"columns": ["Question", "Answer"], "rows": [[f["question"], str(f["answer"])] for f in fl]}}]
    render_docx({"title": "Trainer Guide — Scenarios & Expected Answers", "category": "Trainer Guide",
                 "classification": "Confidential", "doc_control": False, "blocks": tblocks}, ctx, tdir / "Trainer Guide.docx")

    pb = [{"p": "Fictional personas for role-play and agent testing. Use these names in prompts so Copilot can find their documents."}]
    for p in ctx.company.get("people", []):
        pb += [{"h2": f"{p['name']} — {p['title']}"},
               {"kv": [["Department", ctx.departments.get(p.get("department"), {}).get("name", "")], ["Email", p.get("email", "")],
                       ["Reports to", ctx.person_label(p.get("manager")) if p.get("manager") else "—"],
                       ["Location", p.get("location", "")]]}]
        if p.get("bio"):
            pb.append({"p": p["bio"]})
        if p.get("persona_notes"):
            pb.append({"callout": p["persona_notes"], "title": "Persona notes"})
    render_docx({"title": "Personas & Org Chart", "category": "Trainer Guide", "classification": "Internal",
                 "doc_control": False, "blocks": pb}, ctx, tdir / "Personas.docx")
    if brief_md:
        (tdir / "Research Brief.md").write_text(brief_md, encoding="utf-8")
    public = _public(ctx.company)
    (tdir / "company.json").write_text(json.dumps(public, indent=2, ensure_ascii=False), encoding="utf-8")


def _dashboard(root, ctx, items, sites, tmeta, conn, facts, scenarios, brief_md, assets, db_file, xlsx_file):
    tpl = (Path(__file__).parent / "dashboard_template.html").read_text(encoding="utf-8")
    out_items = []
    lib_counts = {}
    for it in items:
        if not it.get("out_path"):
            continue
        try:
            pv = preview(it, ctx)
        except Exception as e:
            warn(f"preview failed for {it['id']}: {e}")
            pv = ""
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", pv))[:5000]
        fr = it.get("author") or (it.get("messages") or [{}])[0].get("from")
        a = ctx.people.get(fr, {}) if isinstance(fr, str) else {"name": fr.get("name", "")} if isinstance(fr, dict) else {}
        mb = ctx.people.get(it.get("modified_by") or it.get("author"), {})
        rel_path = Path(it["out_path"]).relative_to(root).as_posix()
        if it["type"] == "email":
            rel_path = Path(it["_files"][0]).relative_to(root).as_posix()
        last_msg = (it.get("messages") or [{}])[-1]
        mod = (it.get("modified") or last_msg.get("date") or last_msg.get("time") or it.get("start") or it.get("created")
               or ctx.company["as_of"])
        ext = Path(it["out_path"]).suffix.lower().lstrip(".")
        icon = {"jpg": "image", "jpeg": "image", "png": "image", "ics": "meeting"}.get(ext, ext if ext in ("docx", "pptx", "xlsx", "pdf") else it["type"])
        extra = {}
        if it["type"] == "meeting":
            st, en = meet_r.start_end(it)
            org = meet_r._addr(ctx, it["organiser"])
            extra = {"start": st.isoformat(timespec="minutes"), "end": en.isoformat(timespec="minutes"),
                     "location": ctx.fill(it.get("location", "Microsoft Teams Meeting")), "organiser": org[0] or org[1],
                     "attendee_count": len(it.get("attendees", [])), "recurrence": it.get("recurrence", ""),
                     "docs": it.get("_docs", []), "has_transcript": bool(it.get("transcript"))}
            a = ctx.people.get(it["organiser"], {}) if isinstance(it["organiser"], str) else {"name": org[0]}
        if it.get("_previews"):
            extra["images"] = it["_previews"]
        out_items.append(extra | {"icon": icon,
            "id": it["id"], "type": it["type"], "title": ctx.fill(it.get("title") or it.get("subject", "")),
            "filename": it["filename"], "path": rel_path, "site": it.get("site", ""), "library": it.get("library", ""),
            "folder": it.get("folder", ""), "author": a.get("name", ""), "author_id": a.get("id", ""),
            "modified_by": mb.get("name", a.get("name", "")), "modified_by_id": mb.get("id", ""),
            "created": it.get("created", mod), "modified": mod, "version": it.get("version", ""),
            "status": it.get("status", ""), "classification": it.get("classification", "Internal"),
            "category": it.get("category", ""), "tags": it.get("tags", []), "summary": ctx.fill(it.get("summary", "")),
            "review_date": it.get("review_date", ""), "preview": pv, "text": text,
            "mailbox": mailbox_name(ctx.company, it["mailbox"]) if it.get("mailbox") else "",
            "snippet": re.sub(r"\s+", " ", ctx.fill(it["messages"][0]["body"]).replace("**", ""))[:140] if it["type"] == "email" else ""})
        key = (it.get("site"), it.get("library"))
        lib_counts[key] = lib_counts.get(key, 0) + 1
    dsites = []
    for s in sites:
        libs = [{"title": l["title"], "description": l.get("description", ""), "count": lib_counts.get((s["key"], l["title"]), 0)}
                for l in s["libraries"]]
        dsites.append({"key": s["key"], "title": s["title"], "description": s["description"], "head": s["head"], "hub": s["hub"],
                       "libraries": libs, "lists": [m["name"] for m in tmeta if m["site"] == s["key"]]})
    dtables = []
    for m in tmeta:
        cur = conn.execute(f'SELECT * FROM "{m["name"]}" LIMIT {TABLE_EMBED_ROWS}')
        dtables.append({k: m[k] for k in ("name", "title", "description", "system", "columns", "row_count", "sharepoint_list")}
                       | {"site": m["site"], "rows": [list(r) for r in cur.fetchall()]})
    b = ctx.brand
    data = {
        "company": ctx.fill_deep({k: v for k, v in _public(ctx.company).items() if k not in ("people", "brand")}),
        "brand": {**{k: b.get(k) for k in ("primary", "secondary", "accent", "dark", "light", "font_heading", "font_body")},
                  "logo_svg": assets["logo_svg"], "logo_white_svg": assets["logo_white_svg"],
                  "emblem_svg": assets["logo_emblem_svg"], "emblem_white_svg": assets["logo_white_emblem_svg"]},
        "sites": dsites, "items": out_items, "tables": dtables,
        "people": [{k: p.get(k) for k in ("id", "name", "title", "department", "manager", "email", "phone", "location", "bio", "persona_notes")}
                   for p in ctx.company.get("people", [])],
        "facts": [{k: f.get(k) for k in ("id", "category", "question", "answer", "sources", "notes")} | {"answer": str(f.get("answer", ""))} for f in facts],
        "scenarios": scenarios, "research_html": md_to_html(brief_md) if brief_md else "",
        "db_file": db_file, "xlsx_file": xlsx_file, "zip_file": root.name.replace(" ", "_") + ".zip"}
    blob = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    import urllib.parse
    fav = "data:image/svg+xml," + urllib.parse.quote(assets["logo_emblem_svg"])
    page = (tpl.replace("__DATA__", blob).replace("__TITLE__", html.escape(ctx.company["fictional_name"] + " Intranet"))
            .replace("__FAVICON__", fav))
    for k in ("primary", "secondary", "accent", "dark", "light"):
        page = page.replace(f"__{k.upper()}__", b[k])
    (root / "index.html").write_text(page, encoding="utf-8")


def _readme(root, company, items, sites, tmeta, facts, scenarios):
    n = {}
    for it in items:
        if it.get("out_path"):
            n[it["type"]] = n.get(it["type"], 0) + 1
    txt = f"""# {company['fictional_name']} — Training Data Pack

> **Everything in this pack is fictional.** {company['fictional_name']} is an invented organisation created for AI / Copilot
> training. People, figures, clients and records are made up.

**Open `index.html`** in a browser to explore the intranet: sites, document libraries, lists, people, mail/Teams and the Learning Hub.

## Contents

| Folder | What's inside |
|---|---|
| `index.html` | Offline intranet-style dashboard to browse everything |
| `SharePoint/` | One folder per site → document libraries → folders, as real .docx / .pptx / .xlsx / .pdf files |
| `Databases/` | `{company['slug']}.sqlite`, one CSV per table, and an Excel workbook with every table |
| `Communications/` | Email threads (.eml), Teams channel transcripts (.html/.json), calendar invites (`Calendar/*.ics`) and meeting transcripts (`Meetings/*.vtt`) |
| `Dashboard Assets/` | Preview images the dashboard uses for scans and photos |
| `M365 Provisioning/` | PnP PowerShell script + README to create the SharePoint sites, libraries and lists in a tenant |
| `Learner Pack/` | Scenario cards for learners |
| `Trainer Pack/` | Answer key, trainer guide, personas, research brief, world model (company.json) |
| `Brand Kit/` | Fictional logo (PNG/SVG), palette |

## At a glance
* Sites: {', '.join(s['title'] for s in sites)}
* Documents: {n.get('docx', 0)} Word · {n.get('pptx', 0)} PowerPoint · {n.get('xlsx', 0)} Excel · {n.get('pdf', 0)} PDF
* Scans & images: {n.get('scan', 0)} scanned documents (image-only, no text layer) · {n.get('image', 0)} images
* Communications: {n.get('email', 0)} email threads · {n.get('chat', 0)} Teams channels · {n.get('meeting', 0)} meetings
* Data tables: {', '.join(f"{m['title']} ({m['row_count']})" for m in tmeta)}
* Scenarios: {len(scenarios)} · Answer-key facts: {len(facts)}
"""
    (root / "README.md").write_text(txt, encoding="utf-8")
