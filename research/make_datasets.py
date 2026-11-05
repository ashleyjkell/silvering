import json

OUT = __import__("pathlib").Path(__file__).resolve().parents[1] / "spec" / "datasets.json"
AS_OF = "2026-11-05"
# add n working days (Mon-Fri, bank holidays ignored) to a datetime s
WD = "(lambda s, n: s + timedelta(days=(n//5)*7 + n%5 + (2 if s.weekday() + n%5 >= 5 else 0)))"
ISO = ".date().isoformat()"
PC_LET = "'ABDEFGHJLNPQRSTUWXYZ'"


def col(name, gen, **kw):
    return {"name": name, "gen": gen, **kw}


def ex(name, expr, **kw):
    return {"name": name, "gen": "expr", "expr": expr, **kw}


# ---------------------------------------------------------------- schemes
SCHEMES = [
    # id, name, area, town, sector, type, build, storeys, lift, homes, hrb, patch officer
    ("SCH01", "Rosemount Tower", "Maidstone", "Maidstone", "ME16 8", "General needs block", 1968, 12, True, 88, True, "Tom Reed"),
    ("SCH02", "Parkwood Court", "Maidstone", "Maidstone", "ME15 9", "General needs block", 1972, 5, True, 60, False, "Amira Haddad"),
    ("SCH03", "Brenchley Gardens", "Maidstone", "Maidstone", "ME15 8", "General needs estate", 1964, 3, False, 164, False, "Amira Haddad"),
    ("SCH04", "Heron Way", "Maidstone", "Maidstone", "ME15 7", "General needs estate", 1978, 2, False, 100, False, "Amira Haddad"),
    ("SCH05", "Vinters Rise", "Maidstone", "Maidstone", "ME14 5", "General needs estate", 1985, 2, False, 96, False, "Sasha Kemp"),
    ("SCH06", "Shepway Green", "Maidstone", "Maidstone", "ME15 8", "General needs estate", 1958, 2, False, 150, False, "Amira Haddad"),
    ("SCH07", "Coxheath Lane", "Maidstone", "Coxheath", "ME17 4", "General needs estate", 1952, 2, False, 54, False, "Sasha Kemp"),
    ("SCH08", "Allington Mews", "Maidstone", "Maidstone", "ME16 0", "General needs block", 2011, 3, False, 36, False, "Tom Reed"),
    ("SCH09", "Ringlestone Crescent", "Maidstone", "Maidstone", "ME14 2", "General needs estate", 1961, 2, False, 92, False, "Tom Reed"),
    ("SCH10", "Bearsted Court", "Maidstone", "Bearsted", "ME14 4", "Sheltered (SilverLiving)", 1979, 3, True, 48, False, "Margaret Ogunleye"),
    ("SCH11", "Willow House", "Maidstone", "Maidstone", "ME16 9", "Sheltered (SilverLiving)", 1986, 3, True, 42, False, "Margaret Ogunleye"),
    ("SCH12", "Linton Lodge", "Maidstone", "Loose", "ME15 0", "Extra care (SilverLiving)", 2014, 3, True, 60, False, "Margaret Ogunleye"),
    ("SCH13", "Oakwood Place", "Maidstone", "Maidstone", "ME16 8", "Supported housing", 1998, 2, False, 18, False, "Tom Reed"),
    ("SCH14", "Orchard Fields", "Maidstone", "Maidstone", "ME15 9", "New build mixed tenure", 2026, 4, True, 62, False, "Amira Haddad"),
    ("SCH15", "Hop Pocket Way", "Maidstone", "Maidstone", "ME15 6", "New build mixed tenure", 2019, 3, False, 84, False, "Sasha Kemp"),
    ("SCH16", "Lenham Meadows", "Maidstone", "Lenham", "ME17 2", "New build mixed tenure", 2022, 2, False, 70, False, "Sasha Kemp"),
    ("SCH17", "Headcorn & Villages", "Maidstone", "Headcorn", "TN27 9", "Street properties", 1950, 2, False, 62, False, "Sasha Kemp"),
    ("SCH18", "Larkfield Close", "Tonbridge & Malling", "Larkfield", "ME20 6", "General needs estate", 1970, 2, False, 48, False, "Joel Mensah"),
    ("SCH19", "Kings Hill Quarter", "Tonbridge & Malling", "Kings Hill", "ME19 4", "New build mixed tenure", 2017, 3, False, 58, False, "Joel Mensah"),
    ("SCH20", "Snodland Riverside", "Tonbridge & Malling", "Snodland", "ME6 5", "General needs block", 2009, 4, True, 30, False, "Joel Mensah"),
    ("SCH21", "Chatham Hill Court", "Medway", "Chatham", "ME5 7", "General needs block", 1974, 4, False, 40, False, "Joel Mensah"),
    ("SCH22", "Strood Wharf", "Medway", "Strood", "ME2 4", "New build mixed tenure", 2021, 5, True, 46, False, "Joel Mensah"),
    ("SCH23", "Kennington Grange", "Ashford", "Ashford", "TN24 9", "New build mixed tenure", 2018, 3, False, 52, False, "Joel Mensah"),
    ("SCH24", "Mill Court", "Swale", "Sittingbourne", "ME10 3", "General needs block", 2006, 3, False, 28, False, "Joel Mensah"),
    ("SCH25", "Station Road", "Tunbridge Wells", "Paddock Wood", "TN12 6", "New build mixed tenure", 2023, 3, False, 48, False, "Sasha Kemp"),
    ("SCH26", "Marden & Staplehurst Cottages", "Maidstone", "Marden", "TN12 9", "Street properties", 1948, 2, False, 34, False, "Sasha Kemp"),
    ("SCH27", "Maidstone Town Street Properties", "Maidstone", "Maidstone", "ME14 1", "Street properties", 1930, 2, False, 90, False, "Tom Reed"),
    ("SCH28", "Week Street Apartments", "Maidstone", "Maidstone", "ME14 1", "Market rent", 2020, 5, True, 40, False, "Tom Reed"),
    ("SCH29", "Leybourne Court", "Tonbridge & Malling", "Leybourne", "ME19 5", "Sheltered (SilverLiving)", 1982, 2, True, 40, False, "Margaret Ogunleye"),
]
assert sum(s[9] for s in SCHEMES) == 1840, sum(s[9] for s in SCHEMES)
schemes = {
    "name": "schemes", "title": "Schemes & Estates", "department": "assets", "system": "Keystone Housing",
    "description": "Every scheme, estate and block Silvering owns or manages, with type, age, storeys, lifts and the patch housing officer.",
    "sharepoint_list": True, "list_title": "Schemes",
    "columns": ["scheme_id", "scheme_name", "local_authority", "town", "postcode_sector", "scheme_type", "build_year",
                "max_storeys", "has_lift", "homes", "higher_risk_building", "patch_officer"],
    "data": [list(s) for s in SCHEMES],
}

# ---------------------------------------------------------------- properties
BLOCKY = "scheme_type in ('General needs block', 'Sheltered (SilverLiving)', 'Extra care (SilverLiving)', 'Supported housing', 'Market rent')"
properties = {
    "name": "properties", "title": "Property Register", "department": "assets", "system": "Keystone Housing",
    "description": "All 1,840 homes: address, scheme, tenure, type, bedrooms, heating, EPC, Decent Homes status, current rent and service charge.",
    "from_table": "schemes", "explode": "list(range(homes))",
    "columns": [
        col("uprn", "seq", prefix="1000224", start=40001, pad=5),
        col("property_ref", "seq", prefix="SVH", start=10001),
        col("scheme_id", "base"), col("scheme_name", "base"), col("scheme_type", "base"),
        col("local_authority", "base"), col("town", "base"), col("patch_officer", "base"),
        ex("property_type",
           f"('Bedsit' if rnd.random() < 0.08 else 'Flat') if scheme_type.startswith('Sheltered') else "
           f"'Flat' if {BLOCKY} else "
           "rnd.choices(['House', 'Flat', 'Maisonette', 'Bungalow'], [55, 28, 11, 6])[0] if scheme_type == 'General needs estate' else "
           "rnd.choices(['House', 'Bungalow', 'Flat'], [72, 16, 12])[0] if scheme_type == 'Street properties' else "
           "rnd.choices(['House', 'Flat'], [45, 55])[0]"),
        ex("bedrooms",
           "0 if property_type == 'Bedsit' else "
           "rnd.choices([1, 2], [88, 12])[0] if 'SilverLiving' in scheme_type or scheme_type == 'Supported housing' else "
           "rnd.choices([1, 2, 3], [45, 45, 10])[0] if property_type == 'Flat' else "
           "rnd.choices([2, 3], [60, 40])[0] if property_type == 'Maisonette' else "
           "rnd.choices([1, 2], [55, 45])[0] if property_type == 'Bungalow' else "
           "rnd.choices([2, 3, 4], [34, 56, 10])[0]"),
        ex("address_line1",
           "('Flat ' + str(item + 1) + ', ' + base['scheme_name']) if property_type in ('Flat', 'Bedsit', 'Maisonette') and scheme_type != 'Street properties' else "
           "(str(rnd.randint(1, 140)) + ' ' + fake.street_name()) if scheme_type == 'Street properties' else "
           "(str(item + 1) + ' ' + base['scheme_name'])"),
        ex("postcode", f"base['postcode_sector'] + choice({PC_LET}) + choice({PC_LET})"),
        ex("tenure",
           "('Leasehold' if rnd.random() < 0.15 else 'Social rent') if scheme_type == 'General needs block' else "
           "rnd.choices(['Social rent', 'Leasehold', 'Affordable rent'], [89, 7, 4])[0] if scheme_type == 'General needs estate' else "
           "('Leasehold' if rnd.random() < 0.03 else 'Social rent') if scheme_type == 'Street properties' else "
           "'Older persons & supported' if 'SilverLiving' in scheme_type or scheme_type == 'Supported housing' else "
           "'Market rent' if scheme_type == 'Market rent' else "
           "rnd.choices(['Social rent', 'Affordable rent', 'Shared ownership'], [31, 40, 29])[0] if scheme_id == 'SCH14' else "
           "rnd.choices(['Affordable rent', 'Shared ownership'], [68, 32])[0]"),
        col("build_year", "base"),
        ex("storeys", "base['max_storeys'] if property_type in ('Flat', 'Bedsit', 'Maisonette') else (1 if property_type == 'Bungalow' else 2)"),
        ex("heating",
           "'Air source heat pump' if build_year >= 2022 else "
           "'Electric storage heaters' if scheme_id == 'SCH01' or rnd.random() < 0.04 else "
           "rnd.choices(['Gas combi boiler', 'Gas system boiler'], [84, 16])[0]"),
        ex("has_gas", "heating.startswith('Gas')"),
        ex("epc_rating",
           "rnd.choices(['A', 'B'], [40, 60])[0] if build_year >= 2022 else "
           "rnd.choices(['B', 'C', 'A'], [72, 22, 6])[0] if build_year >= 2005 else "
           "rnd.choices(['C', 'B', 'D'], [70, 8, 22])[0] if build_year >= 1980 else "
           "rnd.choices(['C', 'D', 'E'], [44, 46, 10])[0] if build_year >= 1950 else "
           "rnd.choices(['C', 'D', 'E', 'F'], [25, 50, 20, 5])[0]"),
        col("decent_homes", "const", value="Yes"),
        ex("last_stock_survey", "None if build_year >= 2024 or rnd.random() < 0.08 else (d('2021-05-01') + timedelta(days=rnd.randint(0, 1980))).date().isoformat()"),
        ex("weekly_rent",
           "round(0.0, 2) if tenure == 'Leasehold' else round("
           "104 + 13 * bedrooms + rnd.uniform(-5, 6) if tenure == 'Social rent' else "
           "158 + 31 * bedrooms + rnd.uniform(-8, 10) if tenure == 'Affordable rent' else "
           "60 + 14 * bedrooms + rnd.uniform(-6, 8) if tenure == 'Shared ownership' else "
           "106 + 7 * bedrooms + rnd.uniform(-4, 5) if tenure == 'Older persons & supported' else "
           "215 + 74 * bedrooms + rnd.uniform(-10, 15), 2)"),
        ex("weekly_service_charge",
           "round(rnd.uniform(34, 58), 2) if scheme_type == 'Extra care (SilverLiving)' else "
           "round(rnd.uniform(24, 36), 2) if 'SilverLiving' in scheme_type or scheme_type == 'Supported housing' else "
           "round(rnd.uniform(12, 24), 2) if property_type in ('Flat', 'Maisonette', 'Bedsit') and scheme_type != 'Street properties' else "
           "round(rnd.uniform(1.2, 3.5), 2) if scheme_type in ('General needs estate', 'New build mixed tenure') else 0.0"),
        ex("status", "'New build - awaiting let' if scheme_id == 'SCH14' and item >= 44 else 'Occupied'"),
        ex("repair_weight",
           "2.6 if scheme_id == 'SCH03' else 0.25 if tenure in ('Leasehold', 'Shared ownership') else "
           "0.5 if build_year >= 2022 else 1.4 if scheme_id == 'SCH01' else 0.8 if tenure == 'Market rent' else 1.0"),
        ex("damp_weight",
           "0 if tenure in ('Leasehold', 'Shared ownership') else 5.0 if scheme_id == 'SCH03' else 2.5 if scheme_id == 'SCH01' else "
           "2.0 if scheme_id == 'SCH21' else 1.3 if build_year < 1980 else 0.3 if build_year >= 2010 else 0.8"),
    ],
}

