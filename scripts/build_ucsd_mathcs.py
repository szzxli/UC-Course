#!/usr/bin/env python3
"""Build UCSD Mathematics-Computer Science (MA30) major file + pick engine catalog.

Official source: UCSD catalog, Department of Mathematics undergraduate page
https://catalog.ucsd.edu/curric/MATH-ug.html (fetched 2026-10-28).
Course prerequisites below are hand-written from the official CSE/MATH course
descriptions (https://catalog.ucsd.edu/courses/CSE.html and .../MATH.html),
NOT from the stale scraped prerequisites_raw in data/raw/ucsd-courses.json
(those flatten OR-alternatives with semicolons and truncate strings, e.g. CSE 100
ends with a dangling "or", CSE 105 lists alternatives as if all required).

Deliberate encoding decisions (do not "fix" silently):
- Placement-level prerequisites (AP scores, placement exams, MATH 4C/10A/10B/10C)
  are dropped: they are satisfied by placement, not by degree courses. Hence
  MATH 18's tree is MATH 20A only, MATH 20A/31AH have no tree.
- Legacy codes absent from current catalog data (MATH 20F, MATH 15A, MATH 184A)
  are dropped from trees: they are OR-alternatives only, never the sole path,
  and no current student can mark them completed through the site.
- CSE 100/105 trees are the UNION of the course description and the major's
  prior-course note (the note names MATH 184A; the description names a wider set).
- Elective pools (8 units each) are encoded without count, following the
  ucsd-mathematics.json precedent: pick v1 does not auto-recommend electives,
  the pick page states this explicitly for this pilot.
- Engine catalog = fixed requirement courses + transitive prereq closure only.
  Elective pool courses are NOT in the catalog (pick never needs them).
"""
import json, os, re

BASE = "/home/hatch/workspace/uc-course"
SRC = f"{BASE}/data/raw/ucsd-courses.json"

def norm(s):
    return re.sub(r"\b0+(\d)", r"\1", str(s).strip()).replace("  ", " ")

def expand_range(prefix, spec):
    """Expand '170A-B-C' -> [170A,170B,170C]; '120-121' -> [120,121]; '140-140L' -> [140,140L]."""
    parts = spec.split("-")
    if len(parts) == 1:
        return [prefix + " " + parts[0]]
    # first token may carry letters, e.g. 170A; last token may be a letter or number
    first, last = parts[0], parts[-1]
    m = re.match(r"(\d+)([A-Z]*)", first)
    num, letters = m.group(1), m.group(2)
    if last.isalpha() and len(last) == 1 and letters:
        # 170A-B-C style: same number, letters A..last (middle parts are letters too)
        letters_all = [letters] + [p for p in parts[1:] if p.isalpha()]
        return [prefix + " " + num + L for L in letters_all]
    if last.isdigit():
        return [prefix + " " + str(n) for n in range(int(num), int(last) + 1)]
    # 140-140L style: explicit endpoints
    return [prefix + " " + first, prefix + " " + last]

def pool(prefix, specs):
    out = []
    for s in specs:
        for c in expand_range(prefix, s):
            if c not in out:
                out.append(c)
    return out

APP_POOL = pool("MATH", ["170A-B-C", "171A-B", "173A-B", "174", "175", "179", "180B-C", "181A-B-C-E"])
COMP_POOL = (pool("MATH", ["152", "154", "155A-B", "157", "158", "160A-B", "168A", "182", "184", "185",
                            "187A-B", "188", "189"])
             + pool("CSE", ["107", "110", "112", "120-121", "123", "124", "127", "130", "131", "132A-B",
                            "134B", "140-140L", "141-141L", "142", "150A-B", "151A", "152A-B", "158",
                            "160", "165", "167", "168", "169", "176A"])
             + pool("COGS", ["108", "118A-B", "120", "185", "188"]))
GEN_EXTRA = pool("MATH", ["100C", "102", "104A-B", "106", "110", "111A-B", "114", "120A-B", "130",
                           "140A-B", "142A-B", "144", "150A-B", "163", "181D", "181F", "190A-B",
                           "193A-B", "194"])
GEN_POOL = []
for c in APP_POOL + COMP_POOL + GEN_EXTRA:
    if c not in GEN_POOL:
        GEN_POOL.append(c)

