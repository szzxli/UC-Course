#!/usr/bin/env python3
"""Scrape UCSB 2026-2027 catalog via the public CourseDog API behind
catalog.ucsb.edu (legacy my.sa.ucsb.edu catalog ends at 2022-2023 and
redirects to CourseDog). Endpoints: /api/v1/catalogs/urls?url=catalog.ucsb.edu
and /api/v1/cm/ucsb/courses/search/<q>?catalogId=...; headers X-Requested-With:
catalog + Origin: https://catalog.ucsb.edu (as the site's frontend sends).
Polite single process, ~2.75s between requests. Output mirrors UCI/UCSD layout.
"""
import re, json, time, html, sys, os, math, subprocess, urllib.parse

BASE = "/home/hatch/workspace/uc-course"
RAW = f"{BASE}/data/raw"
WEBRAW = f"{BASE}/web/data/raw"
WEBSEARCH = f"{BASE}/web/data/search/ucsb"
API = "https://app.coursedog.com/api/v1"
UA_STR = "Mozilla/5.0 (compatible; UCCoursePlanner/0.1; research project)"
SLEEP = 2.75
SHARD = 200          # courses per raw shard (UCI ~216, UCSD ~168)
SEARCH_CHUNK = 625   # courses per web search chunk (UCI/UCSD ~625)
CATALOG_YEAR_RANGE = "2026-09-24,2027-06-30"  # 2026-2027 academic year

errors = []