# ---------------------------------------------------------------- employees
EXTRA_STAFF = [
    # id, name, title, dept, manager, location, start
    ("E0901", "Tom Reed", "Housing Officer (Maidstone North & Town)", "tenancy", "P011", "Field-based", "2017-04-03"),
    ("E0902", "Sasha Kemp", "Housing Officer (Maidstone East & Villages)", "tenancy", "P011", "Field-based", "2020-08-24"),
    ("E0903", "Joel Mensah", "Housing Officer (Tonbridge, Medway, Swale & Ashford)", "tenancy", "P011", "Field-based", "2023-11-06"),
    ("E0904", "Marcus Adebayo", "Damp & Mould Surveyor", "repairs", "P008", "Field-based", "2025-09-15"),
    ("E0905", "Leah Foster", "Complaints Officer", "customer", "P012", "Maidstone", "2024-06-03"),
    ("E0906", "Priya Chauhan", "Income Officer", "tenancy", "P015", "Maidstone", "2019-02-11"),
    ("E0907", "Sam Odukoya", "Income Officer", "tenancy", "P015", "Maidstone", "2021-10-04"),
]
ROLES = [  # generated staff, in order
    ("repairs", "Multi-trade Operative (Plumbing)", "P018"), ("repairs", "Multi-trade Operative (Plumbing)", "P018"),
    ("repairs", "Multi-trade Operative (Plumbing)", "P018"), ("repairs", "Electrician", "P018"),
    ("repairs", "Electrician", "P018"), ("repairs", "Gas Engineer", "P018"), ("repairs", "Gas Engineer", "P018"),
    ("repairs", "Gas Engineer", "P018"), ("repairs", "Carpenter", "P018"), ("repairs", "Carpenter", "P018"),
    ("repairs", "Carpenter", "P018"), ("repairs", "Operative Decorator (Damp & Mould)", "P008"),
    ("repairs", "Operative Decorator (Damp & Mould)", "P008"), ("repairs", "Plasterer", "P018"),
    ("repairs", "Multi-trade Operative", "P018"), ("repairs", "Multi-trade Operative", "P018"),
    ("repairs", "Multi-trade Operative", "P018"), ("repairs", "Clearance Operative (Voids)", "P021"),
    ("repairs", "Clearance Operative (Voids)", "P021"), ("repairs", "Repairs Planner", "P018"),
    ("customer", "Customer Service Adviser", "P030"), ("customer", "Customer Service Adviser", "P030"),
    ("customer", "Customer Service Adviser", "P030"), ("customer", "Customer Service Adviser", "P030"),
    ("tenancy", "SilverLiving Scheme Officer", "P027"), ("finance", "Finance Assistant", "P016"),
    ("people", "IT Support Analyst", "P014"),
]
N_SEED = 40 + len(EXTRA_STAFF)
employees = {
    "name": "employees", "title": "Staff Directory", "department": "people", "system": "PeoplePath",
    "description": "All Silvering employees with role, team, manager, base, trade (for operatives), contract and salary. Confidential: contains salary data.",
    "rows": len(ROLES),
    "seed_from_company": "people",
    "map": {"employee_id": "id", "full_name": "name", "job_title": "title", "department": "department",
            "manager_id": "manager", "location": "location", "start_date": "start_date", "email": "email"},
    "seed_rows": [dict(employee_id=a, full_name=b, job_title=c, department=dd, manager_id=m, location=loc, start_date=s,
                       email=b.lower().replace(" ", ".") + "@silvering-homes.org.uk") for a, b, c, dd, m, loc, s in EXTRA_STAFF],
    "columns": [
        col("employee_id", "seq", prefix="E", start=1001 - N_SEED),
        ex("full_name", "fake.first_name() + ' ' + fake.last_name()"),
        ex("job_title", f"{json.dumps([r[1] for r in ROLES])}[int(employee_id[1:]) - 1001]"),
        ex("department", f"{json.dumps([r[0] for r in ROLES])}[int(employee_id[1:]) - 1001]"),
        ex("manager_id", f"{json.dumps([r[2] for r in ROLES])}[int(employee_id[1:]) - 1001]"),
        ex("location", "'Field-based' if department == 'repairs' and 'Planner' not in job_title else ('Aylesford depot' if department == 'repairs' else ('Linton Lodge' if department == 'tenancy' else 'Maidstone'))"),
        col("start_date", "date", start="2012-04-01", end="2026-09-01", weekdays=True),
        ex("email", "full_name.lower().replace(' ', '.').replace(\"'\", '') + '@silvering-homes.org.uk'"),
        ex("trade",
           "'Plumbing' if 'Plumbing' in job_title else 'Electrical' if 'Electric' in job_title else 'Gas & heating' if 'Gas' in job_title else "
           "'Carpentry' if 'Carpenter' in job_title else 'Damp & mould' if 'Damp & Mould)' in job_title or 'Plasterer' in job_title else "
           "'Multi-trade' if job_title == 'Multi-trade Operative' else 'Voids clearance' if 'Clearance' in job_title else None"),
        ex("contract", "'Fixed term' if rnd.random() < 0.06 else 'Permanent'"),
        ex("fte", "rnd.choice([0.6, 0.8]) if rnd.random() < 0.14 and trade is None else 1.0"),
        ex("salary_gbp",
           "{'P001': 128000, 'P002': 104000, 'P003': 98000, 'P004': 98000, 'P005': 96000, 'P006': 18000}.get(employee_id) or "
           "(rnd.randint(52, 64) * 1000 if 'Head of' in job_title else rnd.randint(42, 50) * 1000 if 'Manager' in job_title or 'Controller' in job_title else "
           "rnd.randint(34, 41) * 1000 if trade or 'Surveyor' in job_title or 'Officer' in job_title else rnd.randint(25, 31) * 1000)"),
        ex("status", "'Active'"),
    ],
}

# ---------------------------------------------------------------- voids
voids = {
    "name": "voids", "title": "Void Properties", "department": "repairs", "system": "Keystone Housing / FieldLoop",
    "description": "Every empty home (relets) since November 2024: why it became empty, void type, works and let dates, days empty and rent lost.",
    "rows": 214, "sort_by": "void_start", "sharepoint_list": True, "list_title": "Void Tracker",
    "columns": [
        col("void_id", "seq", prefix="VD", start=3001),
        col("uprn", "fk", table="properties", column="uprn",
            filter="ref['tenure'] not in ('Leasehold', 'Shared ownership') and ref['scheme_id'] != 'SCH14'",
            carry={"property_ref": "property_ref", "scheme_id": "scheme_id", "scheme_name": "scheme_name", "tenure": "tenure", "weekly_rent": "weekly_rent"}),
        col("property_ref", "carried"), col("scheme_id", "carried"), col("scheme_name", "carried"), col("tenure", "carried"),
        col("void_start", "date", start="2024-11-04", end="2026-11-02", weekdays=True),
        ex("void_reason", "rnd.choices(['Death of tenant', 'Transfer to another Silvering home', 'Moved to another landlord or private', 'Moved into care', 'Abandonment', 'Eviction', 'Other'], [26, 20, 18, 12, 7, 5, 12])[0] if tenure != 'Older persons & supported' else rnd.choices(['Death of tenant', 'Moved into care', 'Moved to family', 'Other'], [52, 30, 12, 6])[0]"),
        ex("void_type", "'Major works' if (void_reason in ('Death of tenant', 'Abandonment', 'Eviction') and rnd.random() < 0.5) or rnd.random() < 0.12 else 'Standard'"),
        ex("works_completed", "(lambda x: None if x > as_of else x.date().isoformat())(d(void_start) + timedelta(days=max(4, int(rnd.gauss(38, 12) if void_type == 'Major works' else rnd.gauss(14, 5)))))"),
        ex("let_date", "None if works_completed is None else (lambda x: None if x > as_of else x.date().isoformat())(d(works_completed) + timedelta(days=max(1, int(rnd.gauss(7, 4) + (7 if void_start >= '2026-05-01' else 0)))))"),
        ex("status", "'Let' if let_date else ('Ready to let' if works_completed else 'Works in progress')"),
        ex("days_void", "((d(let_date) if let_date else as_of) - d(void_start)).days"),
        col("weekly_rent", "carried"),
        ex("rent_loss_gbp", "round((weekly_rent or 0) / 7 * days_void, 2)"),
        col("void_supervisor", "const", value="Steve Harlow"),
        col("lettings_officer", "const", value="Chloe Benson"),
    ],
}

