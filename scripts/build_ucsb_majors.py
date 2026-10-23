#!/usr/bin/env python3
"""Build UCSB major requirement files from the official 2026-2027 catalog.

Source: CourseDog public catalog API (catalog.ucsb.edu) — the same API the
catalog website uses. Each program's `requisites.requisitesSimple` blocks are
fully structured (conditions: completedAllOf / completedAnyOf /
completedAtLeastXOf / anyOf / allOf / minimumCredits /
completeVariableCoursesAndVariableCredits / freeformText) and are converted
to this repo's majors schema:
  required  = complete-all rules (+ choose-one areas, UCSD-biology parity)
  elective  = pick-from-list / minimum-credit rules
  prereq    = rules inside PRE-MAJOR / PREPARATION blocks
Value entries that are 20+ char ids are courseGroupId references and are
resolved through the courses $filters endpoint. Entries whose value
condition is "courseSets" reference catalog course sets that the public API
does not expand; those requirements are emitted with an explanatory note and
no invented courses (counted in the final report).

Polite: single process, ~2.75s between requests.
"""
import re, json, time, html, os, subprocess, urllib.parse

BASE = "/home/hatch/workspace/uc-course"
MAJ = f"{BASE}/data/majors"
WEBMAJ = f"{BASE}/web/data/majors"
API = "https://app.coursedog.com/api/v1"
UA_STR = "Mozilla/5.0 (compatible; UCCoursePlanner/0.1; research project)"
SLEEP = 2.75
CATALOG_ID = "friXFQMHuLvLoBthCmmV"  # 2026-2027 General Catalog (resolved by scrape_ucsb.py)
RANGE = "2026-09-24,2027-06-30"
CHECKED = "2026-10-23"

# slug -> (programGroupId, expected program name, index display order)
PROGRAMS = [
    ("computer-science",       "BSCMPSC", "Computer Science"),
    ("electrical-engineering", "BSEE",    "Electrical Engineering"),
    ("biology",                "BSBIOSC", "Biological Sciences"),
    ("psychology",             "BSPBS",   "Psychological & Brain Sciences"),
    ("economics",              "BAECON",  "Economics"),
    ("mathematics",            "BSMATH",  "Mathematics"),
]
DEGREE_MAP = {"Bachelor of Science": "B.S.", "Bachelor of Arts": "B.A."}
IDISH = re.compile(r"^[A-Za-z0-9_-]{18,}$")
CODEISH = re.compile(r"^[A-Z][A-Z &]{0,9} \d")  # real codes are "SUBJECT NUMBER" (with space)

errors = []
unresolved_sets = []

def fetch_json(url, tries=4):
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

def slugify(s, used):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "req").lower()).strip("-") or "req"
    base, i = s, 2
    while s in used:
        s = f"{base}-{i}"
        i += 1
    used.add(s)
    return s

# ---------- requisite conversion ----------

