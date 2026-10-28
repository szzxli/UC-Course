# UCSB Course Catalog Scrape Log

Date: 2026-10-23. Method: polite single-process, ~2.75s between requests, CourseDog public catalog API (catalog.ucsb.edu).

Catalog: 2026-2027 General Catalog (id friXFQMHuLvLoBthCmmV), school slug "ucsb".

## Totals

| Campus | Courses | Depts/Subjects | With parsed prereqs |
|---|---|---|---|
| UCSB | 13555 | 159 | 3701 |

Output: `ucsb-courses.json` + `ucsb-pNN.json` shards (fields: campus, dept, code, title, units, description, prerequisites_raw, prerequisites_courses).

Notes:
- Legacy my.sa.ucsb.edu/catalog only publishes up to 2022-2023 and /Current/ redirects to CourseDog, so the current catalog was taken from the CourseDog API that powers catalog.ucsb.edu.
- One record per courseGroupId (newest effective revision kept); course codes normalized to "SUBJECT NUMBER" (e.g. "POL S 1", "ANTH W 3").
- Titles use the catalog longName when present; units from creditHours (min-max when a range is given).
- prerequisites_raw is the catalog's freeform requisite text ("None" normalized to empty). prerequisites_courses parsed from it three ways: explicit subject codes (159 UCSB subjects), department full-name aliases validated against the catalog (e.g. "Anthropology 3" -> ANTH 3, "Film Studies 46" -> FAMST 46), and bare numbers inheriting the last-mentioned subject (alias/bare resolutions kept only when the code exists in the catalog).

## UCSB Environmental Studies B.S. major added (2026-10-27)

Builder: `scripts/build_ucsb_envst.py` (reuses `build_ucsb_majors.py` conversion;
it appends one index entry instead of rebuilding the UCSB index, so the other
six UCSB majors are untouched). Chinese layer: `scripts/add_major_zh.py`
(UCSB Environmental Science section). Output: `data/majors/` +
`web/data/majors/` `ucsb-environmental-science.json` (18 requirements,
131 course refs, 122 unique codes) + one `index.json` entry per copy.

Validation: all 122 unique codes match `data/raw/ucsb-courses.json` (100%,
0 missing). Known honest gap, same class as the 10-23 bio courseSets note:
Area C Outside Concentration Option 1 is defined as 7 catalog course sets
that the public API does not expand, so no course list is invented for it —
the file carries an empty-courses `c-outside-concentration` requirement whose
note states all three options (Option 1 course-set caveat + Option 2 petition
plan + Option 3 double major) and the official program page is linked as
`source_url`. The converter's freeformText quirk (dropping all but the last
freeform option, leaking Option 3's sentence into B-2's note) is repaired in
the builder's Area C post-process, not by hand-editing the JSON.

## Repository packaging note (2026-10-23)

The push channel (github push-files snapshot) rejects files over 15,925 bytes, so the UCSB shards were re-packed by cumulative bytes (each file <= 14,000 bytes; records unchanged, only shard boundaries moved, and each search entry's "f" pointer updated to its new shard). Three aggregate files are therefore NOT committed in this round: `data/raw/ucsb-courses.json`, `data/raw/search-ucsb.json`, and the updated three-campus `data/raw/search-index.json` (the full local copy is kept as-is, not rolled back). All three are regenerable from the committed shards in one pass: concatenate the `ucsb-p*.json` arrays in `data/raw/index.json` order to rebuild `ucsb-courses.json`, project each record to {code,t,u,d,c,f,pre} (f = containing shard) to rebuild `search-ucsb.json`, and set `search-index.json` = the UCI/UCSD entries plus the `search-ucsb.json` entries.
