"""Teams meetings: .ics calendar invites, .vtt transcripts, and Word blocks for transcripts / intelligent recaps."""
import hashlib
from datetime import datetime, timedelta, timezone

from . import common
from .common import parse_date, safe_filename

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/London
BEGIN:STANDARD
DTSTART:19701025T020000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZOFFSETFROM:+0100
TZOFFSETTO:+0000
TZNAME:GMT
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700329T010000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZOFFSETFROM:+0000
TZOFFSETTO:+0100
TZNAME:BST
END:DAYLIGHT
END:VTIMEZONE"""


def _addr(ctx, a):
    from .mail_r import _addr as a_
    return a_(ctx, a)


def start_end(item):
    st = parse_date(item["start"])
    if not isinstance(st, datetime):
        st = datetime.combine(st, datetime.min.time()).replace(hour=10)
    return st, st + timedelta(minutes=int(item.get("duration", 60)))


def folder_name(item, ctx):
    return safe_filename(f"{str(item['start'])[:10]} {ctx.fill(item['title'])}")


def join_url(item, ctx):
    h = hashlib.sha1(item["id"].encode()).hexdigest()
    return f"https://teams.{ctx.company.get('domain', 'example.co.uk')}/l/meetup-join/19%3ameeting_{h[:24]}%40thread.v2"


def _esc(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line):
    out, b = [], line.encode("utf-8")
    while len(b) > 74:
        cut = 74
        while (b[cut] & 0xC0) == 0x80:  # don't split a UTF-8 sequence
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b" " + b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n".join(out)


def is_teams(item):
    return "teams" in str(item.get("location", "Microsoft Teams Meeting")).lower() or item.get("online", False)


def render_ics(item, ctx, path):
    st, en = start_end(item)
    org = _addr(ctx, item["organiser"])
    desc = []
    if item.get("description"):
        desc.append(ctx.fill(item["description"]))
    if item.get("agenda"):
        desc.append("Agenda:\n" + "\n".join(f"{i}. {ctx.fill(a)}" for i, a in enumerate(item["agenda"], 1)))
    if is_teams(item):
        desc.append("Microsoft Teams meeting\nJoin on your computer, mobile app or room device\n" + join_url(item, ctx))
    desc.append(f"(Fictional training data - {ctx.company['fictional_name']})")
    fmt = "%Y%m%dT%H%M%S"
    stamp = parse_date(item.get("sent") or ctx.company["as_of"])
    stamp = datetime.combine(stamp, datetime.min.time()) if not isinstance(stamp, datetime) else stamp
    lines = ["BEGIN:VCALENDAR", f"PRODID:-//{ctx.company['fictional_name']}//Training Pack//EN", "VERSION:2.0",
             "METHOD:REQUEST", *VTIMEZONE.split("\n"), "BEGIN:VEVENT",
             f"UID:{item['id']}@{ctx.company.get('domain', 'example.co.uk')}",
             f"DTSTAMP:{stamp.replace(tzinfo=timezone.utc).strftime(fmt)}Z",
             f"DTSTART;TZID=Europe/London:{st.strftime(fmt)}", f"DTEND;TZID=Europe/London:{en.strftime(fmt)}"]
    if item.get("recurrence"):
        r = item["recurrence"].upper()
        day = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"][st.weekday()]
        rule = {"DAILY": "FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR", "WEEKLY": f"FREQ=WEEKLY;BYDAY={day}",
                "FORTNIGHTLY": f"FREQ=WEEKLY;INTERVAL=2;BYDAY={day}", "MONTHLY": "FREQ=MONTHLY"}.get(r, r)
        lines.append(f"RRULE:{rule}")
    lines += [f"SUMMARY:{_esc(ctx.fill(item['title']))}",
              f"LOCATION:{_esc(ctx.fill(item.get('location', 'Microsoft Teams Meeting')))}",
              f'ORGANIZER;CN="{org[0]}":mailto:{org[1]}']
    for a in item.get("attendees", []):
        n, e = _addr(ctx, a)
        lines.append(f'ATTENDEE;CN="{n}";ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{e}')
    for a in item.get("optional", []):
        n, e = _addr(ctx, a)
        lines.append(f'ATTENDEE;CN="{n}";ROLE=OPT-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{e}')
    lines += [f"DESCRIPTION:{_esc(chr(10).join(desc))}", f"CLASS:{'PRIVATE' if item.get('private') else 'PUBLIC'}",
              "TRANSP:OPAQUE", "X-MICROSOFT-CDO-BUSYSTATUS:BUSY"]
    if is_teams(item):
        lines.append(f"X-MICROSOFT-SKYPETEAMSMEETINGURL:{join_url(item, ctx)}")
    lines += ["BEGIN:VALARM", "TRIGGER:-PT15M", "ACTION:DISPLAY", "DESCRIPTION:Reminder", "END:VALARM",
              "END:VEVENT", "END:VCALENDAR"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\r\n".join(_fold(l) for l in lines) + "\r\n").encode("utf-8"))
    return path


def transcript_lines(item, ctx):
    """[(offset_seconds, speaker_name, text)] - uses explicit 't' (mm:ss / hh:mm:ss) or paces by speech length."""
    out, t = [], 4.0
    for m in item.get("transcript", []):
        if m.get("t"):
            parts = [float(x) for x in str(m["t"]).split(":")]
            t = sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
        text = ctx.fill(m["text"])
        out.append((t, ctx.person(m["from"]).get("name", "") if isinstance(m["from"], str) else m["from"].get("name", ""), text))
        t += max(3.0, len(text) / 14.0) + 1.5
    return out


def _ts(sec, vtt=True):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" + (f".{int((sec % 1) * 1000):03d}" if vtt else "")


def render_vtt(item, ctx, path):
    lines = ["WEBVTT", ""]
    tl = transcript_lines(item, ctx)
    for n, (t, who, text) in enumerate(tl):
        end = tl[n + 1][0] - 0.2 if n + 1 < len(tl) else t + max(3.0, len(text) / 14.0)
        lines += [f"{item['id']}-{n + 1}", f"{_ts(t)} --> {_ts(end)}", f"<v {who}>{text}</v>", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def header_kv(item, ctx):
    st, en = start_end(item)
    who = lambda a: _addr(ctx, a)[0] or _addr(ctx, a)[1]
    kv = [["Date", st.strftime("%A ") + common.long_date(st.date())], ["Time", f"{st:%H:%M} - {en:%H:%M} (UK time)"],
          ["Location", ctx.fill(item.get("location", "Microsoft Teams Meeting"))], ["Organiser", who(item["organiser"])],
          ["Attendees", "; ".join(who(a) for a in item.get("attendees", []))]]
    if item.get("optional"):
        kv.append(["Optional", "; ".join(who(a) for a in item["optional"])])
    if item.get("recurrence"):
        kv.append(["Recurrence", item["recurrence"].title()])
    return kv


def transcript_blocks(item, ctx):
    tl = transcript_lines(item, ctx)
    blocks = [{"kv": header_kv(item, ctx) + [["Transcript", f"{len(tl)} entries · auto-generated by Microsoft Teams"]]}]
    rows = [[_ts(t, False), who, text] for t, who, text in tl]
    blocks.append({"table": {"columns": ["Time", "Speaker", "Text"], "rows": rows}})
    return blocks


def recap_blocks(item, ctx):
    rc = item.get("recap", {})
    blocks = [{"kv": header_kv(item, ctx)}]
    if rc.get("summary"):
        blocks += [{"h2": "Meeting summary"}, {"p": rc["summary"]}]
    if rc.get("topics"):
        blocks.append({"h2": "Topics discussed"})
        for tp in rc["topics"]:
            blocks += [{"h3": tp["title"] + (f"  ({tp['t']})" if tp.get("t") else "")}, {"p": tp.get("text", "")}]
    if rc.get("decisions"):
        blocks += [{"h2": "Decisions"}, {"bullets": rc["decisions"]}]
    if rc.get("actions"):
        blocks += [{"h2": "Follow-up tasks"}, {"actions": rc["actions"]}]
    if rc.get("mentions"):
        blocks += [{"h2": "Mentions"}, {"bullets": rc["mentions"]}]
    blocks.append({"callout": "Generated by Copilot in Teams from the meeting transcript. AI-generated content may be incorrect - "
                              "check against the transcript.", "title": "Intelligent recap"})
    return blocks
