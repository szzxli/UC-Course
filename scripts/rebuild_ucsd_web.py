#!/usr/bin/env python3
"""Rebuild UCSD web chunks (data/raw + data/search) from repaired raw data.
Mirrors the original chunking: sequential chunks."""
import json, math, os

BASE = "/home/hatch/workspace/uc-course"
RAW = f"{BASE}/data/raw/ucsd-courses.json"
WEBRAW = f"{BASE}/web/data/raw"
WEBSEARCH = f"{BASE}/web/data/search/ucsd"

def chunked(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def main():
    d = json.load(open(RAW))
    print("raw courses:", len(d))
    # 1. web/data/raw/ucsd-pNN.json — full records, ~625/chunk like before
    #    (original: 6874 over 41 uci+ucsd files; ucsd had 11 search files; keep raw chunks stable-ish)
    #    Check existing ucsd raw chunk count to preserve file names
    existing = sorted(f for f in os.listdir(WEBRAW) if f.startswith("ucsd-p"))
    n_chunks = len(existing)
    print("existing ucsd raw chunks:", n_chunks)
    per = math.ceil(len(d) / n_chunks)
    for i, ch in enumerate(chunked(d, per)):
        fn = f"{WEBRAW}/ucsd-p{i+1:02d}.json"
        json.dump(ch, open(fn, "w"), ensure_ascii=False)
    # 2. web/data/search/ucsd/idx-pNN.json — search index
    man = json.load(open(f"{WEBSEARCH}/manifest.json"))
    n_s = len(man["files"])
    per_s = math.ceil(len(d) / n_s)
    idx_files = []
    for i, ch in enumerate(chunked(d, per_s)):
        fn = f"idx-p{i+1:02d}.json"
        idx = [{"code": c["code"], "t": c["title"], "u": c["units"], "d": c["dept"],
                "c": c["campus"], "f": f"ucsd-p{(j // per) + 1:02d}.json",
                "pre": c.get("prerequisites_courses", [])} for j, c in
               enumerate(ch, start=i * per_s)]
        json.dump(idx, open(f"{WEBSEARCH}/{fn}", "w"), ensure_ascii=False)
        idx_files.append(fn)
    json.dump({"files": idx_files, "count": len(d)}, open(f"{WEBSEARCH}/manifest.json", "w"))
    # verify
    tot = sum(len(json.load(open(f"{WEBSEARCH}/{f}"))) for f in idx_files)
    n_pre = sum(1 for f in idx_files for c in json.load(open(f"{WEBSEARCH}/{f}")) if c["pre"])
    print(f"search index: {tot} courses, {n_pre} with pre")

if __name__ == "__main__":
    main()
