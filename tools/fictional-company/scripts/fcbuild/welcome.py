"""Auto-generated orientation content: a 'Welcome to <Company>' deck and an '<Company> at a Glance' one-pager.

Built from company.json (+ facts via placeholders), so every pack gets them without extra spec work."""


def _first_sentence(s, limit=150):
    s = (s or "").strip()
    cut = s.find(". ")
    s = s[:cut + 1] if 0 < cut < limit else s
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def welcome_items(company, scenarios):
    name = company["fictional_name"]
    people = {p["id"]: p for p in company.get("people", [])}
    deps = company.get("departments", [])
    hub = next((d for d in deps if d.get("hub")), deps[0])
    ceo = next((p for p in company.get("people", []) if not p.get("manager")), None)
    execs = [p for p in company.get("people", []) if ceo and p.get("manager") == ceo["id"]]
    w = company.get("welcome", {}) if isinstance(company.get("welcome"), dict) else {}
    base = {"site": hub["id"], "library": w.get("library", "New Starters"), "folder": w.get("folder", ""),
            "author": w.get("author") or (ceo or {}).get("id"), "classification": "Internal", "category": "Induction",
            "tags": ["induction", "welcome", "new starter"], "created": company.get("as_of"), "version": "1.0"}

    head = lambda d: f"{people[d['head']]['name']}, {people[d['head']]['title']}" if d.get("head") in people else ""
    org_rows = [[d.get("site_title", d["name"]), _first_sentence(d.get("description", ""), 90), head(d)]
                for d in deps if not d.get("hub")]
    profile = [[k, v] for k, v in [("Legal name", company.get("legal_name")), ("Sector", company.get("sector")),
                                   ("Founded", company.get("founded")), ("Headquarters", ", ".join(
                                       v for v in (company.get("hq") or {}).values() if v)),
                                   ("People", company.get("headcount")), ("Revenue", company.get("revenue_label")),
                                   ("Part of", company.get("parent_company")), ("Year end", company.get("financial_year_end")),
                                   ("Website", company.get("domain"))] if v]
    personas = []
    for pid in dict.fromkeys(s.get("persona") for s in scenarios if s.get("persona") in people):
        p = people[pid]
        personas.append([p["name"], p["title"], _first_sentence(p.get("bio", ""), 110)])

    slides = [
        {"layout": "title", "title": f"Welcome to {name}", "subtitle": company.get("tagline", ""),
         "notes": "Orientation deck for new starters and course learners. Fictional training data."},
        {"layout": "bullets", "title": "Who we are", "subtitle": _first_sentence(company.get("description", ""), 200),
         "bullets": [f"{k}: {v}" for k, v in profile[:7]]},
    ]
    if company.get("kpis"):
        slides.append({"layout": "kpis", "title": f"{name} in numbers",
                       "kpis": [{"label": k["label"], "value": k["value"], "note": k.get("note", "")} for k in company["kpis"][:6]]})
    slides.append({"layout": "table", "title": "How we're organised",
                   "subtitle": "Each team has its own SharePoint site on the intranet",
                   "table": {"columns": ["Team", "What they do", "Head"], "rows": org_rows[:12]}})
    if ceo:
        slides.append({"layout": "table", "title": "Our leadership team",
                       "table": {"columns": ["Name", "Role"], "rows": [[ceo["name"], ceo["title"]]] +
                                 [[p["name"], p["title"]] for p in execs][:11]}})
    if company.get("timeline"):
        slides.append({"layout": "steps", "title": "Our story",
                       "steps": [{"label": str(t["date"]), "text": t["event"]} for t in company["timeline"][-5:]]})
    if company.get("values"):
        slides.append({"layout": "bullets", "title": "What we value", "bullets": company["values"]})
    if company.get("offices") or company.get("systems"):
        slides.append({"layout": "two_column", "title": "Where we work and the tools we use",
                       "left": {"heading": "Offices", "bullets": [f"{o['name']}" for o in company.get("offices", [])][:7]},
                       "right": {"heading": "Systems", "bullets": [f"{s['name']} - {s.get('purpose', '')}".strip(" -")
                                                                    for s in company.get("systems", [])][:7]}})
    if company.get("glossary"):
        slides.append({"layout": "table", "title": "Words you'll hear",
                       "table": {"columns": ["Term", "Meaning"],
                                 "rows": [[g["term"], _first_sentence(g["definition"], 110)] for g in company["glossary"][:10]]}})
    slides += [
        {"layout": "section", "title": "Your training environment", "subtitle": f"Everything about {name} is fictional"},
        {"layout": "steps", "title": "How to use this environment", "steps": [
            {"label": "Explore", "text": "Browse the intranet: team sites, libraries, lists, mail, Teams and calendar."},
            {"label": "Pick a persona", "text": "Each scenario tells you who you are and what your job is."},
            {"label": "Ground Copilot", "text": "Point Copilot or an agent at the sites and files the scenario names."},
            {"label": "Do the task", "text": "Summarise, draft, analyse or automate, as your persona would."},
            {"label": "Check", "text": "Compare your answer with the data and the success criteria."}]},
    ]
    if personas:
        slides.append({"layout": "table", "title": "People you'll play",
                       "table": {"columns": ["Name", "Role", "About them"], "rows": personas[:10]}})
    slides += [
        {"layout": "bullets", "title": "Ground rules", "bullets": [
            f"{name}, its people, clients and figures are invented for training.",
            "Never paste real customer, learner or employee data into the exercises.",
            "Treat documents marked Confidential as you would at work - notice when Copilot surfaces them.",
            "Always check AI output against the source documents and data."]},
        {"layout": "title", "title": f"Welcome aboard", "subtitle": f"{name} · {company.get('domain', '')}"},
    ]
    deck = dict(base, id="welcome-deck", type="pptx", title=f"Welcome to {name}",
                summary=f"Induction deck: who {name} is, how it's organised, leadership, values and how to use this training environment.",
                slides=slides)

    # kept to one page: key numbers and profile share a table, values go on one line
    kpis = [[k["label"], k["value"]] for k in company.get("kpis", [])[:4]]
    blocks = [{"p": company.get("description", "")},
              {"h2": "At a glance"}, {"kv": kpis + [r for r in profile if r[0] not in ("Website", "Year end")]},
              {"h2": "Our teams"}, {"table": {"columns": ["Team", "Head"], "rows": [[r[0], r[2]] for r in org_rows]}}]
    if company.get("values"):
        blocks.append({"p": "**Our values:** " + " · ".join(company["values"])})
    if company.get("systems"):
        blocks.append({"p": "**Key systems:** " + " · ".join(s["name"] for s in company["systems"][:10])})
    pager = dict(base, id="welcome-onepager", type="pdf", title=f"{name} at a Glance", doc_control=False,
                 doc_type_label="Fact sheet", subtitle=company.get("tagline", ""),
                 summary=f"One-page fact sheet about {name}: profile, key numbers, teams, values and systems.", blocks=blocks)
    return [deck, pager]