# ---------------------------------------------------------------- tenancies
OPEN_VOIDS = "{v['uprn'] for v in tables['voids'] if v['status'] != 'Let'}"
tenancies = {
    "name": "tenancies", "title": "Tenancies & Households", "department": "tenancy", "system": "Keystone Housing",
    "description": "Current tenancies and leases: lead tenant, tenancy type, start date, household, vulnerability and Universal Credit. Confidential: personal and special category data.",
    "from_table": "properties", "where": f"status == 'Occupied' and uprn not in {OPEN_VOIDS}",
    "columns": [
        col("tenancy_ref", "seq", prefix="TEN", start=500001),
        col("uprn", "base"), col("property_ref", "base"), col("scheme_id", "base"), col("scheme_name", "base"),
        col("tenure", "base"), col("patch_officer", "base"), col("address_line1", "base"), col("postcode", "base"),
        ex("tenancy_type",
           "{'Shared ownership': 'Shared ownership lease', 'Market rent': 'Assured periodic (market rent)', 'Leasehold': 'Long lease (right to buy)'}.get(tenure, 'Assured')"),
        ex("start_date",
           "(d('2026-10-05') + timedelta(days=rnd.randint(0, 24))).date().isoformat() if base['scheme_id'] == 'SCH14' else "
           "(lambda lo: (lo + timedelta(days=int((as_of - lo).days * (rnd.random() ** 0.8) * 0.98))).date().isoformat())"
           "(d(str(max(base['build_year'], 1976)) + '-03-01'))"),
        ex("lead_tenant", "fake.first_name() + ' ' + fake.last_name()"),
        ex("lead_tenant_age",
           "rnd.randint(58, 96) if tenure == 'Older persons & supported' and base['scheme_id'] != 'SCH13' else "
           "rnd.randint(19, 45) if base['scheme_id'] == 'SCH13' else rnd.randint(24, 62) if tenure == 'Market rent' else "
           "max(19, min(92, int(rnd.gauss(49, 16))))"),
        ex("household_size",
           "rnd.choices([1, 2], [82, 18])[0] if tenure == 'Older persons & supported' else "
           "rnd.choices([1, 2, 3, 4], [40, 35, 18, 7])[0] if base['property_type'] != 'House' else rnd.choices([1, 2, 3, 4, 5, 6], [10, 22, 28, 24, 11, 5])[0]"),
        ex("children_in_household", "household_size >= 3 and lead_tenant_age < 60 and rnd.random() < 0.8"),
        ex("vulnerability_flag", "rnd.random() < (0.55 if tenure == 'Older persons & supported' else 0.17)"),
        ex("vulnerability_type", "rnd.choice(['Mobility', 'Mental health', 'Respiratory condition', 'Hearing or sight', 'Learning disability', 'Domestic abuse survivor', 'Frailty']) if vulnerability_flag else None"),
        ex("universal_credit", "tenure in ('Social rent', 'Affordable rent', 'Market rent', 'Older persons & supported') and lead_tenant_age < 66 and rnd.random() < (0.47 if tenure == 'Affordable rent' else 0.12 if tenure == 'Market rent' else 0.6 if base['scheme_id'] == 'SCH13' else 0.4)"),
        ex("apa_in_place", "universal_credit and rnd.random() < 0.28"),
        ex("contact_preference", "rnd.choices(['Phone', 'Letter', 'Email', 'MySilvering app'], [55, 30, 10, 5])[0] if lead_tenant_age >= 70 else rnd.choices(['Phone', 'Email', 'MySilvering app', 'Letter'], [42, 26, 24, 8])[0]"),
        ex("phone", "'07700 900' + str(rnd.randint(100, 999))"),
        ex("email", "None if contact_preference in ('Letter',) and rnd.random() < 0.7 else lead_tenant.lower().replace(' ', '.').replace(\"'\", '') + str(rnd.randint(1, 99)) + '@' + choice(['example.com', 'example.net', 'example.org'])"),
        ex("status", "'Notice given' if rnd.random() < 0.012 else 'Current'"),
        col("weekly_rent", "base"), col("weekly_service_charge", "base"), col("damp_weight", "base"),
        ex("complaint_weight", "2.6 if base['scheme_id'] == 'SCH03' else 1.6 if base['scheme_id'] in ('SCH01', 'SCH14') else 1.0"),
    ],
}

rent_accounts = {
    "name": "rent_accounts", "title": "Rent Accounts", "department": "tenancy", "system": "Keystone Housing",
    "description": "One account per tenancy or lease: weekly charge, current balance (positive = arrears), recovery stage, Universal Credit/APA, last payment and income officer.",
    "from_table": "tenancies",
    "columns": [
        col("account_ref", "seq", prefix="RA", start=700001),
        col("tenancy_ref", "base"), col("property_ref", "base"), col("scheme_id", "base"), col("lead_tenant", "base"), col("tenure", "base"),
        col("universal_credit", "base"), col("apa_in_place", "base"),
        ex("weekly_charge", "round((base['weekly_rent'] or 0) + (base['weekly_service_charge'] or 0), 2)"),
        ex("balance_gbp",
           "(lambda p: round(weekly_charge * (min(26, rnd.expovariate(1 / 4.6)) + 0.3), 2) if rnd.random() < p else "
           "(-round(weekly_charge * rnd.uniform(0, 1.6), 2) if rnd.random() < 0.45 else 0.0))"
           "(0.5 if universal_credit and not apa_in_place else 0.34 if universal_credit else 0.07 if tenure == 'Older persons & supported' else 0.1 if tenure in ('Leasehold', 'Shared ownership') else 0.18)"),
        ex("weeks_in_arrears", "round(balance_gbp / weekly_charge, 1) if balance_gbp > 0 and weekly_charge else 0.0"),
        ex("arrears_band", "'No arrears' if balance_gbp <= 0 else 'Under £250' if balance_gbp < 250 else '£250 - £999' if balance_gbp < 1000 else '£1,000 - £2,499' if balance_gbp < 2500 else '£2,500 and over'"),
        ex("recovery_stage",
           "'None' if balance_gbp <= 0 else 'Early contact' if weeks_in_arrears < 1 else 'Stage 1 - letter' if weeks_in_arrears < 3 else "
           "rnd.choice(['Payment arrangement', 'Stage 2 - call and visit']) if weeks_in_arrears < 7 else "
           "rnd.choice(['Payment arrangement', 'NOSP served', 'Hardship referral']) if weeks_in_arrears < 13 else "
           "rnd.choice(['NOSP served', 'Court action pending', 'Suspended possession order'])"),
        ex("last_payment_date", "(as_of - timedelta(days=rnd.randint(1, 13) if balance_gbp <= 0 else rnd.randint(3, 20) if weeks_in_arrears < 6 else rnd.randint(10, 75))).date().isoformat()"),
        ex("income_officer", "choice(['Ryan Tait', 'Priya Chauhan', 'Sam Odukoya'])"),
    ],
}

