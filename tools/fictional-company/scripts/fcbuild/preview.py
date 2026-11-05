"""Build HTML previews (for the dashboard) straight from content specs, so no client-side Office parsing."""
import html

from .common import inline_html as ih, uk_date

E = html.escape
MAX_ROWS = 150


def _table(cols, rows, limit=MAX_ROWS):
    head = "".join(f"<th>{E(str(c))}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{ih('' if v is None else v)}</td>" for v in r) + "</tr>" for r in rows[:limit])
    more = f"<p class='pv-more'>Showing {limit} of {len(rows)} rows.</p>" if len(rows) > limit else ""
    return f"<div class='pv-tablewrap'><table class='pv-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>{more}"


def blocks_html(blocks, ctx):
    out = []
    for b in blocks:
        b = ctx.fill_deep(b)
        if "h1" in b:
            out.append(f"<h2>{ih(b['h1'])}</h2>")
        elif "h2" in b:
            out.append(f"<h3>{ih(b['h2'])}</h3>")
        elif "h3" in b:
            out.append(f"<h4>{ih(b['h3'])}</h4>")
        elif "p" in b:
            out.append(f"<p>{ih(b['p'])}</p>")
        elif "bullets" in b:
            out.append("<ul>" + "".join(f"<li class='{'l2' if str(x).startswith('  ') else ''}'>{ih(str(x).strip())}</li>" for x in b["bullets"]) + "</ul>")
        elif "numbered" in b:
            out.append("<ol>" + "".join(f"<li>{ih(x)}</li>" for x in b["numbered"]) + "</ol>")
        elif "table" in b:
            cols, rows = ctx.resolve_table(b["table"])
            cap = f"<div class='pv-cap'>{ih(b['table']['caption'])}</div>" if b["table"].get("caption") else ""
            out.append(cap + _table(cols, rows))
        elif "kv" in b:
            out.append("<table class='pv-kv'>" + "".join(f"<tr><th>{ih(k)}</th><td>{ih(v)}</td></tr>" for k, v in b["kv"]) + "</table>")
        elif "callout" in b:
            t = f"<strong>{ih(b['title'])}</strong><br>" if b.get("title") else ""
            out.append(f"<div class='pv-callout'>{t}{ih(b['callout'])}</div>")
        elif "quote" in b:
            out.append(f"<blockquote>“{ih(b['quote'])}”{('<cite>— ' + ih(b['by']) + '</cite>') if b.get('by') else ''}</blockquote>")
        elif "signature" in b:
            out.append(f"<p class='pv-sig'>Signed: <strong>{E(ctx.person_label(b['signature']))}</strong></p>")
        elif "actions" in b:
            rows = [[str(i), a.get("action", ""), ctx.people.get(a.get("owner"), {}).get("name", a.get("owner", "")),
                     uk_date(a["due"]) if a.get("due") else "", a.get("status", "Open")] for i, a in enumerate(b["actions"], 1)]
            out.append(_table(["#", "Action", "Owner", "Due", "Status"], rows))
    return "".join(out)


def doc_preview(item, ctx):
    label = ctx.fill(item.get("doc_type_label", item.get("category", "")))
    sub = f"<p class='pv-sub'>{ih(ctx.fill(item['subtitle']))}</p>" if item.get("subtitle") else ""
    meta = ""
    if item.get("owner") or item.get("version"):
        meta = (f"<div class='pv-meta'>Owner: {E(ctx.person_label(item.get('owner') or item.get('author')))} · "
                f"v{E(str(item.get('version', '1.0')))} · {E(item.get('status', 'Approved'))}"
                f"{' · Next review ' + uk_date(item['review_date']) if item.get('review_date') else ''}</div>")
    return (f"<article class='pv-doc'><div class='pv-label'>{E(label.upper())}</div><h1>{ih(ctx.fill(item['title']))}</h1>"
            f"{sub}{meta}{blocks_html(item.get('blocks', []), ctx)}</article>")


