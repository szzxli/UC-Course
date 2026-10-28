#!/usr/bin/env python3
"""Build ONE UCSB major file (Environmental Studies, B.S.) from the official
2026-2027 catalog, reusing scripts/build_ucsb_majors.py conversion logic.

Why a separate script: build_ucsb_majors.main() rebuilds the whole UCSB index
from its hardcoded 6-program list; running it would drop/rewrite the other
six UCSB majors. This script fetches only BSENVST, writes
data/majors/ucsb-environmental-science.json + web copy, and APPENDS one
index entry to both index.json files (idempotent on re-run).

Source: CourseDog public catalog API (catalog.ucsb.edu), same as the 6
existing UCSB majors. Polite: ~2.75s between requests.
"""
import sys, json, re, time, urllib.parse

sys.path.insert(0, "/home/hatch/workspace/uc-course/scripts")
import build_ucsb_majors as B

SLUG, GID, EXPECT = "environmental-science", "BSENVST", "Environmental Studies"
CHECKED = "2026-10-27"
MAJ, WEBMAJ = B.MAJ, B.WEBMAJ


def main():
    url = (f"{B.API}/cm/ucsb/programs?programGroupIds={GID}"
           f"&effectiveDatesRange={B.RANGE}&formatDependents=true")
    d = B.fetch_json(url)
    p = list(d.values())[0]
    assert EXPECT in p["name"], f"{GID}: unexpected program {p['name']}"
    assert p.get("status") == "Active", f"{GID}: not Active"
    print(f"fetched {p['name'].strip()} ({GID})")
    time.sleep(B.SLEEP)

    refs = set()

    def scan(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
        elif isinstance(obj, str) and B.IDISH.match(obj) and not B.CODEISH.match(obj):
            refs.add(obj)

    scan((p.get("requisites") or {}).get("requisitesSimple") or [])
    resolved = {}
    if refs:
        qs = "&".join(f"courseGroupIds={urllib.parse.quote(r)}" for r in sorted(refs))
        url = (f"{B.API}/cm/ucsb/courses/search/%24filters?{qs}"
               f"&effectiveDatesRange={B.RANGE}&skip=0&limit=500")
        d = B.fetch_json(url)
        for r in d.get("data") or []:
            code = f"{(r.get('subjectCode') or '').strip()} {(r.get('courseNumber') or '').strip()}"
            resolved[r["courseGroupId"]] = code
        print(f"id refs: {len(refs)}, resolved to courses: {len(resolved)}")
        time.sleep(B.SLEEP)
    resolve = lambda i: resolved.get(i)  # noqa: E731

    dept_names = {}
    for did in sorted(set(p.get("departments") or [])):
        try:
            info = B.fetch_json(f"{B.API}/ucsb/departments/{urllib.parse.quote(did)}")
            dept_names[did] = info.get("displayName") or info.get("name") or did
        except Exception:  # noqa: BLE001
            dept_names[did] = did
        time.sleep(B.SLEEP)

    reqs = B.convert_program(p, resolve)

    # ---- Area C fix (converter drops it; do not silently lose it) ----
    # C. Outside Concentration is an anyOf parent whose options yield no
    # courses: OPTION 1 is 7 catalog course sets (the public API does not
    # expand them) and OPTION 2/3 are freeformText. The converter also leaks
    # OPTION 3's sentence into the previous requirement's note (b-2) and
    # drops OPTION 2 entirely. Restore Area C faithfully: no invented
    # courses, empty course list + a note carrying all three options.
    for b in (p.get("requisites") or {}).get("requisitesSimple") or []:
        for r in b.get("rules") or []:
            if (r.get("name") or "").strip().startswith("Upper"):
                for sr in r.get("subRules") or []:
                    if (sr.get("name") or "").strip().startswith("C."):
                        opts = sr.get("subRules") or []
                        o1d = B.clean(opts[0].get("description") or "") if len(opts) > 0 else ""
                        o2 = B.clean(opts[1].get("value") or "") if len(opts) > 1 else ""
                        o3 = B.clean(opts[2].get("value") or "") if len(opts) > 2 else ""
                        for rq in reqs:
                            if o3 and o3 in (rq.get("note") or ""):
                                rq["note"] = re.sub(r"\s+", " ", rq["note"].replace(o3, "")).strip()
                        c_note = (
                            "Complete 16 upper-division units by one of three options. "
                            f"Option 1: {o1d}. "
                            "Course list is defined as a catalog course set; "
                            "see the official program page for the courses in this area. "
                            f"Option 2: {o2} "
                            f"Option 3: {o3}"
                        )
                        reqs.append({"id": "c-outside-concentration",
                                     "name": "C. Outside Concentration",
                                     "type": "elective", "courses": [], "note": c_note})
                        print("Area C restored from raw C block (no invented courses)")

    major_name = re.sub(r"\s+-\s+(BS|BA|B\.S\.|B\.A\.).*$", "", p["name"]).strip()
    degree = B.DEGREE_MAP.get(p.get("degreeDesignation") or "", "")
    dept_label = "; ".join(
        (dn if dn.lower().startswith("department") else f"Department of {dn}")
        for dn in (dept_names.get(dd, dd) for dd in (p.get("departments") or [])))
    doc = {
        "campus": "UCSB",
        "major": major_name,
        "degree": degree,
        "department": dept_label,
        "school": p.get("college") or "",
        "source_url": f"https://catalog.ucsb.edu/programs/{GID}",
        "checked": CHECKED,
        "requirements": reqs,
    }
    fn = f"ucsb-{SLUG}.json"
    for dd in (MAJ, WEBMAJ):
        with open(f"{dd}/{fn}", "w") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
    entry = {"campus": "UCSB", "major": major_name, "degree": degree,
             "file": fn, "requirement_count": len(reqs)}
    for dd in (MAJ, WEBMAJ):
        idx_path = f"{dd}/index.json"
        index = json.load(open(idx_path))
        index = [e for e in index if e.get("file") != fn]
        index.append(entry)
        with open(idx_path, "w") as f:
            json.dump(index, f, ensure_ascii=False, indent=1)
    codes = sorted({c for r in reqs for c in r["courses"]})
    print(f"{fn}: {major_name} {degree}, {len(reqs)} requirements, "
          f"{sum(len(r['courses']) for r in reqs)} course refs, {len(codes)} unique codes")
    print("requirement ids:", [r["id"] for r in reqs])
    if B.unresolved_sets:
        print(f"UNRESOLVED course-set refs ({len(set(B.unresolved_sets))}): "
              f"{sorted(set(B.unresolved_sets))}")
    if B.errors:
        print("ERRORS:", B.errors)


if __name__ == "__main__":
    main()