# ---------------------------------------------------------------- repairs
DESC = {
    "Plumbing": ["Leaking tap in kitchen", "Toilet not flushing", "Leak under bath", "Blocked sink", "Water coming through ceiling from flat above", "Dripping overflow pipe", "Shower not working", "Burst pipe in airing cupboard"],
    "Heating & gas": ["No heating or hot water", "Boiler losing pressure", "Radiator cold at top", "Boiler making loud banging noise", "Thermostat not working", "Smell of gas reported (made safe)"],
    "Electrical": ["Sockets not working in bedroom", "Light fitting not working in hallway", "Extractor fan not working in bathroom", "Smoke alarm beeping", "Electric shower tripping", "Exposed wiring at light switch"],
    "Carpentry": ["Front door not locking", "Kitchen cupboard door hanging off", "Internal door sticking", "Loose stair handrail", "Skirting board damaged", "Window board rotten"],
    "Windows & doors": ["Window will not close", "Condensation between double-glazed panes", "Back door seal letting in draught", "Broken window catch (child safety)", "Patio door off its runners"],
    "Damp & mould": ["Black mould on bedroom wall", "Mould around bathroom window", "Damp patch on living room ceiling", "Musty smell and mould in child's bedroom", "Condensation running down windows every morning"],
    "Roofing": ["Roof leak into loft", "Slipped roof tiles", "Gutter overflowing", "Flat roof leaking over kitchen", "Fascia board loose"],
    "Plastering": ["Crack in ceiling plaster", "Plaster blown behind tiles", "Hole in wall after leak", "Ceiling repair after water damage"],
    "Drainage": ["Blocked outside drain", "Smell from drain", "Gully overflowing", "Shared drain blocked (block)"],
    "Fencing & external": ["Fence panel blown down", "Path slab uneven (trip hazard)", "Gate broken", "Communal bin store door broken", "Outside light not working"],
    "General": ["Pre-tenancy inspection follow-up", "Install grab rail", "Replace bath panel", "Ease and adjust doors", "Make good after adaptation"],
}
TARGET = {"Emergency": 1, "Urgent": 7, "Routine": 28, "Planned": 90}
repairs = {
    "name": "repairs", "title": "Responsive Repairs", "department": "repairs", "system": "FieldLoop",
    "description": "Every responsive repair reported since November 2024: trade, priority, target and completion dates, operative or contractor, cost, first-time fix and resident feedback.",
    "rows": 6900, "sort_by": "reported_date", "sharepoint_list": True, "list_rows": 400, "list_title": "Repairs (latest 400)",
    "columns": [
        col("job_no", "seq", prefix="RJ", start=400001),
        col("uprn", "fk", table="properties", column="uprn", weight_col="repair_weight",
            carry={"property_ref": "property_ref", "scheme_id": "scheme_id", "scheme_name": "scheme_name", "tenure": "tenure", "address_line1": "address_line1", "build_year": "build_year"}),
        col("property_ref", "carried"), col("scheme_id", "carried"), col("scheme_name", "carried"), col("tenure", "carried"), col("address_line1", "carried"),
        ex("reported_date", "(lambda x: x if x.weekday() < 5 or rnd.random() < 0.3 else x - timedelta(days=x.weekday() - 4))(d('2024-11-04') + timedelta(days=rnd.randint(0, 730), hours=rnd.randint(7, 19), minutes=rnd.choice([0, 10, 20, 30, 40, 50])) if build_year < 2026 else d('2026-10-06') + timedelta(days=rnd.randint(0, 29), hours=rnd.randint(8, 17))).strftime('%Y-%m-%dT%H:%M:00')"),
        ex("channel", "rnd.choices(['Phone', 'MySilvering portal', 'Email', 'Operative-raised', 'Housing officer'], [54, 23, 10, 8, 5])[0]"),
        ex("trade", f"rnd.choices({json.dumps(list(DESC))}, [20, 12, 12, 14, 8, 6 if build_year >= 1980 else 10, 5, 6, 5, 6, 4])[0]"),
        ex("description", f"choice({json.dumps(DESC)}[trade])"),
        ex("priority",
           "'Emergency' if description in ('No heating or hot water', 'Smell of gas reported (made safe)', 'Water coming through ceiling from flat above', 'Burst pipe in airing cupboard', 'Exposed wiring at light switch', 'Front door not locking') and rnd.random() < 0.85 else "
           "rnd.choices(['Emergency', 'Urgent', 'Routine', 'Planned'], [6, 24, 64, 6])[0]"),
        ex("target_date", f"(d(reported_date) + timedelta(days={json.dumps(TARGET)}[priority])).date().isoformat()"),
        ex("_due_dt", "None", ),
        ex("completed_date",
           "(lambda x: x.strftime('%Y-%m-%dT%H:%M:00'))(d(reported_date) + timedelta(hours=("
           "rnd.uniform(1, 20) if rnd.random() < 0.93 else rnd.uniform(24, 60)) if priority == 'Emergency' else timedelta(days=max(0.2, ("
           "rnd.gauss(4.6, 2.4) if priority == 'Urgent' else rnd.gauss(16, 8) if priority == 'Routine' else rnd.gauss(55, 22))"
           " + (rnd.uniform(0, 14) if scheme_id == 'SCH03' and priority in ('Routine', 'Urgent') else 0)"
           " + (rnd.uniform(0, 17) if priority == 'Routine' and reported_date >= '2026-05-01' else 0)"
           " + (rnd.uniform(0, 12) if trade == 'Electrical' and reported_date >= '2026-03-01' and priority != 'Emergency' else 0)"
           " + (rnd.uniform(0, 6) if trade in ('Damp & mould', 'Roofing') else 0))).total_seconds() / 3600))"),
        ex("status", "'Cancelled' if rnd.random() < 0.03 else ('Completed' if d(completed_date) <= as_of else rnd.choices(['Open', 'Appointment booked', 'Awaiting parts', 'Awaiting contractor'], [40, 38, 14, 8])[0])"),
        ex("days_to_complete", "round((d(completed_date) - d(reported_date)).total_seconds() / 86400, 1) if status == 'Completed' else None"),
        ex("in_target", "(d(completed_date).date() <= d(target_date).date()) if status == 'Completed' else None"),
        ex("overdue", "status not in ('Completed', 'Cancelled') and as_of.date() > d(target_date).date()"),
        ex("contractor", "('Weald Roofing & Guttering Ltd' if trade == 'Roofing' else 'ClearFlow Drainage Ltd') if trade in ('Roofing', 'Drainage') else ('Brightline Electrical Ltd' if trade == 'Electrical' and reported_date >= '2026-03-01' and rnd.random() < 0.3 else None)"),
        ex("operative",
           "None if contractor else (lambda pool: choice(pool) if pool else None)([e['full_name'] for e in tables['employees'] if e['trade'] == "
           "{'Plumbing': 'Plumbing', 'Heating & gas': 'Gas & heating', 'Electrical': 'Electrical', 'Carpentry': 'Carpentry', 'Windows & doors': 'Carpentry', "
           "'Damp & mould': 'Damp & mould', 'Plastering': 'Damp & mould', 'Fencing & external': 'Multi-trade', 'General': 'Multi-trade'}.get(trade)])"),
        ex("cost_gbp", "round(max(18, rnd.gauss({'Plumbing': 95, 'Heating & gas': 140, 'Electrical': 110, 'Carpentry': 120, 'Windows & doors': 160, 'Damp & mould': 340, 'Roofing': 420, 'Plastering': 210, 'Drainage': 180, 'Fencing & external': 150, 'General': 90}[trade], 40)) * (1.25 if contractor else 1), 2) if status == 'Completed' else None"),
        ex("first_time_fix", "(rnd.random() < (0.62 if scheme_id == 'SCH03' else 0.79)) if status == 'Completed' else None"),
        ex("resident_rating", "(rnd.choices([5, 4, 3, 2, 1], [44, 26, 12, 9, 9] if in_target and first_time_fix else [16, 20, 20, 20, 24])[0]) if status == 'Completed' and rnd.random() < 0.28 else None"),
    ],
}
repairs["columns"] = [c for c in repairs["columns"] if c["name"] != "_due_dt"]

# ---------------------------------------------------------------- damp & mould
SEASON = "[1.7, 1.8, 1.5, 1.0, 0.6, 0.5, 0.45, 0.5, 0.7, 1.1, 1.5, 1.8]"
damp = {
    "name": "damp_mould_cases", "title": "Damp & Mould Cases", "department": "repairs", "system": "FieldLoop / Keystone Housing",
    "description": "Damp and mould reports since November 2024 with hazard level, investigation, written summary and works dates. Cases from 27 October 2025 are covered by Awaab's Law timescales.",
    "rows": 232, "sort_by": "reported_date", "sharepoint_list": True, "list_title": "Damp & Mould Tracker",
    "columns": [
        col("case_id", "seq", prefix="DM", start=1001),
        col("tenancy_ref", "fk", table="tenancies", column="tenancy_ref", weight_col="damp_weight",
            carry={"uprn": "uprn", "property_ref": "property_ref", "scheme_id": "scheme_id", "scheme_name": "scheme_name", "address_line1": "address_line1",
                   "lead_tenant": "lead_tenant", "vulnerability_flag": "vulnerability_flag", "children_in_household": "children_in_household"}),
        col("uprn", "carried"), col("property_ref", "carried"), col("scheme_id", "carried"), col("scheme_name", "carried"), col("address_line1", "carried"),
        col("lead_tenant", "carried"), col("vulnerability_flag", "carried"), col("children_in_household", "carried"),
        ex("reported_date", f"(lambda days: rnd.choices(days, [{SEASON}[x.month - 1] for x in days])[0].date().isoformat())([d('2024-11-04') + timedelta(days=k) for k in range(0, 730) if (d('2024-11-04') + timedelta(days=k)).weekday() < 5])"),
        ex("source", "rnd.choices(['Repair report', 'Housing officer visit', 'MySilvering', 'Complaint', 'Operative-raised', 'TSM survey', 'Councillor or MP'], [44, 15, 14, 9, 9, 5, 4])[0]"),
        ex("hazard_level", "rnd.choices(['Emergency', 'Significant', 'Not significant'], [7, 58 + (10 if children_in_household or vulnerability_flag else 0), 35])[0]"),
        ex("awaabs_law", "reported_date >= '2025-10-27'"),
        ex("investigation_due", f"(d(reported_date) + timedelta(days=1)).date().isoformat() if hazard_level == 'Emergency' else {WD}(d(reported_date), 10){ISO}"),
        ex("investigated_date",
           "(lambda x: None if x > as_of else x.date().isoformat())(d(reported_date) + timedelta(days=("
           "(0 if rnd.random() < 0.85 else rnd.randint(1, 3)) if hazard_level == 'Emergency' else "
           "max(1, int(rnd.gauss(7, 3) + (rnd.uniform(0, 9) if scheme_id == 'SCH03' else 0) + (rnd.uniform(0, 5) if reported_date >= '2026-06-01' else 0))) if awaabs_law else max(2, int(rnd.gauss(16, 8))))))"),
        ex("summary_due", f"{WD}(d(investigated_date), 3){ISO} if investigated_date else None"),
        ex("summary_sent_date",
           "None if not investigated_date or (awaabs_law and rnd.random() < 0.03) else (lambda x: None if x > as_of else x.date().isoformat())(d(investigated_date) + timedelta(days=rnd.choices([0, 1, 2, 3, 4, 6, 9, 14], [16, 32, 24, 12, 7, 4, 3, 2])[0]))"),
        ex("works_due", f"(None if hazard_level == 'Not significant' or not investigated_date else (d(investigated_date) + timedelta(days=1)).date().isoformat() if hazard_level == 'Emergency' else {WD}(d(investigated_date), 5){ISO})"),
        ex("works_started_date",
           "None if not works_due else (lambda x: None if x > as_of else x.date().isoformat())(d(investigated_date) + timedelta(days=(rnd.choice([0, 0, 1, 1, 2]) if hazard_level == 'Emergency' else max(1, int(rnd.gauss(4, 2) + (rnd.uniform(0, 7) if scheme_id == 'SCH03' else 0))))))"),
        ex("works_completed_date", "None if not works_started_date else (lambda x: None if x > as_of else x.date().isoformat())(d(works_started_date) + timedelta(days=max(1, int(rnd.gauss(12, 8)))))"),
        ex("cause", "rnd.choices(['Condensation (ventilation)', 'Penetrating damp', 'Plumbing leak', 'Roof or gutter defect', 'Rising damp', 'Cold bridging / insulation'], [44, 18, 13, 12, 5, 8])[0]"),
        ex("surveyor", "('Marcus Adebayo' if rnd.random() < 0.45 else 'Ellie Novak') if reported_date >= '2025-09-15' else 'Ellie Novak'"),
        ex("alternative_accommodation", "'Decant to temporary accommodation' if hazard_level == 'Emergency' and rnd.random() < 0.35 else None"),
        ex("status", "'Open - awaiting investigation' if not investigated_date else 'Open - works in progress' if works_due and not works_completed_date else 'Open - awaiting written summary' if not summary_sent_date else 'Closed'"),
        ex("timescale_breach",
           "None if not awaabs_law else (lambda r: '; '.join(r) or None)([m for m, bad in ["
           "('Investigation late', (d(investigated_date) if investigated_date else as_of).date() > d(investigation_due).date()), "
           "('Written summary late', bool(investigated_date) and (d(summary_sent_date) if summary_sent_date else as_of).date() > d(summary_due).date()), "
           "('Safety works start late', bool(works_due) and (d(works_started_date) if works_started_date else as_of).date() > d(works_due).date())] if bad])"),
    ],
}

