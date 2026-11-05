"""Email threads -> .eml files; Teams chats -> JSON + HTML transcript."""
import html
import json
import mimetypes
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path

from .common import inline_html, parse_date, safe_filename, slugify, uk_date


def _addr(ctx, a):
    if isinstance(a, dict):
        return a.get("name", ""), a.get("email", "")
    if a in ctx.people:
        p = ctx.people[a]
        return p["name"], p["email"]
    if "<" in str(a):
        n, e = str(a).split("<", 1)
        return n.strip(), e.strip(">").strip()
    return "", str(a)


def _fmt(n, e):
    return f'"{n}" <{e}>' if n else e


def signature(ctx, pid):
    if not isinstance(pid, str) or pid not in ctx.people:
        return ""
    p = ctx.people[pid]
    return f"\n\n{p['name']}\n{p['title']}\n{ctx.company['fictional_name']}\n{p.get('phone', '')}".rstrip()


def render_email_thread(item, ctx, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    subject = ctx.fill(item["subject"])
    prev_id, refs, out = None, [], []
    for i, m in enumerate(item.get("messages", []), 1):
        m = ctx.fill_deep(m)
        msg = EmailMessage()
        fn, fe = _addr(ctx, m["from"])
        msg["From"] = _fmt(fn, fe)
        msg["To"] = ", ".join(_fmt(*_addr(ctx, a)) for a in m.get("to", []))
        if m.get("cc"):
            msg["Cc"] = ", ".join(_fmt(*_addr(ctx, a)) for a in m["cc"])
        msg["Subject"] = subject if i == 1 else f"RE: {subject}"
        dt = parse_date(m["date"])
        msg["Date"] = format_datetime(dt.astimezone()) if dt else ""
        mid = make_msgid(domain=ctx.company.get("domain", "example.co.uk"))
        msg["Message-ID"] = mid
        if prev_id:
            msg["In-Reply-To"] = prev_id
            msg["References"] = " ".join(refs)
        if item.get("importance") == "high" and i == 1:
            msg["Importance"] = "High"
        body = m["body"].replace("**", "") + signature(ctx, m["from"])
        msg.set_content(body)
        for att in m.get("attachments", []):
            it = ctx.items.get(att)
            if it and it.get("out_path") and Path(it["out_path"]).exists():
                ap = Path(it["out_path"])
                mt, _ = mimetypes.guess_type(ap.name)
                maj, mn = (mt or "application/octet-stream").split("/")
                msg.add_attachment(ap.read_bytes(), maintype=maj, subtype=mn, filename=ap.name)
        p = folder / f"{i:02d} - {safe_filename(dt.strftime('%Y-%m-%d %H%M') if dt else '')} - {safe_filename(fn)}.eml"
        p.write_bytes(bytes(msg))
        out.append(str(p))
        prev_id = mid
        refs.append(mid)
    return out


def render_chat(item, ctx, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    name = safe_filename(ctx.fill(item["title"]))
    msgs = []
    for m in item.get("messages", []):
        m = ctx.fill_deep(m)
        p = ctx.person(m["from"])
        msgs.append({"from": p.get("name"), "from_email": p.get("email"), "time": m["time"], "text": m["text"],
                     "reactions": m.get("reactions", [])})
    data = {"channel": ctx.fill(item.get("channel", item["title"])), "team": item.get("team", ""), "messages": msgs}
    (folder / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = "".join(
        f"<div class='m'><b>{html.escape(m['from'] or '')}</b> <span>{uk_date(m['time'], True)}</span><p>{inline_html(m['text'])}</p></div>"
        for m in msgs)
    (folder / f"{name}.html").write_text(
        f"<!doctype html><meta charset='utf-8'><title>{html.escape(name)}</title>"
        f"<style>body{{font-family:Segoe UI,Arial;max-width:760px;margin:2rem auto;color:#222}}.m{{border-bottom:1px solid #eee;padding:.6rem 0}}span{{color:#777;font-size:.85em}}</style>"
        f"<h2>{html.escape(data['channel'])}</h2>{rows}", encoding="utf-8")
    return [str(folder / f"{name}.html"), str(folder / f"{name}.json")]


def thread_folder_name(item):
    first = item.get("messages", [{}])[0].get("date", "")
    return safe_filename(f"{str(first)[:10]} {item['subject']}")
