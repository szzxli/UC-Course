#!/usr/bin/env python3
"""Repair UCSD prerequisites: extract from plain-text 'Prerequisites:' in description
for courses where the scraper's <strong><em> split missed them."""
import json, re

CODE_RE = re.compile(r"\b([A-Z]{2,5})\s+(\d{1,3}[A-Z]{0,2})\b")
FAKE_DEPTS = {"THE", "AND", "FOR", "WITH", "FROM", "GPA", "ALL", "ANY", "ONE", "TWO",
              "UPPER", "LOWER", "PRIOR", "GRADE", "MINIMUM", "CONSENT", "INSTRUCTOR"}
CUT_MARKERS = ["corequisites:", "recommended preparation:", "recommended:", "note:", "concurrent:"]

def norm_code(s):
    return re.sub(r"\b0+(\d)", r"\1", s.strip())

def extract(desc, self_code):
    m = re.search(r"prerequisites?:", desc, re.I)
    if not m:
        return []
    seg = desc[m.end():]
    low = seg.lower()
    cut = len(seg)
    for cm in CUT_MARKERS:
        i = low.find(cm)
        if 0 <= i < cut:
            cut = i
    seg = seg[:cut]
    out = []
    for cm in CODE_RE.finditer(seg):
        dept, num = cm.group(1), cm.group(2)
        if dept in FAKE_DEPTS:
            continue
        c = norm_code(f"{dept} {num}")
        if c == norm_code(self_code):
            continue
        if c not in out:
            out.append(c)
        # slash expansion: "MATH 1B/10B" -> also "MATH 10B"
        tail = seg[cm.end():]
        sm = re.match(r"\s*/\s*(\d{1,3}[A-Z]{0,2})\b", tail)
        if sm:
            c2 = norm_code(f"{dept} {sm.group(1)}")
            if c2 != norm_code(self_code) and c2 not in out:
                out.append(c2)
    return out

def main():
    p = "/home/hatch/workspace/uc-course/data/raw/ucsd-courses.json"
    d = json.load(open(p))
    fixed = 0
    samples = []
    for c in d:
        if c.get("prerequisites_courses"):
            continue
        got = extract(c.get("description", ""), c["code"])
        if got:
            c["prerequisites_raw"] = "Prerequisites: " + "; ".join(got)
            c["prerequisites_courses"] = got
            fixed += 1
            if len(samples) < 8:
                samples.append((c["code"], got))
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)
    print(f"fixed: {fixed}")
    for code, got in samples:
        print(f"  {code} -> {got}")

if __name__ == "__main__":
    main()