# ---------------------------------------------------------------- complaints
CMP_CAT = ["Repairs - delay", "Repairs - quality", "Damp & mould", "Communication", "Anti-social behaviour handling", "Staff conduct", "Rent & service charges", "Estate services & cleaning", "Lettings & transfers", "New build defects"]
CMP_SUM = {
    "Repairs - delay": ["Waited weeks for a leak repair; three missed appointments", "Heating repair still not done after operative said parts were ordered", "Routine repair booked and cancelled twice without notice"],
    "Repairs - quality": ["Repair had to be redone three times", "Operative left mess and did not finish the job", "Window replaced but still lets in water"],
    "Damp & mould": ["Mould keeps coming back after treatment; child has asthma", "Told it was condensation and to open windows; no inspection", "No written update after damp inspection"],
    "Communication": ["Nobody returns calls or emails", "Letter sent to wrong name after bereavement", "Promised call-back did not happen"],
    "Anti-social behaviour handling": ["Reported noise for months and nothing done", "Case closed without telling me", "Feel unsafe and officer has not visited"],
    "Staff conduct": ["Adviser was rude on the phone", "Operative was dismissive about my disability", "Officer discussed my case in front of neighbours"],
    "Rent & service charges": ["Service charge increase not explained", "Payment not credited to rent account", "Threatening arrears letter sent while UC claim was pending"],
    "Estate services & cleaning": ["Communal areas not cleaned for weeks", "Grass not cut and bins overflowing", "Lift out of order repeatedly"],
    "Lettings & transfers": ["Transfer request ignored", "Home not ready on move-in day", "Not told why bid was unsuccessful"],
    "New build defects": ["Snagging items still outstanding after move-in", "Heat pump controls not explained and bills high", "Front door does not seal properly"],
}
complaints = {
    "name": "complaints", "title": "Complaints Register", "department": "customer", "system": "Keystone Housing",
    "description": "All formal complaints since November 2024 under the Complaint Handling Code: stage 1 and stage 2 dates and targets, outcome, compensation and Housing Ombudsman referrals.",
    "rows": 214, "sort_by": "received_date", "sharepoint_list": True, "list_title": "Complaints Register",
    "columns": [
        col("complaint_id", "seq", prefix="CMP-", start=24001),
        col("tenancy_ref", "fk", table="tenancies", column="tenancy_ref", weight_col="complaint_weight",
            carry={"property_ref": "property_ref", "scheme_id": "scheme_id", "scheme_name": "scheme_name", "lead_tenant": "lead_tenant", "tenure": "tenure"}),
        col("property_ref", "carried"), col("scheme_id", "carried"), col("scheme_name", "carried"), col("complainant", "carried"), col("tenure", "carried"),
        col("received_date", "date", start="2024-11-04", end="2026-11-03", weekdays=True),
        ex("channel", "rnd.choices(['Phone', 'Email', 'MySilvering', 'Letter', 'In person', 'Councillor or MP'], [38, 26, 20, 5, 5, 6])[0]"),
        ex("category", f"rnd.choices({json.dumps(CMP_CAT)}, [24, 12, 15 if scheme_id != 'SCH03' else 40, 12, 8, 5, 6, 8, 4, 0 if scheme_id not in ('SCH14', 'SCH25') else 40])[0]"),
        ex("summary", f"choice({json.dumps(CMP_SUM)}[category])"),
        ex("ack_due", f"{WD}(d(received_date), 5){ISO}"),
        ex("ack_date", "(lambda x: None if x > as_of else x.date().isoformat())(d(received_date) + timedelta(days=rnd.choices([0, 1, 2, 3, 5, 7, 9], [20, 30, 20, 12, 9, 6, 3])[0]))"),
        ex("stage1_due", f"{WD}(d(ack_date), 10){ISO} if ack_date else None"),
        ex("stage1_response_date",
           "None if not ack_date else (lambda x: None if x > as_of else x.date().isoformat())(d(ack_date) + timedelta(days=max(1, int(rnd.gauss(11, 4.5) + (rnd.uniform(0, 9) if '2026-06-01' <= received_date < '2026-10-01' else 0) + (rnd.uniform(0, 5) if category.startswith('Repairs') or category == 'Damp & mould' else 0)))))"),
        ex("stage1_in_target", "(d(stage1_response_date).date() <= d(stage1_due).date()) if stage1_response_date else None"),
        ex("stage1_outcome", "rnd.choices(['Upheld', 'Partly upheld', 'Not upheld'], [42, 32, 26] if category in ('Repairs - delay', 'Damp & mould', 'Communication') else [28, 30, 42])[0] if stage1_response_date else None"),
        ex("compensation_gbp", "(rnd.choices([0, 50, 75, 100, 150, 250, 400, 650], [16, 18, 14, 18, 12, 10, 8, 4])[0] if stage1_outcome in ('Upheld', 'Partly upheld') else 0) if stage1_response_date else None"),
        ex("escalated_stage2", "bool(stage1_response_date) and rnd.random() < (0.12 if stage1_outcome == 'Upheld' else 0.3)"),
        ex("stage2_received", "(lambda x: None if x > as_of else x.date().isoformat())(d(stage1_response_date) + timedelta(days=rnd.randint(2, 21))) if escalated_stage2 else None"),
        ex("stage2_due", f"{WD}(d(stage2_received), 25){ISO} if stage2_received else None"),
        ex("stage2_response_date", "None if not stage2_received else (lambda x: None if x > as_of else x.date().isoformat())(d(stage2_received) + timedelta(days=max(5, int(rnd.gauss(30, 9)))))"),
        ex("stage2_outcome", "rnd.choices(['Upheld', 'Partly upheld', 'Not upheld'], [30, 35, 35])[0] if stage2_response_date else None"),
        ex("ombudsman", "(rnd.choices(['Referred - awaiting determination', 'Determined - maladministration', 'Determined - service failure', 'Determined - no maladministration'], [40, 20, 20, 20])[0] if rnd.random() < 0.32 else None) if stage2_response_date and stage2_response_date < '2026-09-01' else None"),
        ex("handler", "'Owen Fletcher' if stage2_received else choice(['Mark Pennington', 'Mark Pennington', 'Leah Foster'])"),
        ex("status", "'With Housing Ombudsman' if ombudsman == 'Referred - awaiting determination' else 'Open - stage 2' if stage2_received and not stage2_response_date else 'Open - stage 1' if not stage1_response_date else 'Closed'"),
        ex("learning", "choice(['Missed appointments: text reminder added', 'Damp follow-up visit now booked at inspection', 'Call-back promises logged as tasks in Keystone', 'Repairs history checked before stage 1 response', 'Bereavement name-change process reviewed', 'Contractor quality checks on 10% of jobs', None, None]) if stage1_outcome in ('Upheld', 'Partly upheld') else None"),
    ],
}
for c in complaints["columns"]:
    if c["name"] == "tenancy_ref":
        c["carry"] = {"property_ref": "property_ref", "scheme_id": "scheme_id", "scheme_name": "scheme_name", "complainant": "lead_tenant", "tenure": "tenure"}

# ---------------------------------------------------------------- ASB
asb = {
    "name": "asb_cases", "title": "Anti-social Behaviour Cases", "department": "tenancy", "system": "Keystone Housing",
    "description": "ASB cases opened since November 2024: category, risk, risk assessment, officer, actions taken, outcome and reporter satisfaction. Confidential.",
    "rows": 126, "sort_by": "opened_date",
    "columns": [
        col("case_id", "seq", prefix="ASB-", start=9001),
        col("reporter_tenancy", "fk", table="tenancies", column="tenancy_ref", carry={"scheme_id": "scheme_id", "scheme_name": "scheme_name", "patch_officer": "patch_officer"}),
        col("scheme_id", "carried"), col("scheme_name", "carried"),
        col("opened_date", "date", start="2024-11-04", end="2026-11-03", weekdays=True),
        ex("category", "rnd.choices(['Noise', 'Neighbour dispute', 'Drugs or drug dealing', 'Harassment or threats', 'Vandalism or criminal damage', 'Pets and animals', 'Hate incident', 'Domestic abuse', 'Rubbish and fly-tipping'], [30, 18, 10, 10, 8, 8, 4, 5, 7])[0]"),
        ex("risk_level", "'High' if category in ('Hate incident', 'Domestic abuse', 'Harassment or threats') and rnd.random() < 0.7 else rnd.choices(['High', 'Medium', 'Low'], [8, 42, 50])[0]"),
        ex("risk_assessment_done", "rnd.random() < (0.96 if risk_level == 'High' else 0.72)"),
        ex("officer", "'Gary Doyle' if risk_level == 'High' or category == 'Drugs or drug dealing' else patch_officer"),
        col("patch_officer", "carried"),
        ex("actions_taken", "choice(['Advice and diary sheets', 'Warning letter', 'Mediation referral', 'Acceptable behaviour agreement', 'Joint visit with police', 'Noise monitoring app', 'Injunction application', 'Closure order (partner-led)'])"),
        ex("closed_date", "(lambda x: None if x > as_of else x.date().isoformat())(d(opened_date) + timedelta(days=max(5, int(rnd.gauss(48, 25) * (1.6 if risk_level == 'High' else 1)))))"),
        ex("status", "'Closed' if closed_date else 'Open'"),
        ex("outcome", "choice(['Resolved', 'Resolved', 'Behaviour stopped', 'No further reports', 'Insufficient evidence', 'Reporter moved', 'Legal action']) if closed_date else None"),
        ex("reporter_satisfied", "(rnd.random() < 0.56) if closed_date and rnd.random() < 0.6 else None"),
    ],
}
asb["columns"] = [c for c in asb["columns"] if c["name"] != "patch_officer"]
asb["columns"].insert(3, col("patch_officer", "carried"))

