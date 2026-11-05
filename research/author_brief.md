# Brief for content authors: Silvering Homes

You are writing JSON content specs for **Silvering Homes**. It is a fictional UK housing association modelled on a real one, built for a Microsoft 365 Copilot training course. A deterministic builder renders your JSON into real Word, Excel, PowerPoint and PDF files, emails, Teams chats, meetings, scans and images.

## Read first (in this order)
1. `C:\Users\ashle\.claude\skills\fictional-company\references\spec-format.md`: the contract. Every field you use must be in it.
2. `C:\Users\ashle\fictional-companies\silvering\spec\company.json`: the world model. Use its people (P001-P040), departments, systems, schemes, glossary and mailboxes.
3. `C:\Users\ashle\fictional-companies\silvering\research\schema.txt`: the database tables and columns your SQL can query.
4. `C:\Users\ashle\fictional-companies\silvering\research\fact_values.txt`: current values of the core facts (ids are in `spec/facts/core.json`).
5. `C:\Users\ashle\fictional-companies\silvering\research\brief.md`: research on the real landlord. Use it for realism only. **Never name the real organisation, its people, its schemes or its suppliers.**
6. For tone and depth, look at 2-3 files in `C:\Users\ashle\.claude\skills\fictional-company\references\example-spec\content\`. That is a worked example for a different company.

## World facts to keep consistent
- **Date and scale.** "Today" is **5 November 2026**. Data runs from November 2024. The financial year ends 31 March. TSM years are 2025/26 (complete) and 2026/27 (in progress).
- **Homes and schemes.** 1,840 homes across 29 schemes, mostly in Maidstone, plus a few in Tonbridge & Malling, Medway, Ashford, Swale and Tunbridge Wells.
  - **Brenchley Gardens** (SCH03, a 1964 estate of 164 homes) is the problem estate: damp and mould, a repairs backlog, complaints and low satisfaction.
  - **Rosemount Tower** (SCH01, 12 storeys, 88 flats) is the only higher-risk building. Fire door actions are overdue.
  - **Orchard Fields** phase 1 (62 homes, handed over October 2026) is the new-build scheme. 18 homes are awaiting let and there are many defects. The main contractor is Castlemere Construction.
- **The regulator and Awaab's Law.**
  - The RSH inspection in March 2026 gave **C2 / G1 / V2**. Damp and mould and complaint handling are the areas to improve.
  - Awaab's Law applies from 27 October 2025:
    - emergency hazards must be made safe within 24 hours;
    - significant damp and mould must be investigated within 10 working days;
    - a written summary must reach the resident within 3 working days of the investigation;
    - safety works must start within 5 working days.
- **Repairs story.** Routine repairs in target fell sharply from May 2026. The causes:
  - two electrician vacancies and one plasterer vacancy;
  - more use of the subcontractor Brightline Electrical;
  - summer leave.

  See `monthly_repairs`.
- **Complaints.** Stage 1 response times slipped from June to September 2026. Satisfaction with complaint handling (TP09) is low.
- **Arrears.** Arrears are rising slowly as Universal Credit migration completes. Most arrears are owed by UC households.
- **Rents.** Rents rose 4.8% in April 2026 (CPI + 1%).
- **AI pilot.** The Copilot pilot is sponsored by P005 Simone Achterberg, with IT led by P014 Craig Whitmore. The main worry is oversharing of vulnerability data.
- **External organisations** must be fictional; reuse the names in the `suppliers` table. You may name the real regulators and public bodies: Regulator of Social Housing, Housing Ombudsman, Building Safety Regulator, Homes England, DWP, HSE, ICO. Refer to councils generically ("the borough council", "the county council") and to "the police".
- **External people** (residents, councillors, contractors) need fictional names, with emails on fictional domains such as `example.com`, `castlemere-construction.co.uk` or `brightline-electrical.co.uk`. For residents, prefer real tenants from the `tenancies` table (use `lead_tenant` and `address_line1`).

## Rules
- **Numbers that exist in the data** must come from `{{fact:id}}`, `{{sql:...}}`, a `sql` table or a `sql` chart. Never type them by hand.
  - You can use the core facts.
  - You can add your own facts in your facts file. Prefer `sql` facts, and keep queries simple and correct for SQLite.
  - Board papers that describe a past snapshot (for example, the September 2026 board pack) may quote fixed historical figures. They must be plausible against the monthly tables.
- **Content must be substantive and realistic:** real policy clauses, real decisions, real analysis, UK spelling, UK social-housing terminology. No lorem ipsum.
  - Vary authors, dates (2024-11 to 2026-11-05), versions, statuses and classifications.
  - Plant a few realistic imperfections for exercises: a draft that disagrees with the final, an outdated version, a missed action. Say what you planted in a fact or in scenario `trainer_notes`.
- **Ids must use your prefix**, for example `rep-`. Scenario ids look like `S-REP-01`.
- **Every `site`/`library`** must exist in company.json for that department. Use `folder` for structure.
- **Mixed-case booleans in SQL:** booleans are stored as 0/1.
- **Validate as you go:** `PYTHONUTF8=1 python C:/Users/ashle/.claude/skills/fictional-company/scripts/check_content.py C:/Users/ashle/fictional-companies/silvering <your file>`. Run it on each content, facts and scenarios file. Fix everything it reports, including unknown ids, bad placeholders and SQL errors.
- **Do NOT run `build_pack.py`.** Others are working in parallel and it replaces the build they validate against.
- Only write your own files, listed in your task. Don't edit company.json, datasets.json or other authors' files. If you need data that doesn't exist, work with what is there and mention it in your final report.

## Final report
Keep it under 200 words. Cover:
- the files you wrote, with item counts by type;
- the facts you added;
- the scenarios;
- any planted inconsistencies;
- any problems.