def deck_preview(item, ctx):
    slides = []
    for n, s in enumerate(item.get("slides", []), 1):
        s = ctx.fill_deep(s)
        lay = s.get("layout", "bullets")
        body = ""
        if lay in ("title", "section"):
            body = f"<div class='sl-big'>{ih(s.get('title', ''))}</div><div class='sl-subbig'>{ih(s.get('subtitle', ''))}</div>"
        else:
            body = f"<div class='sl-title'>{ih(s.get('title', ''))}</div>"
            if s.get("subtitle"):
                body += f"<div class='sl-sub'>{ih(s['subtitle'])}</div>"
            if s.get("bullets") and lay != "chart":
                body += "<ul>" + "".join(f"<li class='{'l2' if str(x).startswith('  ') else ''}'>{ih(str(x).strip())}</li>" for x in s["bullets"]) + "</ul>"
            if lay == "two_column":
                cols = []
                for k in ("left", "right"):
                    c = s.get(k, {})
                    c = {"bullets": c} if isinstance(c, list) else c
                    h = f"<h5>{ih(c['heading'])}</h5>" if c.get("heading") else ""
                    inner = _chart_html(c["chart"], ctx) if c.get("chart") else "<ul>" + "".join(f"<li>{ih(str(x).strip())}</li>" for x in c.get("bullets", [])) + "</ul>"
                    cols.append(f"<div>{h}{inner}</div>")
                body += f"<div class='sl-2col'>{''.join(cols)}</div>"
            if lay == "table":
                cols, rows = ctx.resolve_table(s["table"])
                body += _table(cols, rows, 14)
            if lay == "chart":
                body += f"<div class='sl-chartrow'>{_chart_html(s['chart'], ctx)}" + (
                    "<ul>" + "".join(f"<li>{ih(x)}</li>" for x in s.get("bullets", [])) + "</ul>" if s.get("bullets") else "") + "</div>"
            if lay == "kpis":
                body += "<div class='sl-kpis'>" + "".join(
                    f"<div><b>{E(str(k.get('value', '')))}</b><span>{E(k.get('label', ''))}</span><small>{E(k.get('note', ''))}</small></div>"
                    for k in s.get("kpis", [])) + "</div>"
            if lay == "steps":
                body += "<div class='sl-steps'>" + "".join(
                    f"<div><b>{E(st.get('label', ''))}</b><p>{ih(st.get('text', ''))}</p></div>" for st in s.get("steps", [])) + "</div>"
            if lay == "quote":
                body += f"<blockquote>“{ih(s.get('quote', ''))}”<cite>{E(s.get('by', ''))}</cite></blockquote>"
        notes = f"<details class='sl-notes'><summary>Speaker notes</summary>{ih(s['notes'])}</details>" if s.get("notes") else ""
        slides.append(f"<div class='slide lay-{lay}'><div class='sl-inner'>{body}</div><span class='sl-n'>{n}</span></div>{notes}")
    return f"<div class='pv-deck'>{''.join(slides)}</div>"


def _chart_html(ch, ctx):
    """Simple horizontal bar rendering of the first series (preview only)."""
    try:
        cats, series = ctx.resolve_chart(ch)
    except Exception:
        return ""
    if not series:
        return ""
    name, vals = series[0]
    mx = max([abs(v) for v in vals] + [1])
    rows = "".join(f"<div class='bar'><span>{E(str(c))}</span><i style='width:{abs(v) / mx * 100:.0f}%'></i><em>{v:,.0f}</em></div>"
                   for c, v in zip(cats[:12], vals[:12]))
    t = ch.get("title") or name
    return f"<div class='sl-chart'><div class='sl-ct'>{E(t)}</div>{rows}</div>"


def book_preview(item, ctx):
    tabs, panes = [], []
    for i, sh in enumerate(item.get("sheets", [])):
        sh = ctx.fill_deep(sh)
        tabs.append(f"<button class='xl-tab{' on' if i == 0 else ''}' data-i='{i}'>{E(sh.get('name', 'Sheet'))}</button>")
        if sh.get("text"):
            inner = "".join(f"<p>{ih(t)}</p>" for t in sh["text"])
        else:
            if "sql" in sh:
                cols, rows = ctx.query(sh["sql"])
                cols = sh.get("columns", cols)
            else:
                cols, rows = sh.get("columns", []), sh.get("rows", [])
            from .common import fmt_value
            fm = sh.get("format", {})
            rows = [[("(formula)" if isinstance(v, str) and v.startswith("=") else fmt_value(v, fm.get(c))) for c, v in zip(cols, r)] for r in rows]
            inner = _table(cols, rows)
        panes.append(f"<div class='xl-pane' data-i='{i}' {'hidden' if i else ''}>{inner}</div>")
    return f"<div class='pv-book'><div class='xl-tabs'>{''.join(tabs)}</div>{''.join(panes)}</div>"


def email_preview(item, ctx):
    from .mail_r import _addr
    out = [f"<div class='pv-mail'><h1>{ih(ctx.fill(item['subject']))}</h1>"]
    for m in item.get("messages", []):
        m = ctx.fill_deep(m)
        fn, fe = _addr(ctx, m["from"])
        to = ", ".join((_addr(ctx, a)[0] or _addr(ctx, a)[1]) for a in m.get("to", []))
        cc = ", ".join((_addr(ctx, a)[0] or _addr(ctx, a)[1]) for a in m.get("cc", []))
        atts = "".join(f"<span class='att'>📎 {E(ctx.items[a].get('filename') or ctx.fill(ctx.items[a].get('title', a)))}</span>" for a in m.get("attachments", []) if a in ctx.items)
        body = "".join(f"<p>{ih(par)}</p>" for par in m["body"].split("\n\n"))
        initials = "".join(w[0] for w in (fn or fe).split()[:2]).upper()
        out.append(f"<div class='msg'><div class='av'>{E(initials)}</div><div class='mb'><div class='mh'><b>{E(fn or fe)}</b>"
                   f"<span>{uk_date(m['date'], True)}</span></div><div class='mto'>To: {E(to)}{(' · Cc: ' + E(cc)) if cc else ''}</div>"
                   f"{body.replace(chr(10), '<br>')}{('<div class=atts>' + atts + '</div>') if atts else ''}</div></div>")
    return "".join(out) + "</div>"