class Ctx:
    def __init__(self, resolve):
        self.resolve = resolve      # id -> code string or None
        self.pending_notes = []     # narrative/freeform notes waiting for a requirement

    def resolve_entry(self, entry):
        """One value entry -> list of course codes (resolving group ids)."""
        codes = []
        for v in entry.get("value") or []:
            if " " not in v and IDISH.match(v):
                # id reference (course group or course set), never a course code
                code = self.resolve(v)
                if code:
                    codes.append(code)
                else:
                    unresolved_sets.append(v)
            elif CODEISH.match(v):
                codes.append(re.sub(r"\s+", " ", v).strip())
            else:
                codes.append(v)
        return codes

    def convert_rule(self, rule, block_name, block_type, used_ids):
        """-> list of requirement dicts (0..n)."""
        cond = rule.get("condition")
        name = clean(rule.get("name") or "") or block_name
        notes = list(self.pending_notes)
        self.pending_notes = []
        if rule.get("notes"):
            notes.append(clean(rule["notes"]))
        if rule.get("description"):
            notes.append(clean(rule["description"]))
        is_prep = (block_type == "Prerequisite" or
                   re.search(r"PRE[- ]?MAJOR|PREPARATION", block_name or "", re.I))

        if cond == "freeformText":
            txt = clean(rule.get("value") or "")
            if txt:
                self.pending_notes.append(txt)
            return []

        if rule.get("subRules"):
            subs = rule["subRules"]
            if cond == "anyOf":
                # choose one path among sub-rules
                opts, union = [], []
                for sr in subs:
                    sub_reqs = self.convert_rule(sr, block_name, block_type, used_ids)
                    sc = []
                    for rq in sub_reqs:
                        sc.extend(rq["courses"])
                    if sc:
                        opts.append(sc)
                        union.extend(sc)
                if not union:
                    return []
                return [{"id": slugify(name, used_ids), "name": name,
                         "type": "prereq" if is_prep else "required",
                         "courses": sorted(set(union), key=natural_key),
                         "note": " ".join(notes), "options": opts}]
            # allOf (or other): each sub-rule becomes its own requirement
            out = []
            for sr in subs:
                out.extend(self.convert_rule(sr, block_name, block_type, used_ids))
            if notes and out:
                out[0]["note"] = " ".join(notes + ([out[0]["note"]] if out[0]["note"] else []))
            return out

        value = rule.get("value") or {}
        vcond = value.get("condition")
        entries = [self.resolve_entry(e) for e in (value.get("values") or [])]
        entries = [e for e in entries if e]
        union = sorted({c for e in entries for c in e}, key=natural_key)

        if vcond == "courseSets":
            notes.append("Course list is defined as a catalog course set; "
                         "see the official program page for the courses in this area.")
        if rule.get("credits"):
            notes.insert(0, f"Minimum {rule['credits']} units.")
        if cond == "completedAtLeastXOf" and rule.get("restriction"):
            notes.insert(0, f"Complete {rule['restriction']} of the following.")
        if cond == "completedAnyOf":
            notes.insert(0, "Complete one of the following.")
        if cond == "completeVariableCoursesAndVariableCredits":
            notes.insert(0, "Complete a variable number of courses/units from the following list.")

        if cond == "completedAllOf":
            rtype = "prereq" if is_prep else "required"
            opts = [e for e in entries if len(e) > 1]
            req = {"id": slugify(name, used_ids), "name": name, "type": rtype,
                   "courses": union, "note": " ".join(n for n in notes if n),
                   "options": opts}
            return [req] if union or notes else []
        if cond in ("completedAnyOf",):
            rtype = "prereq" if is_prep else "required"
            req = {"id": slugify(name, used_ids), "name": name, "type": rtype,
                   "courses": union, "note": " ".join(n for n in notes if n),
                   "options": entries}
            return [req] if union else []
        if cond in ("completedAtLeastXOf", "completeVariableCoursesAndVariableCredits",
                    "minimumCredits", "anyOf", "allOf"):
            if cond == "completedAtLeastXOf" and rule.get("restriction") == 1 and not is_prep:
                rtype = "required"
            else:
                rtype = "prereq" if is_prep else "elective"
            req = {"id": slugify(name, used_ids), "name": name, "type": rtype,
                   "courses": union, "note": " ".join(n for n in notes if n),
                   "options": entries if len(entries) > 1 else []}
            return [req] if union or notes else []
        # unknown condition: keep the courses, mark required, log it
        errors.append(f"unknown rule condition {cond} in {block_name}/{name}")
        req = {"id": slugify(name, used_ids), "name": name,
               "type": "prereq" if is_prep else "required",
               "courses": union, "note": " ".join(n for n in notes if n),
               "options": []}
        return [req] if union else []

def natural_key(code):
    m = re.match(r"^(.*?) (\d+)(.*)$", code)
    if m:
        return (m.group(1), int(m.group(2)), m.group(3))
    return (code, 0, "")

def convert_program(prog, resolve):
    ctx = Ctx(resolve)
    used_ids = set()
    reqs = []
    blocks = (prog.get("requisites") or {}).get("requisitesSimple") or []
    for b in blocks:
        bname = clean(b.get("name") or "")
        if b.get("notes"):
            ctx.pending_notes.append(clean(b["notes"]))
        if b.get("type") == "Narrative Text":
            continue
        for r in b.get("rules") or []:
            reqs.extend(ctx.convert_rule(r, bname, b.get("type"), used_ids))
    # trailing narrative notes: attach to last requirement
    if ctx.pending_notes and reqs:
        extra = " ".join(ctx.pending_notes)
        reqs[-1]["note"] = (reqs[-1]["note"] + " " + extra).strip()
    # drop empty note/options keys to match existing file style
    for rq in reqs:
        if not rq["note"]:
            del rq["note"]
        if not rq["options"]:
            del rq["options"]
    return reqs