REQUIREMENTS = [
    {"id": "ld-calc", "name": "Lower-division: Linear Algebra and Calculus sequence (one of)",
     "type": "prereq",
     "courses": ["MATH 18", "MATH 20A", "MATH 20B", "MATH 20C", "MATH 20D", "MATH 20E",
                 "MATH 31AH", "MATH 31BH", "MATH 31CH"],
     "options": [["MATH 18", "MATH 20A", "MATH 20B", "MATH 20C", "MATH 20D", "MATH 20E"],
                 ["MATH 31AH", "MATH 31BH", "MATH 31CH", "MATH 20D"]]},
    {"id": "ld-cse11", "name": "Introduction to Programming and Computational Problem-Solving: Accelerated Pace (CSE 11)",
     "type": "prereq", "courses": ["CSE 11"]},
    {"id": "ld-tools", "name": "Software Tools and Techniques Laboratory (one of)",
     "type": "prereq", "courses": ["CSE 15L", "CSE 29"], "options": [["CSE 15L"], ["CSE 29"]]},
    {"id": "ld-cse12", "name": "Basic Data Structures and Object-Oriented Design (CSE 12)",
     "type": "prereq", "courses": ["CSE 12"]},
    {"id": "ud-math109", "name": "Mathematical Reasoning (MATH 109)",
     "type": "required", "courses": ["MATH 109"],
     "note": "Students completing MATH 31AH-BH-CH may substitute a four-unit upper-division mathematics elective for MATH 109."},
    {"id": "ud-algebra", "name": "Modern Applied Algebra or Modern Algebra (one sequence)",
     "type": "required", "courses": ["MATH 103A", "MATH 103B", "MATH 100A", "MATH 100B"],
     "options": [["MATH 103A", "MATH 103B"], ["MATH 100A", "MATH 100B"]]},
    {"id": "ud-cse105", "name": "Theory of Computability (CSE 105)",
     "type": "required", "courses": ["CSE 105"],
     "note": "CSE 21 or MATH 100A or MATH 103A or MATH 184 or MATH 184A must be taken prior to CSE 105."},
    {"id": "ud-cse100", "name": "Computer Implementations of Data Structures (CSE 100)",
     "type": "required", "courses": ["CSE 100"],
     "note": "CSE 21 or MATH 154 or MATH 184 or MATH 184A must be taken prior to CSE 100."},
    {"id": "ud-prob", "name": "Intro to Probability (one of)",
     "type": "required", "courses": ["MATH 180A", "MATH 183"], "options": [["MATH 180A"], ["MATH 183"]],
     "note": "MATH 183 is not a prerequisite for MATH 181A; duplication of credit exists between MATH 180A/183 and ECON 120A."},
    {"id": "ud-discrete", "name": "Discrete Math or Combinatorics (one of)",
     "type": "required", "courses": ["MATH 154", "MATH 158", "MATH 184", "MATH 188"],
     "options": [["MATH 154"], ["MATH 158"], ["MATH 184"], ["MATH 188"]]},
    {"id": "ud-cse101", "name": "Design and Analysis of Algorithms (CSE 101)",
     "type": "required", "courses": ["CSE 101"]},
    {"id": "ud-app-elect", "name": "Applied Mathematics Electives (8 units)",
     "type": "elective", "courses": APP_POOL,
     "note": "Eight units from the listed courses; a single course cannot fulfill more than one major requirement."},
    {"id": "ud-comp-elect", "name": "Computational Electives (8 units)",
     "type": "elective", "courses": COMP_POOL,
     "note": "Eight units from the listed courses; a single course cannot fulfill more than one major requirement. Students interested in computer architecture courses (CSE 140-140L, 141-141L, 142) should take CSE 30 as preparation."},
    {"id": "ud-gen-elect", "name": "General Math\u2014CS Electives (8 units)",
     "type": "elective", "courses": GEN_POOL,
     "note": "Eight additional units from the applied/computational elective lists or the listed courses; a single course cannot fulfill more than one major requirement."},
]

# Hand-written prerequisite trees (parser-friendly and/or form; see header notes).
TREES = {
    "MATH 18": "MATH 20A",
    "MATH 20A": "",
    "MATH 20B": "MATH 20A",
    "MATH 20C": "MATH 20B",
    "MATH 20D": "MATH 20C or MATH 31BH and MATH 18 or MATH 31AH",
    "MATH 20E": "MATH 18 or MATH 31AH and MATH 20C or MATH 31BH",
    "MATH 31AH": "",
    "MATH 31BH": "MATH 31AH",
    "MATH 31CH": "MATH 31BH",
    "MATH 109": "MATH 18 or MATH 31AH and MATH 20C",
    "MATH 100A": "MATH 31CH or MATH 109",
    "MATH 100B": "MATH 100A",
    "MATH 103A": "MATH 31CH or MATH 109",
    "MATH 103B": "MATH 103A or MATH 100A",
    "MATH 154": "MATH 31CH or MATH 109",
    "MATH 158": "MATH 31CH or MATH 109",
    "MATH 184": "MATH 31CH or MATH 109",
    "MATH 188": "MATH 31CH or MATH 109 and MATH 18 or MATH 31AH and MATH 100A or MATH 103A",
    "MATH 180A": "MATH 20C or MATH 31BH",
    "MATH 183": "MATH 20C or MATH 31BH",
    "CSE 11": "",
    "CSE 12": "CSE 8B or CSE 11",
    "CSE 15L": "CSE 8B or CSE 11 or CSE 12 or DSC 30",
    "CSE 29": "CSE 11 or CSE 8B or ECE 15",
    "CSE 20": "CSE 11 or CSE 6R or CSE 8A or CSE 8B or ECE 15",
    "CSE 21": "CSE 20 or MATH 31CH",
    "CSE 100": "CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 and CSE 15L or CSE 29 or ECE 15",
    "CSE 101": "CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 or DSC 30",
    "CSE 105": "CSE 12 and CSE 20 or MATH 109 or MATH 31CH and CSE 21 or MATH 100A or MATH 103A or MATH 154 or MATH 158 or MATH 184 or MATH 188",
}