# ---------------------------------------------------------------- compliance
compliance = {
    "name": "compliance_checks", "title": "Home Safety Checks (Gas & Electrical)", "department": "assets", "system": "Assure360",
    "description": "Latest landlord gas safety record (12-monthly) and electrical installation condition report (5-yearly) for every rented home, with result, next due date and status.",
    "from_table": "properties", "where": "tenure not in ('Leasehold', 'Shared ownership')",
    "explode": "(['Gas safety (LGSR)'] if has_gas else []) + ['Electrical (EICR)']",
    "columns": [
        col("check_id", "seq", prefix="CC", start=100001),
        col("uprn", "base"), col("property_ref", "base"), col("scheme_id", "base"), col("scheme_name", "base"), col("address_line1", "base"),
        ex("check_type", "item"),
        ex("last_completed",
           "(d(str(base['build_year']) + '-09-15') + timedelta(days=rnd.randint(0, 20))).date().isoformat() if base['build_year'] == 2026 else "
           "(as_of - timedelta(days=rnd.randint(4, 355))).date().isoformat() if item.startswith('Gas') else "
           "(as_of - timedelta(days=rnd.randint(1832, 1990) if rnd.random() < 0.0185 else rnd.randint(10, 1815))).date().isoformat()"),
        ex("next_due", "(d(last_completed) + timedelta(days=365 if item.startswith('Gas') else 1826)).date().isoformat()"),
        ex("result",
           "rnd.choices(['Satisfactory', 'At risk - remedial works', 'Immediately dangerous - appliance capped'], [95.5, 3.7, 0.8])[0] if item.startswith('Gas') else "
           "rnd.choices(['Satisfactory', 'Unsatisfactory - C2 remedials'], [87, 13])[0]"),
        ex("remedial_status", "None if result == 'Satisfactory' else ('Outstanding' if rnd.random() < 0.18 else 'Completed')"),
        ex("status", "'Compliant' if d(next_due) >= as_of else 'Overdue'"),
        ex("no_access_attempts", "rnd.randint(2, 5) if status == 'Overdue' else 0"),
        ex("engineer", "choice(['Silvering gas team', 'Silvering gas team', 'Kentish Heating Services Ltd']) if item.startswith('Gas') else choice(['Silvering electrical team', 'Brightline Electrical Ltd'])"),
    ],
}
BS_TYPES = "(['Fire risk assessment', 'Legionella risk assessment', 'Asbestos re-inspection (communal)'] + (['Lift thorough examination (LOLER)'] if has_lift else []) + (['Communal fire door inspection'] if max_storeys >= 4 else []))"
building_safety = {
    "name": "building_safety", "title": "Building Safety (Communal Checks)", "department": "assets", "system": "Assure360",
    "description": "Communal fire, water, asbestos, lift and fire door checks for every block and scheme with shared areas, with risk rating and open actions.",
    "from_table": "schemes", "where": "scheme_type not in ('General needs estate', 'Street properties')", "explode": BS_TYPES,
    "sharepoint_list": True, "list_title": "Building Safety Checks",
    "columns": [
        col("check_id", "seq", prefix="BS", start=5001),
        col("scheme_id", "base"), col("scheme_name", "base"), col("max_storeys", "base"),
        ex("check_type", "item"),
        ex("frequency_months", "{'Fire risk assessment': 12 if base['max_storeys'] >= 4 or 'SilverLiving' in base['scheme_type'] else 24, 'Legionella risk assessment': 24, 'Asbestos re-inspection (communal)': 12, 'Lift thorough examination (LOLER)': 6, 'Communal fire door inspection': 3}[item]"),
        ex("last_completed", "(as_of - timedelta(days=rnd.randint(5, int(frequency_months * 30.4) - 5))).date().isoformat() if base['build_year'] < 2026 else '2026-09-28'"),
        ex("next_due", "(d(last_completed) + timedelta(days=int(frequency_months * 30.4))).date().isoformat()"),
        ex("risk_rating", "rnd.choices(['Trivial', 'Tolerable', 'Moderate'], [15, 65, 20])[0] if item == 'Fire risk assessment' else None"),
        ex("open_actions", "rnd.randint(0, 6) if item in ('Fire risk assessment', 'Communal fire door inspection') else rnd.randint(0, 2)"),
        ex("overdue_actions", "0"),
        ex("status", "'Compliant' if d(next_due) >= as_of else 'Overdue'"),
        ex("assessor", "{'Fire risk assessment': 'Fireguard Compliance Ltd', 'Legionella risk assessment': 'AquaSafe Water Hygiene Ltd', 'Asbestos re-inspection (communal)': 'Asbestos Survey Partners Ltd', 'Lift thorough examination (LOLER)': 'Liftwise Engineering Ltd', 'Communal fire door inspection': 'Silvering building safety team'}[item]"),
    ],
}

# ---------------------------------------------------------------- TSM survey
SAT = ["Very dissatisfied", "Fairly dissatisfied", "Neither satisfied nor dissatisfied", "Fairly satisfied", "Very satisfied"]
AGR = ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"]


def tsm_q(name, cond, neg, pos=0.0, labels=SAT):
    # derived from TP01 score with a question-specific shift
    return ex(name,
              f"(lambda s: {json.dumps(labels)}[max(0, min(4, s - (1 if rnd.random() < {neg} else 0) + (1 if rnd.random() < {pos} else 0) + rnd.choice([-1, 0, 0, 0, 0, 0, 1])))])"
              f"({json.dumps(SAT)}.index(tp01_overall)) if {cond} else None")


LCRA = "tenure_group == 'LCRA'"
COMMENTS_POS = ["Repairs team were brilliant, came the next day.", "My housing officer really listens.", "Lovely scheme, Margaret and the team are wonderful.", "Happy with my home, no complaints.", "Much better since the new repairs app.", "The new kitchen made a big difference."]
COMMENTS_NEG = ["Still waiting for the damp in my son's room to be sorted.", "Nobody calls back when they say they will.", "Three appointments missed for the same leak.", "Mould came back two weeks after they painted over it.", "I reported the noise next door for months and nothing happened.", "Service charge went up and no one explained why.", "Communal areas are filthy and the lift keeps breaking.", "As a shared owner I pay for repairs but get no say in anything.", "It takes forever to get through on the phone.", "They closed my complaint without fixing anything."]
tsm = {
    "name": "tsm_survey", "title": "Tenant Satisfaction Survey Responses", "department": "customer", "system": "Customer Voice survey platform",
    "description": "Individual responses to the Tenant Satisfaction Measures survey (TP01-TP12) for 2025/26 and 2026/27 to date, by tenure group, scheme and method, with free-text comments.",
    "rows": 860, "sort_by": "survey_date",
    "columns": [
        col("response_id", "seq", prefix="TSM", start=50001),
        col("tenancy_ref", "fk", table="tenancies", column="tenancy_ref", filter="ref['tenure'] not in ('Market rent', 'Leasehold')",
            carry={"scheme_id": "scheme_id", "scheme_name": "scheme_name", "tenure": "tenure"}),
        col("scheme_id", "carried"), col("scheme_name", "carried"), col("tenure", "carried"),
        ex("tenure_group", "'LCHO' if tenure == 'Shared ownership' else 'LCRA'"),
        col("survey_date", "date", start="2025-04-07", end="2026-10-30", weekdays=True),
        ex("tsm_year", "'2025/26' if survey_date < '2026-04-01' else '2026/27'"),
        ex("method", "rnd.choices(['Telephone', 'Online', 'Paper'], [55, 35, 10])[0]"),
        ex("had_repair_12m", "tenure_group == 'LCRA' and rnd.random() < 0.76"),
        ex("complained_12m", "rnd.random() < (0.36 if scheme_id == 'SCH03' else 0.24)"),
        ex("tp01_overall",
           f"(lambda p: {json.dumps(SAT)}[rnd.choices([4, 3], [52, 48])[0] if rnd.random() < p else rnd.choices([2, 1, 0], [40, 33, 27])[0]])"
           "({'Older persons & supported': 0.9, 'Social rent': 0.78, 'Affordable rent': 0.8, 'Shared ownership': 0.58}[tenure] - (0.2 if scheme_id == 'SCH03' else 0.08 if scheme_id == 'SCH01' else 0) + (0.12 if scheme_id == 'SCH14' else 0) + (0.008 if tsm_year == '2026/27' else 0) - (0.05 if complained_12m else 0))"),
        tsm_q("tp02_repairs", "had_repair_12m", 0.08),
        tsm_q("tp03_time_taken", "had_repair_12m", 0.3),
        tsm_q("tp04_well_maintained", LCRA, 0.12),
        tsm_q("tp05_safe_home", LCRA, 0.0, 0.25),
        tsm_q("tp06_listens_acts", "True", 0.35, 0, AGR),
        tsm_q("tp07_kept_informed", "True", 0.15, 0, AGR),
        tsm_q("tp08_fair_respect", "True", 0.0, 0.2, AGR),
        tsm_q("tp09_complaints", "complained_12m", 0.88),
        tsm_q("tp10_communal_areas", "scheme_id in ('SCH01', 'SCH02', 'SCH08', 'SCH10', 'SCH11', 'SCH12', 'SCH13', 'SCH14', 'SCH20', 'SCH21', 'SCH22', 'SCH24', 'SCH29') or rnd.random() < 0.2", 0.2),
        tsm_q("tp11_neighbourhood", "True", 0.3, 0, AGR),
        tsm_q("tp12_asb_approach", "rnd.random() < 0.55", 0.33),
        ex("comment", f"(choice({json.dumps(COMMENTS_POS)}) if tp01_overall in ('Very satisfied', 'Fairly satisfied') else choice({json.dumps(COMMENTS_NEG)})) if rnd.random() < 0.42 else None"),
    ],
}