def chat_preview(item, ctx):
    out = [f"<div class='pv-chat'><h1># {ih(ctx.fill(item.get('channel', item['title'])))}</h1>"]
    for m in item.get("messages", []):
        m = ctx.fill_deep(m)
        p = ctx.person(m["from"])
        initials = "".join(w[0] for w in p.get("name", "?").split()[:2]).upper()
        rx = "".join(f"<span class='rx'>{E(r)}</span>" for r in m.get("reactions", []))
        out.append(f"<div class='msg'><div class='av'>{E(initials)}</div><div class='mb'><div class='mh'><b>{E(p.get('name', ''))}</b>"
                   f"<span>{uk_date(m['time'], True)}</span></div><p>{ih(m['text']).replace(chr(10), '<br>')}</p>{rx}</div></div>")
    return "".join(out) + "</div>"


def image_preview(item, ctx):
    imgs = "".join(f"<img src='{E(p)}' alt='{E(ctx.fill(item['title']))} page {n}' loading='lazy'>"
                   for n, p in enumerate(item.get("_previews", []), 1))
    note = ("<p class='pv-more'>Scanned copy - this file is an image with no text layer, so search and Copilot can't read "
            "it until it has been OCR'd.</p>") if item["type"] == "scan" else ""
    return f"<div class='pv-img'>{note}{imgs}</div>"


def meeting_preview(item, ctx):
    from . import meet_r
    st, en = meet_r.start_end(item)
    rows = "".join(f"<tr><th>{E(k)}</th><td>{E(v)}</td></tr>" for k, v in meet_r.header_kv(item, ctx))
    out = [f"<div class='pv-mail pv-meet'><div class='pv-label'>{'TEAMS MEETING' if meet_r.is_teams(item) else 'MEETING'}</div>"
           f"<h1>{ih(ctx.fill(item['title']))}</h1><table class='pv-kv'>{rows}</table>"]
    if meet_r.is_teams(item):
        out.append(f"<p><span class='att'>🎥 Join Microsoft Teams meeting</span> <small class='pv-more'>{E(meet_r.join_url(item, ctx))}</small></p>")
    if item.get("description"):
        out.append(f"<p>{ih(ctx.fill(item['description']))}</p>")
    if item.get("agenda"):
        out.append("<h3>Agenda</h3><ol>" + "".join(f"<li>{ih(ctx.fill(a))}</li>" for a in item["agenda"]) + "</ol>")
    docs = [d for d in item.get("_docs", []) if d in ctx.items]
    if docs:
        out.append("<p>" + "".join(f"<a class='att' href=\"javascript:openFile('{E(d)}')\">📄 {E(ctx.items[d]['filename'])}</a>" for d in docs) + "</p>")
    rc = item.get("recap")
    if rc:
        out.append("<h3>✨ Intelligent recap</h3>")
        if rc.get("summary"):
            out.append(f"<p>{ih(ctx.fill(rc['summary']))}</p>")
        for tp in rc.get("topics", []):
            out.append(f"<p><b>{ih(ctx.fill(tp['title']))}</b>{(' <small class=pv-more>' + E(tp['t']) + '</small>') if tp.get('t') else ''}<br>{ih(ctx.fill(tp.get('text', '')))}</p>")
        if rc.get("decisions"):
            out.append("<h4>Decisions</h4><ul>" + "".join(f"<li>{ih(ctx.fill(x))}</li>" for x in rc["decisions"]) + "</ul>")
        if rc.get("actions"):
            out.append("<h4>Follow-up tasks</h4>" + blocks_html([{"actions": rc["actions"]}], ctx))
    if item.get("transcript"):
        tl = meet_r.transcript_lines(item, ctx)
        lines = "".join(f"<div class='msg'><div class='av'>{E(''.join(w[0] for w in who.split()[:2]).upper())}</div><div class='mb'>"
                        f"<div class='mh'><b>{E(who)}</b><span>{meet_r._ts(t, False)}</span></div><p>{ih(text)}</p></div></div>"
                        for t, who, text in tl)
        out.append(f"<details><summary><b>Transcript ({len(tl)} entries)</b></summary>{lines}</details>")
    return "".join(out) + "</div>"


def preview(item, ctx):
    t = item["type"]
    if t in ("scan", "image"):
        return image_preview(item, ctx)
    if t == "meeting":
        return meeting_preview(item, ctx)
    if t in ("docx", "pdf"):
        return doc_preview(item, ctx)
    if t == "pptx":
        return deck_preview(item, ctx)
    if t == "xlsx":
        return book_preview(item, ctx)
    if t == "email":
        return email_preview(item, ctx)
    if t == "chat":
        return chat_preview(item, ctx)
    return ""


def plain_text(item, ctx, limit=4000):
    """Searchable text for the dashboard index."""
    import re
    h = preview(item, ctx)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))[:limit]