CODE_RE = re.compile(r"\b([A-Z]{2,5})\s+(\d{1,3}[A-Z]{0,2})\b")

def leaves(raw):
    out = []
    for dept, num in CODE_RE.findall(raw or ""):
        c = norm(f"{dept} {num}")
        if c not in out:
            out.append(c)
    return out

def main():
    stored = {}
    for c in json.load(open(SRC)):
        stored[norm(c["code"])] = c
    major = {
        "campus": "UCSD",
        "checked": "2026-10-28",
        "degree": "B.S.",
        "department": "Department of Mathematics",
        "file": "ucsd-mathematics-computer-science.json",
        "major": "Mathematics-Computer Science",
        "note": "Mathematics-Computer Science major (MA30). A math-CS major is not allowed to also minor in computer science in the Department of Computer Science and Engineering; CSE courses are subject to enrollment restrictions.",
        "requirements": REQUIREMENTS,
        "school": "Division of Physical Sciences",
        "source_url": "https://catalog.ucsd.edu/curric/MATH-ug.html",
    }
    fixed = set()
    for r in REQUIREMENTS:
        if r["type"] != "elective":
            fixed.update(norm(c) for c in r["courses"])
    # Transitive closure over tree leaves.
    catalog_codes = set(fixed)
    frontier = list(fixed)
    while frontier:
        nxt = []
        for code in frontier:
            for leaf in leaves(TREES.get(code, "")):
                if leaf not in catalog_codes:
                    catalog_codes.add(leaf)
                    nxt.append(leaf)
        frontier = nxt
    courses = []
    for code in sorted(catalog_codes):
        s = stored.get(code, {})
        courses.append({
            "code": code,
            "title": s.get("title", ""),
            "units": str(s.get("units", "")),
            "prerequisites_raw": TREES.get(code, ""),
            "prerequisites_courses": leaves(TREES.get(code, "")),
        })
    engine = {"campus": "UCSD", "major": "Mathematics-Computer Science", "checked": "2026-10-28",
              "n_courses": len(courses), "courses": courses}
    for d in (f"{BASE}/data/majors", f"{BASE}/web/data/majors"):
        with open(f"{d}/ucsd-mathematics-computer-science.json", "w", encoding="utf-8") as f:
            json.dump(major, f, ensure_ascii=False, indent=1)
    for d in (f"{BASE}/data/engine", f"{BASE}/web/data/engine"):
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/ucsd-mathcs.json", "w", encoding="utf-8") as f:
            json.dump(engine, f, ensure_ascii=False, indent=1)
    entry = {"campus": "UCSD", "major": "Mathematics-Computer Science", "degree": "B.S.",
             "file": "ucsd-mathematics-computer-science.json", "requirement_count": len(REQUIREMENTS),
             "major_zh": "\u6570\u5b66-\u8ba1\u7b97\u673a\u79d1\u5b66", "major_tw": "\u6578\u5b78-\u8a08\u7b97\u6a5f\u79d1\u5b78"}
    for p in (f"{BASE}/data/majors/index.json", f"{BASE}/web/data/majors/index.json"):
        idx = json.load(open(p))
        assert not any(e["file"] == entry["file"] for e in idx), "entry already exists"
        pos = max([i for i, e in enumerate(idx) if e["campus"] == "UCSD"], default=-1) + 1
        idx.insert(pos, entry)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=1)
    print("requirements:", len(REQUIREMENTS), "| fixed courses:", len(fixed),
          "| catalog courses:", len(courses))
    print("fixed:", sorted(fixed))
    print("closure-only:", sorted(catalog_codes - fixed))
    missing_titles = [c["code"] for c in courses if not c["title"]]
    print("catalog entries without stored title:", missing_titles)

if __name__ == "__main__":
    main()