# ---------------------------------------------------------------- static tables
suppliers = {
    "name": "suppliers", "title": "Contractors & Suppliers", "department": "finance", "system": "Northway Finance Cloud",
    "description": "Main contractors and suppliers with contract value, dates, contract manager and performance notes.",
    "columns": ["supplier_id", "supplier_name", "category", "annual_value_gbp", "contract_start", "contract_end", "contract_manager", "performance_rag", "notes"],
    "data": [
        ["SUP01", "Kentish Heating Services Ltd", "Gas servicing overflow (subcontract)", 186000, "2023-04-01", "2027-03-31", "P022", "Green", "Covers about a third of annual gas services."],
        ["SUP02", "Brightline Electrical Ltd", "EICR testing and electrical repairs overflow", 142000, "2024-06-01", "2027-05-31", "P023", "Amber", "Used more since March 2026 because of two electrician vacancies; invoices often lack job numbers."],
        ["SUP03", "Weald Roofing & Guttering Ltd", "Roofing and rainwater goods", 98000, "2022-09-01", "2026-12-31", "P008", "Amber", "Contract ends 31 Dec 2026; re-tender not yet started."],
        ["SUP04", "ClearFlow Drainage Ltd", "Drainage", 41000, "2023-01-01", "2027-12-31", "P008", "Green", ""],
        ["SUP05", "Castlemere Construction Ltd", "Orchard Fields main contractor (design & build)", 9850000, "2024-07-15", "2029-06-30", "P034", "Amber", "Phase 1 handed over Oct 2026 with 140+ open defects."],
        ["SUP06", "Fireguard Compliance Ltd", "Fire risk assessments and fire door surveys", 36000, "2024-04-01", "2027-03-31", "P022", "Green", ""],
        ["SUP07", "AquaSafe Water Hygiene Ltd", "Legionella risk assessments and monitoring", 22000, "2023-10-01", "2026-09-30", "P022", "Amber", "Contract expired 30 Sep 2026; running on an extension letter."],
        ["SUP08", "Liftwise Engineering Ltd", "Lift maintenance and LOLER inspections", 31000, "2025-01-01", "2027-12-31", "P022", "Red", "Repeated breakdowns at Rosemount Tower and Parkwood Court."],
        ["SUP09", "Asbestos Survey Partners Ltd", "Asbestos surveys and re-inspections", 27000, "2024-04-01", "2027-03-31", "P009", "Green", ""],
        ["SUP10", "FieldLoop Systems Ltd", "Repairs scheduling software", 58000, "2024-11-18", "2029-11-17", "P014", "Green", ""],
        ["SUP11", "Keystone Software Ltd", "Housing management system", 74000, "2019-04-01", "2027-03-31", "P014", "Amber", "Contract renewal decision due Dec 2026 (CRM project)."],
        ["SUP12", "Greenway Grounds Ltd", "Grounds maintenance", 88000, "2025-03-01", "2028-02-28", "P011", "Amber", "Resident complaints about missed grass cuts summer 2026."],
        ["SUP13", "Telecare Partners Ltd", "Careline monitoring centre", 46000, "2023-07-01", "2026-06-30", "P027", "Green", "Extended to 30 June 2027."],
        ["SUP14", "Hartwell Scaffolding Ltd", "Scaffolding hire", 39000, "2024-02-01", "2027-01-31", "P040", "Green", ""],
    ],
}
developments = {
    "name": "developments", "title": "Development Pipeline", "department": "development", "system": "Development appraisal model (Excel)",
    "description": "New-build schemes completed, on site and in the pipeline, with homes, tenure mix, cost, grant, contractor and status.",
    "columns": ["dev_id", "scheme", "location", "homes", "tenure_mix", "status", "start_on_site", "completion", "total_scheme_cost_gbp", "homes_england_grant_gbp", "contractor", "notes"],
    "data": [
        ["DEV01", "Orchard Fields phase 1", "Maidstone ME15", 62, "19 social rent / 25 affordable rent / 18 shared ownership", "Completed - letting", "2024-08-05", "2026-10-02", 14900000, 3100000, "Castlemere Construction Ltd", "First residents moved in Oct 2026; 44 let, 18 awaiting let."],
        ["DEV02", "Orchard Fields phase 2", "Maidstone ME15", 58, "20 social rent / 22 affordable rent / 16 shared ownership", "On site", "2025-11-03", "2027-09-30", 14400000, 3000000, "Castlemere Construction Ltd", "Two months behind programme after groundworks delay."],
        ["DEV03", "Orchard Fields phase 3 and community hub", "Maidstone ME15", 44, "Mix to be confirmed + community hub and 2 shops", "Planning approved", "2027-10-01", "2029-06-30", 12200000, 2400000, "Castlemere Construction Ltd", "Board decision on proceeding due Feb 2027."],
        ["DEV04", "Lenham Meadows phase 2", "Lenham ME17", 32, "20 affordable rent / 12 shared ownership", "Contract signed", "2027-01-11", "2028-03-31", 8100000, 1600000, "Oakbridge Homes Ltd", ""],
        ["DEV05", "Former Tovil depot", "Maidstone ME15", 26, "Social rent", "Feasibility", None, None, 7300000, 1900000, None, "Site purchase delayed by contamination survey."],
        ["DEV06", "Paddock Wood North (S106)", "Paddock Wood TN12", 20, "12 affordable rent / 8 shared ownership", "Exchanged", "2026-05-01", "2027-11-30", 4600000, 0, "Developer-led (S106)", "Section 106 acquisition from a private developer."],
        ["DEV07", "Hollingbourne Road garage sites", "Maidstone ME14", 9, "Social rent bungalows", "Feasibility", None, None, 2700000, 650000, None, "Residents' consultation on garage loss planned Jan 2027."],
    ],
}
risk = {
    "name": "risk_register", "title": "Strategic Risk Register", "department": "board", "system": "Excel (Governance)",
    "description": "Board-level strategic risks with owner, inherent and residual scores, controls and trend.",
    "columns": ["risk_id", "risk", "category", "owner", "inherent_score", "residual_score", "appetite", "trend", "key_controls", "last_reviewed"],
    "data": [
        ["SR01", "Failure to meet Awaab's Law timescales for damp and mould", "Compliance / Consumer", "P004", 20, 15, "Averse", "Rising", "Dedicated damp team; daily FieldLoop breach report; second surveyor recruited Sep 2025", "2026-10-14"],
        ["SR02", "Consumer standards: failure to move from C2 to C1", "Regulatory", "P001", 20, 12, "Averse", "Stable", "RSH action plan; monthly exec tracking; Customer Experience Committee oversight", "2026-10-14"],
        ["SR03", "Building safety failure (fire, gas, electrical, water, asbestos, lifts)", "Health & safety", "P004", 25, 10, "Averse", "Rising", "Assure360 tracking; external FRAs; BSR registration for Rosemount Tower", "2026-10-14"],
        ["SR04", "Loss of financial headroom (interest cover covenant)", "Financial", "P002", 16, 12, "Cautious", "Rising", "Monthly covenant forecast; stress testing; investment programme phasing", "2026-10-14"],
        ["SR05", "Rent arrears increase as Universal Credit migration completes", "Financial", "P011", 12, 9, "Cautious", "Rising", "Income team triage; APA requests; hardship fund", "2026-10-14"],
        ["SR06", "Inability to recruit and retain skilled trades", "People", "P005", 16, 12, "Open", "Rising", "Market supplement for electricians; apprenticeship scheme; subcontractor framework", "2026-10-14"],
        ["SR07", "Development cost overrun or contractor failure", "Development", "P010", 16, 9, "Cautious", "Stable", "Fixed-price D&B contracts; contractor financial checks; contingency 5%", "2026-10-14"],
        ["SR08", "Data breach or cyber attack", "Information", "P005", 20, 10, "Averse", "Stable", "MFA; Cyber Essentials Plus; phishing training; Copilot sensitivity labels pilot", "2026-10-14"],
        ["SR09", "Poor complaint handling leads to Ombudsman findings", "Consumer", "P003", 16, 12, "Averse", "Rising", "Complaint Handling Code self-assessment; weekly case review; extra officer", "2026-10-14"],
        ["SR10", "Stock condition data incomplete or out of date", "Assets", "P009", 12, 9, "Cautious", "Stable", "Rolling 20% survey programme; Power BI coverage dashboard", "2026-10-14"],
        ["SR11", "Net zero and EPC C by 2030 not affordable", "Assets", "P009", 12, 9, "Open", "Stable", "SHDF wave 3 bid; retrofit pilot at Coxheath Lane", "2026-07-15"],
        ["SR12", "IT system change (CRM / housing system) disrupts services", "Operational", "P005", 12, 8, "Cautious", "New", "Phased plan; data migration testing; business readiness group", "2026-10-14"],
    ],
}
months = [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13) if "2024-11" <= f"{y}-{m:02d}" <= "2026-10"]
monthly_income = {
    "name": "monthly_income", "title": "Monthly Rent Income & Arrears", "department": "finance", "system": "Keystone Housing / Northway Finance Cloud",
    "description": "Rent and service charges due and collected each month, collection rate and current tenant arrears at month end (as % of the annual rent debit).",
    "rows": len(months),
    "columns": [
        ex("month", f"{json.dumps(months)}[int(row.get('_i', 0))] if False else None"),
    ],
}
# monthly_income via explicit expr on a seq index
monthly_income["columns"] = [
    col("n", "seq", start=0),
    ex("month", f"{json.dumps(months)}[n]"),
    ex("rent_debit_gbp", "round(1059000 * (1.048 if month >= '2026-04' else 1.0) * (1 + 0.0012 * n) + rnd.uniform(-6000, 6000), 0)"),
    ex("collected_gbp", "round(rent_debit_gbp * (rnd.uniform(0.985, 1.005) - (0.012 if month in ('2025-04', '2026-04') else 0) + (0.02 if month in ('2025-03', '2026-03') else 0)), 0)"),
    ex("collection_rate", "round(collected_gbp / rent_debit_gbp, 4)"),
    ex("arrears_pct", "round(0.0206 + 0.00016 * n + rnd.uniform(-0.0006, 0.0006) + (0.0012 if month in ('2025-04', '2025-05', '2026-04', '2026-05') else 0), 4)"),
    ex("current_arrears_gbp", "round(arrears_pct * rent_debit_gbp * 12, 0)"),
    ex("uc_households", "int(452 + 3.9 * n + rnd.randint(-4, 4))"),
]