def fetch_json(url, tries=4):
    # curl, not urllib: the MITM proxy truncates urllib responses.
    last = None
    for i in range(tries):
        try:
            out = subprocess.run(
                ["curl", "-k", "-s", "--max-time", "120",
                 "-H", "X-Requested-With: catalog",
                 "-H", "Origin: https://catalog.ucsb.edu",
                 "-A", UA_STR, url],
                capture_output=True, timeout=150)
            return json.loads(out.stdout.decode("utf-8", errors="replace"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (i + 1))
    errors.append(f"FETCH FAIL {url}: {last}")
    raise last

def clean(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()

# ---- field conversion ----

def fmt_units(rec):
    cr = rec.get("credits") or {}
    ch = cr.get("creditHours") or {}
    def num(x):
        if x is None:
            return None
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    mn, mx = ch.get("min"), ch.get("max")
    if mn is not None and mx is not None and float(mx) != float(mn):
        return f"{num(mn)}-{num(mx)}"
    if mn is not None:
        return num(mn)
    if cr.get("numberOfCredits") is not None:
        return num(cr["numberOfCredits"])
    return ""

def make_prereq_parser(subjects, aliases, catalog_codes):
    """Parse course refs from freeform requisite text: explicit codes,
    department full names (aliases), bare numbers inheriting the last
    subject. Alias/bare resolutions kept only if the code exists."""
    alt = "|".join(re.escape(s) for s in sorted(subjects, key=len, reverse=True))
    code_rx = re.compile(r"(?<![A-Z])(" + alt + r")\s+(\d{1,3}[A-Z]{0,3})(?![A-Z0-9])")
    aalt = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
    alias_rx = re.compile(r"(?<![A-Za-z])(" + aalt + r")\s+(\d{1,3}[A-Z]{0,3})(?![A-Z0-9])") if aalt else None
    bare_rx = re.compile(r"(?<![\dA-Za-z])(\d{1,3}[A-Z]{0,3})(?![\dA-Za-z])")
    skip_next = {"units", "unit", "gpa", "grade", "percent", "%", "points", "point",
                 "quarters", "quarter", "years", "year", "hours", "hour"}

    def parse(raw, self_code):
        raw = raw or ""
        events = []  # (pos, subject, number, explicit)
        for m in code_rx.finditer(raw):
            events.append((m.start(), m.group(1), m.group(2), True))
        if alias_rx:
            for m in alias_rx.finditer(raw):
                events.append((m.start(), aliases[m.group(1)], m.group(2), False))
        events.sort()
        out, cur = [], None
        consumed = [(m.start(), m.end()) for m in code_rx.finditer(raw)]
        if alias_rx:
            consumed += [(m.start(), m.end()) for m in alias_rx.finditer(raw)]
        for _, subj, num, explicit in events:
            cur = subj
            c = f"{subj} {num}"
            if c == self_code:
                continue
            if explicit or c in catalog_codes:
                if c not in out:
                    out.append(c)
        # bare numbers inheriting the current subject, in text order
        if events:
            subj, ei = None, 0
            for m in bare_rx.finditer(raw):
                while ei < len(events) and events[ei][0] < m.start():
                    subj = events[ei][1]
                    ei += 1
                if subj is None:
                    continue
                if any(s <= m.start() < e for s, e in consumed):
                    continue
                nxt = re.match(r"\s*([A-Za-z%]+)", raw[m.end():m.end() + 12])
                if nxt and nxt.group(1).lower() in skip_next:
                    continue
                c = f"{subj} {m.group(1)}"
                if c == self_code or c in out:
                    continue
                if c in catalog_codes:
                    out.append(c)
        return out
    return parse

def convert(rec, parse_prereqs):
    subj = (rec.get("subjectCode") or "").strip()
    number = (rec.get("courseNumber") or "").strip()
    code = f"{subj} {number}"
    title = clean(rec.get("longName") or rec.get("name") or "")
    desc = clean(rec.get("description") or "")
    req = rec.get("requisites") or {}
    ff = (req.get("requisitesFreeform") or {}).get("value") or ""
    praw = clean(ff)
    if praw.lower() == "none":
        praw = ""
    return {
        "campus": "UCSB",
        "dept": subj,
        "code": code,
        "title": title,
        "units": fmt_units(rec),
        "description": desc,
        "prerequisites_raw": praw,
        "prerequisites_courses": parse_prereqs(praw, code),
    }

def sort_key(c):
    m = re.match(r"^(.*?) (\d+)(.*)$", c["code"])
    if m:
        return (c["dept"], int(m.group(2)), m.group(3), c["code"])
    return (c["dept"], 0, "", c["code"])

# ---- main ----

def main():
    t0 = time.time()
    meta = fetch_json(f"{API}/catalogs/urls?url=catalog.ucsb.edu")
    school = meta["school"]
    catalog = meta["catalog"]
    cat_id = catalog["_id"]
    print(f"school={school} catalog={catalog['displayName']} id={cat_id}")
    time.sleep(SLEEP)

    # enumerate all courses in the catalog (blank query, paged)
    recs, skip = [], 0
    total = None
    while total is None or skip < total:
        q = urllib.parse.quote(" ")
        url = (f"{API}/cm/{school}/courses/search/{q}?catalogId={cat_id}"
               f"&skip={skip}&limit=1000&effectiveDatesRange={CATALOG_YEAR_RANGE}")
        page = fetch_json(url)
        total = page["listLength"]
        recs.extend(page["data"])
        print(f"  page skip={skip}: +{len(page['data'])} (total {len(recs)}/{total})")
        skip += 1000
        time.sleep(SLEEP)

    # dedupe: one revision per courseGroupId (prefer dated, latest, highest version)
    best = {}
    for r in recs:
        g = r["courseGroupId"]
        score = (r.get("effectiveStartDate") is not None, r.get("effectiveStartDate") or "",
                 r.get("version") or 0, r.get("lastEditedAt") or 0)
        if g not in best or score > best[g][0]:
            best[g] = (score, r)
    uniq = [v[1] for v in best.values()]
    print(f"records {len(recs)} -> distinct course groups {len(uniq)}")

    subjects = sorted({(r.get("subjectCode") or "").strip() for r in uniq} - {""})
    catalog_codes = {f"{(r.get('subjectCode') or '').strip()} {(r.get('courseNumber') or '').strip()}"
                     for r in uniq}

    # department full-name aliases (UCSB requisite texts often use names, not codes)
    dept_ids = sorted({d for r in uniq for d in (r.get("departments") or [])})
    depts = {}
    for did in dept_ids:
        try:
            depts[did] = fetch_json(f"{API}/ucsb/departments/{urllib.parse.quote(did)}")
        except Exception:  # noqa: BLE001
            errors.append(f"dept fetch failed: {did}")
        time.sleep(SLEEP)
    print(f"departments fetched: {len(depts)}/{len(dept_ids)}")

    subj_counts = {}
    for r in uniq:
        s = (r.get("subjectCode") or "").strip()
        subj_counts[s] = subj_counts.get(s, 0) + 1

    def primary_subject(dinfo):
        # subject with most catalog courses (dept id != live subject, e.g. FLMST->FAMST)
        subs = [s.strip() for s in (dinfo.get("subjectCodes") or [])]
        if not subs:
            return dinfo.get("_id")
        return max(subs, key=lambda s: subj_counts.get(s, 0))

    stop = {"and", "&", "of", "the"}
    def tokens(s):
        return {t for t in re.split(r"[^A-Za-z]+", s.lower()) if t and t not in stop}
    def phrase_matches(phrase, dname):
        pt, dt = tokens(phrase), tokens(dname)
        if not pt:
            return False
        return all(any(d.startswith(p) and len(p) >= 3 for d in dt) for p in pt)

    aliases = {}
    def add_alias(phrase, subj):
        phrase = re.sub(r"\s+", " ", phrase).strip()
        if phrase and subj and phrase not in aliases:
            aliases[phrase] = subj
    for did, dinfo in depts.items():
        subj = primary_subject(dinfo)
        for nm in {dinfo.get("displayName") or "", dinfo.get("name") or ""}:
            if nm:
                add_alias(nm, subj)
                add_alias(nm.replace(" & ", " and "), subj)
    # mine name phrases actually used in requisite texts, map by token-subset
    phrase_count = {}
    for r in uniq:
        ff = ((r.get("requisites") or {}).get("requisitesFreeform") or {}).get("value") or ""
        t = clean(ff)
        for m in re.finditer(r"([A-Z][A-Za-z&.'-]+(?: [A-Z][A-Za-z&.'-]+){0,3}) (\d{1,3}[A-Z]{0,3})\b", t):
            phrase_count[m.group(1)] = phrase_count.get(m.group(1), 0) + 1
    all_texts = [clean(((r.get("requisites") or {}).get("requisitesFreeform") or {}).get("value") or "")
                 for r in uniq]
    mined = 0
    for phrase, cnt in phrase_count.items():
        if cnt < 3 or phrase in aliases:
            continue
        hits = [d for d in depts.values()
                if phrase_matches(phrase, d.get("displayName") or "") or
                   phrase_matches(phrase, d.get("name") or "")]
        if len(hits) == 1:
            subj = primary_subject(hits[0])
            # keep only if a real reference resolves to a catalog course
            rx = re.compile(re.escape(phrase) + r"\s+(\d{1,3}[A-Z]{0,3})(?![A-Z0-9])")
            if any(f"{subj} {m.group(1)}" in catalog_codes
                   for t in all_texts for m in rx.finditer(t)):
                aliases[phrase] = subj
                mined += 1
    print(f"prereq aliases: {len(aliases)} ({mined} mined from texts)")

    parse_prereqs = make_prereq_parser(subjects, aliases, catalog_codes)
    courses = sorted((convert(r, parse_prereqs) for r in uniq), key=sort_key)
    n = len(courses)
    n_pre = sum(1 for c in courses if c["prerequisites_courses"])
    print(f"courses: {n}, subjects: {len(subjects)}, with parsed prereqs: {n_pre}")

    # 1. full file + raw shards (data/raw + web/data/raw)
    with open(f"{RAW}/ucsb-courses.json", "w") as f:
        json.dump(courses, f, ensure_ascii=False, indent=1)
    shards = []
    for i in range(0, n, SHARD):
        fn = f"ucsb-p{len(shards) + 1:02d}.json"
        chunk = courses[i:i + SHARD]
        for d in (RAW, WEBRAW):
            with open(f"{d}/{fn}", "w") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=1)
        shards.append(fn)
    print(f"shards: {len(shards)} x ~{SHARD}")

    # 2. raw index (data/raw only, mirroring UCI/UCSD)
    for p in (f"{RAW}/index.json",):
        idx = json.load(open(p))
        idx["ucsb"] = shards
        tc = idx.get("total_courses") or {}
        tc["ucsb"] = n
        idx["total_courses"] = tc
        # stable key order: campus lists, totals, schema
        ordered = {}
        for k in ("uci", "ucsd", "ucsb"):
            if k in idx:
                ordered[k] = idx[k]
        ordered["total_courses"] = {k: tc[k] for k in ("uci", "ucsd", "ucsb") if k in tc}
        ordered["schema"] = idx["schema"]
        with open(p, "w") as f:
            json.dump(ordered, f, ensure_ascii=False, indent=1)

    # 3. search entries
    entries = []
    for j, c in enumerate(courses):
        entries.append({"code": c["code"], "t": c["title"], "u": c["units"], "d": c["dept"],
                        "c": "UCSB", "f": shards[j // SHARD],
                        "pre": c["prerequisites_courses"]})
    with open(f"{RAW}/search-ucsb.json", "w") as f:
        json.dump(entries, f, ensure_ascii=False)
    si = json.load(open(f"{RAW}/search-index.json"))
    si = [e for e in si if e.get("c") != "UCSB"] + entries
    with open(f"{RAW}/search-index.json", "w") as f:
        json.dump(si, f, ensure_ascii=False)

    # 4. web search chunks
    os.makedirs(WEBSEARCH, exist_ok=True)
    files = []
    for i in range(0, n, SEARCH_CHUNK):
        fn = f"idx-p{len(files) + 1:02d}.json"
        with open(f"{WEBSEARCH}/{fn}", "w") as f:
            json.dump(entries[i:i + SEARCH_CHUNK], f, ensure_ascii=False)
        files.append(fn)
    with open(f"{WEBSEARCH}/manifest.json", "w") as f:
        json.dump({"files": files, "count": n}, f)
    print(f"web search chunks: {len(files)}")

    # 5. logs (same style as existing scrape-* logs)
    if errors:
        with open(f"{RAW}/scrape-ucsb-errors.log", "w") as f:
            f.write("\n".join(errors) + "\n")
    with open(f"{RAW}/scrape-ucsb-log.md", "w") as f:
        f.write("# UCSB Course Catalog Scrape Log\n\n")
        f.write(f"Date: 2026-10-23. Method: polite single-process, ~{SLEEP}s between requests, "
                "CourseDog public catalog API (catalog.ucsb.edu).\n\n")
        f.write(f"Catalog: {catalog['displayName']} (id {cat_id}), school slug \"{school}\".\n\n")
        f.write("## Totals\n\n| Campus | Courses | Depts/Subjects | With parsed prereqs |\n"
                "|---|---|---|---|\n")
        f.write(f"| UCSB | {n} | {len(subjects)} | {n_pre} |\n\n")
        f.write("Output: `ucsb-courses.json` + `ucsb-pNN.json` shards "
                "(fields: campus, dept, code, title, units, description, "
                "prerequisites_raw, prerequisites_courses).\n\n")
        f.write("Notes:\n"
                "- Legacy my.sa.ucsb.edu/catalog only publishes up to 2022-2023 and "
                "/Current/ redirects to CourseDog, so the current catalog was taken "
                "from the CourseDog API that powers catalog.ucsb.edu.\n"
                "- One record per courseGroupId (newest effective revision kept); "
                "course codes normalized to \"SUBJECT NUMBER\" (e.g. \"POL S 1\", \"ANTH W 3\").\n"
                "- Titles use the catalog longName when present; units from creditHours "
                "(min-max when a range is given).\n"
                "- prerequisites_raw is the catalog's freeform requisite text "
                "(\"None\" normalized to empty). prerequisites_courses parsed from it "
                "three ways: explicit subject codes (159 UCSB subjects), department "
                "full-name aliases validated against the catalog (e.g. \"Anthropology 3\" "
                "-> ANTH 3, \"Film Studies 46\" -> FAMST 46), and bare numbers inheriting "
                "the last-mentioned subject (alias/bare resolutions kept only when the "
                "code exists in the catalog).\n")
    print(f"done in {time.time() - t0:.0f}s, errors: {len(errors)}")

if __name__ == "__main__":
    main()
