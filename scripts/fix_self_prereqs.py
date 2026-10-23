#!/usr/bin/env python3
"""Remove self-references from structured prerequisites (K4 root fix).

Root cause: the UCI parser collected every bubblelink in the prereq
segment (including placement text naming the course itself), and the
UCSD parser scanned trailing prose ("may not receive credit for both
CSE 100R and CSE 100", "enrollment in DSC 95 is required") as if it
were prerequisite clauses. The parsers are patched separately; this
script sanitizes the stored data in place:

  data/raw/<campus>-courses.json        (prerequisites_courses)
  web/data/raw/<campus>-p*.json         (prerequisites_courses)
  web/data/search/<campus>/idx-*.json   (pre)

Only entries whose normalized code equals the course's own normalized
code are removed. prerequisites_raw (catalog text) is never touched.
"""
import json, glob, re, os

BASE = "/home/hatch/workspace/uc-course"

def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"\b0+(\d)", r"\1", str(s).strip()))

def clean_list(code, lst):
    k = norm(code)
    return [c for c in lst if norm(c) != k]

def process(path, field):
    d = json.load(open(path, encoding="utf-8"))
    n = 0
    for c in d:
        old = c.get(field) or []
        new = clean_list(c["code"], old)
        if len(new) != len(old):
            c[field] = new
            n += 1
    if n:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    return n

def main():
    total = 0
    for camp in ["uci", "ucsd", "ucsb"]:
        a = process(f"{BASE}/data/raw/{camp}-courses.json", "prerequisites_courses")
        b = 0
        for f in glob.glob(f"{BASE}/web/data/raw/{camp}-p*.json"):
            b += process(f, "prerequisites_courses")
        for f in glob.glob(f"{BASE}/data/raw/{camp}-p*.json"):
            b += process(f, "prerequisites_courses")
        s = 0
        for f in glob.glob(f"{BASE}/web/data/search/{camp}/idx-*.json"):
            s += process(f, "pre")
        print(f"{camp}: raw fixed {a}, webraw fixed {b}, search fixed {s}")
        total += a
    # verify zero self-refs remain in search indexes
    bad = 0
    for camp in ["uci", "ucsd", "ucsb"]:
        man = json.load(open(f"{BASE}/web/data/search/{camp}/manifest.json"))
        for f in man["files"]:
            for c in json.load(open(f"{BASE}/web/data/search/{camp}/{f}")):
                if norm(c["code"]) in [norm(p) for p in c.get("pre", [])]:
                    bad += 1
    print("remaining self-refs in search indexes:", bad)
    assert bad == 0

if __name__ == "__main__":
    main()