# ---------------------------------------------------------------- derived
TSM_Q = [("TP01", "tp01_overall", "Overall satisfaction", SAT), ("TP02", "tp02_repairs", "Satisfaction with repairs", SAT),
         ("TP03", "tp03_time_taken", "Satisfaction with time taken to complete most recent repair", SAT),
         ("TP04", "tp04_well_maintained", "Satisfaction that the home is well maintained", SAT),
         ("TP05", "tp05_safe_home", "Satisfaction that the home is safe", SAT),
         ("TP06", "tp06_listens_acts", "Agreement that the landlord listens to tenant views and acts upon them", AGR),
         ("TP07", "tp07_kept_informed", "Agreement that the landlord keeps tenants informed about things that matter to them", AGR),
         ("TP08", "tp08_fair_respect", "Agreement that the landlord treats tenants fairly and with respect", AGR),
         ("TP09", "tp09_complaints", "Satisfaction with the landlord's approach to handling complaints", SAT),
         ("TP10", "tp10_communal_areas", "Satisfaction that the landlord keeps communal areas clean and well maintained", SAT),
         ("TP11", "tp11_neighbourhood", "Agreement that the landlord makes a positive contribution to neighbourhoods", AGR),
         ("TP12", "tp12_asb_approach", "Satisfaction with the landlord's approach to handling anti-social behaviour", SAT)]
parts = []
for code, colname, label, lab in TSM_Q:
    pos = "('" + "', '".join(lab[3:]) + "')"
    parts.append(f"SELECT tsm_year, tenure_group, '{code}' AS measure_code, '{label.replace(chr(39), chr(39)*2)}' AS measure, COUNT({colname}) AS responses, "
                 f"ROUND(100.0 * SUM(CASE WHEN {colname} IN {pos} THEN 1 ELSE 0 END) / COUNT({colname}), 1) AS pct_positive "
                 f"FROM tsm_survey WHERE {colname} IS NOT NULL GROUP BY tsm_year, tenure_group")
tsm_results = {"name": "tsm_results", "title": "TSM Results by Year and Tenure", "department": "customer", "system": "Customer Voice survey platform",
               "description": "Tenant perception measures TP01-TP12: % satisfied (or agree) by year and tenure group (LCRA / LCHO), with number of responses.",
               "sql": " UNION ALL ".join(parts) + " ORDER BY 1, 2, 3"}
monthly_repairs = {
    "name": "monthly_repairs", "title": "Monthly Repairs Performance", "department": "repairs", "system": "FieldLoop",
    "description": "Repairs reported and completed each month, % completed in target by priority, and average days for routine repairs.",
    "sql": ("WITH c AS (SELECT substr(completed_date, 1, 7) AS month, * FROM repairs WHERE status = 'Completed') "
            "SELECT m.month, (SELECT COUNT(*) FROM repairs r WHERE substr(r.reported_date, 1, 7) = m.month) AS reported, COUNT(*) AS completed, "
            "ROUND(100.0 * AVG(in_target), 1) AS pct_in_target, "
            "ROUND(100.0 * AVG(CASE WHEN priority = 'Emergency' THEN in_target END), 1) AS emergency_pct, "
            "ROUND(100.0 * AVG(CASE WHEN priority = 'Urgent' THEN in_target END), 1) AS urgent_pct, "
            "ROUND(100.0 * AVG(CASE WHEN priority = 'Routine' THEN in_target END), 1) AS routine_pct, "
            "ROUND(AVG(CASE WHEN priority = 'Routine' THEN days_to_complete END), 1) AS routine_avg_days, "
            "ROUND(100.0 * AVG(first_time_fix), 1) AS first_time_fix_pct, ROUND(SUM(cost_gbp), 0) AS cost_gbp "
            "FROM (SELECT DISTINCT month FROM c WHERE month >= '2024-11' AND month <= '2026-10') m JOIN c USING (month) GROUP BY m.month ORDER BY m.month"),
}
scheme_summary = {
    "name": "scheme_summary", "title": "Scheme Performance Summary", "department": "assets", "system": "Power BI dataset",
    "description": "One row per scheme: homes, repairs and open/overdue repairs (last 12 months), damp cases, complaints, arrears and TSM overall satisfaction.",
    "sql": ("SELECT s.scheme_id, s.scheme_name, s.scheme_type, s.local_authority, s.homes, "
            "(SELECT COUNT(*) FROM repairs r WHERE r.scheme_id = s.scheme_id AND r.reported_date >= '2025-11-05') AS repairs_12m, "
            "(SELECT COUNT(*) FROM repairs r WHERE r.scheme_id = s.scheme_id AND r.status NOT IN ('Completed', 'Cancelled')) AS open_repairs, "
            "(SELECT COUNT(*) FROM repairs r WHERE r.scheme_id = s.scheme_id AND r.overdue = 1) AS overdue_repairs, "
            "(SELECT COUNT(*) FROM damp_mould_cases m WHERE m.scheme_id = s.scheme_id AND m.reported_date >= '2025-11-05') AS damp_cases_12m, "
            "(SELECT COUNT(*) FROM damp_mould_cases m WHERE m.scheme_id = s.scheme_id AND m.status != 'Closed') AS open_damp_cases, "
            "(SELECT COUNT(*) FROM complaints c WHERE c.scheme_id = s.scheme_id AND c.received_date >= '2025-11-05') AS complaints_12m, "
            "(SELECT ROUND(SUM(balance_gbp), 0) FROM rent_accounts a WHERE a.scheme_id = s.scheme_id AND a.balance_gbp > 0) AS arrears_gbp, "
            "(SELECT ROUND(100.0 * AVG(CASE WHEN tp01_overall IN ('Very satisfied', 'Fairly satisfied') THEN 1.0 ELSE 0 END), 1) FROM tsm_survey t WHERE t.scheme_id = s.scheme_id) AS tsm_overall_pct, "
            "(SELECT COUNT(*) FROM tsm_survey t WHERE t.scheme_id = s.scheme_id) AS tsm_responses "
            "FROM schemes s ORDER BY s.scheme_id"),
}

post_sql = [
    # open/cancelled jobs carry no completion date
    "UPDATE repairs SET completed_date = NULL WHERE status != 'Completed'",
    # properties that are empty now
    "UPDATE properties SET status = 'Void' WHERE uprn IN (SELECT uprn FROM voids WHERE status != 'Let')",
    # tenancy start = latest relet date
    "UPDATE tenancies SET start_date = (SELECT MAX(let_date) FROM voids v WHERE v.uprn = tenancies.uprn AND v.status = 'Let') WHERE EXISTS (SELECT 1 FROM voids v WHERE v.uprn = tenancies.uprn AND v.status = 'Let')",
    "UPDATE tenancies SET tenancy_type = 'Starter (12 months)' WHERE tenancy_type = 'Assured' AND tenure IN ('Social rent', 'Affordable rent') AND start_date >= '2025-11-05'",
    # three non-decent homes at Brenchley Gardens with open damp cases
    "UPDATE properties SET decent_homes = 'No - serious hazard (damp and mould)' WHERE uprn IN (SELECT uprn FROM damp_mould_cases WHERE scheme_id = 'SCH03' AND status != 'Closed' ORDER BY case_id LIMIT 2)",
    "UPDATE properties SET decent_homes = 'No - disrepair (roof)' WHERE uprn = (SELECT uprn FROM properties WHERE scheme_id = 'SCH03' AND property_type = 'House' AND decent_homes = 'Yes' AND tenure = 'Social rent' ORDER BY uprn LIMIT 1 OFFSET 40)",
    # one overdue gas check (no access)
    "UPDATE compliance_checks SET last_completed = '2025-10-29', next_due = '2026-10-29', status = 'Overdue', no_access_attempts = 4 WHERE check_id = (SELECT check_id FROM compliance_checks WHERE check_type LIKE 'Gas%' AND scheme_id = 'SCH06' ORDER BY check_id LIMIT 1 OFFSET 7)",
    # building safety plants
    "UPDATE building_safety SET last_completed = '2025-08-20', next_due = '2026-08-20', status = 'Overdue', risk_rating = 'Moderate', open_actions = 5, overdue_actions = 2 WHERE scheme_id = 'SCH21' AND check_type = 'Fire risk assessment'",
    "UPDATE building_safety SET risk_rating = 'Moderate', open_actions = 11, overdue_actions = 3, last_completed = '2026-03-12', next_due = '2027-03-12', status = 'Compliant' WHERE scheme_id = 'SCH01' AND check_type = 'Fire risk assessment'",
    "UPDATE building_safety SET open_actions = 9, overdue_actions = 4 WHERE scheme_id = 'SCH01' AND check_type = 'Communal fire door inspection'",
    "UPDATE building_safety SET last_completed = '2026-03-30', next_due = '2026-09-28', status = 'Overdue' WHERE scheme_id = 'SCH02' AND check_type = 'Lift thorough examination (LOLER)'",
    "UPDATE building_safety SET overdue_actions = 0 WHERE overdue_actions IS NULL",
    # month-end arrears for the latest month = the live rent accounts
    "UPDATE monthly_income SET current_arrears_gbp = (SELECT ROUND(SUM(balance_gbp), 0) FROM rent_accounts WHERE balance_gbp > 0 AND tenure NOT IN ('Leasehold', 'Shared ownership')) WHERE month = '2026-10'",
    "UPDATE monthly_income SET uc_households = (SELECT COUNT(*) FROM tenancies WHERE universal_credit = 1) WHERE month = '2026-10'",
    "UPDATE monthly_income SET arrears_pct = ROUND(current_arrears_gbp / (rent_debit_gbp * 12), 4) WHERE month = '2026-10'",
]

spec = {
    "seed": 2005, "locale": "en_GB",
    "tables": [schemes, properties, employees, voids, tenancies, rent_accounts, repairs, damp, complaints, asb, compliance,
               building_safety, tsm, suppliers, developments, risk, monthly_income],
    "derived": [tsm_results, monthly_repairs, scheme_summary],
    "post_sql": post_sql,
}
with open(OUT, "w", encoding="utf-8", newline="\r\n") as f:
    json.dump(spec, f, ensure_ascii=False, indent=2)
print("written", OUT)