# ---------- main ----------

def main():
    # 1. fetch all six programs
    progs = {}
    for slug, gid, expect in PROGRAMS:
        url = (f"{API}/cm/ucsb/programs?programGroupIds={gid}"
               f"&effectiveDatesRange={RANGE}&formatDependents=true")
        d = fetch_json(url)
        p = list(d.values())[0]
        assert expect in p["name"], f"{gid}: unexpected program {p['name']}"
        assert p.get("status") == "Active", f"{gid}: not Active"
        progs[slug] = (gid, p)
        print(f"fetched {p['name'].strip()} ({gid})")
        time.sleep(SLEEP)

    # 2. collect + resolve courseGroupId references in values
    refs = set()
    def scan(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
        elif isinstance(obj, str) and IDISH.match(obj) and not CODEISH.match(obj):
            refs.add(obj)
    for _, p in progs.values():
        scan((p.get("requisites") or {}).get("requisitesSimple") or [])
    # course set ids also look like ids; resolution attempt covers both:
    # courseGroupIds resolve to courses; courseSets simply won't resolve.
    resolved = {}
    if refs:
        qs = "&".join(f"courseGroupIds={urllib.parse.quote(r)}" for r in sorted(refs))
        url = (f"{API}/cm/ucsb/courses/search/%24filters?{qs}"
               f"&effectiveDatesRange={RANGE}&skip=0&limit=500")
        d = fetch_json(url)
        for r in d.get("data") or []:
            code = f"{(r.get('subjectCode') or '').strip()} {(r.get('courseNumber') or '').strip()}"
            resolved[r["courseGroupId"]] = code
        print(f"id refs: {len(refs)}, resolved to courses: {len(resolved)}")
        time.sleep(SLEEP)
    resolve = lambda i: resolved.get(i)  # noqa: E731

    # 3. department display names for the `department` field
    dept_names = {}
    dept_ids = sorted({d for _, p in progs.values() for d in (p.get("departments") or [])})
    for did in dept_ids:
        try:
            info = fetch_json(f"{API}/ucsb/departments/{urllib.parse.quote(did)}")
            dept_names[did] = info.get("displayName") or info.get("name") or did
        except Exception:  # noqa: BLE001
            dept_names[did] = did
        time.sleep(SLEEP)

    # 4. build files + index
    idx_path = f"{MAJ}/index.json"
    index = json.load(open(idx_path))
    index = [e for e in index if e.get("campus") != "UCSB"]
    for slug, gid, expect in PROGRAMS:
        _, p = progs[slug]
        reqs = convert_program(p, resolve)
        major_name = re.sub(r"\s+-\s+(BS|BA|B\.S\.|B\.A\.).*$", "", p["name"]).strip()
        major_name = major_name.replace(" & ", " & ")
        degree = DEGREE_MAP.get(p.get("degreeDesignation") or "", "")
        dept_label = "; ".join(
            (dn if dn.lower().startswith("department") else f"Department of {dn}")
            for dn in (dept_names.get(d, d) for d in (p.get("departments") or [])))
        doc = {
            "campus": "UCSB",
            "major": major_name,
            "degree": degree,
            "department": dept_label,
            "school": p.get("college") or "",
            "source_url": f"https://catalog.ucsb.edu/programs/{gid}",
            "checked": CHECKED,
            "requirements": reqs,
        }
        fn = f"ucsb-{slug}.json"
        for d in (MAJ, WEBMAJ):
            with open(f"{d}/{fn}", "w") as f:
                json.dump(doc, f, ensure_ascii=False, indent=1)
        index.append({"campus": "UCSB", "major": major_name, "degree": degree,
                      "file": fn, "requirement_count": len(reqs)})
        print(f"{fn}: {major_name} {degree}, {len(reqs)} requirements, "
              f"{sum(len(r['courses']) for r in reqs)} course refs")
    for d in (MAJ, WEBMAJ):
        with open(f"{d}/index.json", "w") as f:
            json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"index entries: {len(index)}")
    if unresolved_sets:
        print(f"UNRESOLVED course-set refs ({len(set(unresolved_sets))}): "
              f"{sorted(set(unresolved_sets))}")
    if errors:
        print("ERRORS:", errors)

if __name__ == "__main__":
    main()
