# UC Course Catalog Scrape Log

Date: 2026-10-18. Method: polite single-process, ~2.75s between requests, static HTML only.

## Totals

| Campus | Courses | Depts/Subjects | With parsed prereqs |
|---|---|---|---|
| UCI | 5,843 | 120 (of 153 dept pages) | 1,985 |
| UCSD | 6,761 | 79 (of 80 subject pages) | 1,409 |

Output: `uci-courses.json`, `ucsd-courses.json` (fields: campus, dept, code, title, units, description, prerequisites_raw, prerequisites_courses).

## UCI notes

- 153 dept pages fetched; 33 returned 0 courses. Spot-verified (anesth, hindi, linguis, cbems): these pages genuinely list no courses (med-school clinical depts, restructured programs). Not parser failures.
- 18 pages initially failed with HTTP IncompleteRead (truncated responses); all retried successfully with robust fetching (+1,011 courses recovered).
- Prereq links extracted from `bubblelink code` anchors (title attr holds canonical code, e.g. "I&C SCI 45C").
- Units stored as string; ranges preserved ("2-4").

## UCSD notes

- 80 subject pages in sitemap; `FILM.html` returns 404 (stale sitemap entry — film courses moved under VIS/Visual Arts, already captured there).
- `HMNR.html` (Human Rights minor page) uses variant format: cross-listed codes with colon (`HMNR 100: SOCI 174 or HITO 119.`), and `<p class="course-name">` carries an id attribute. Parser adapted for both.
- 30 duplicate course codes: cross-listed courses appearing under two departments (e.g. ANTH 227 = SCIS version). Both records kept with their dept attribution.
- Prereq extraction is regex-based on raw text; non-course conditions (consent of instructor, GPA, standing) skipped via dept stoplist; self-references filtered.
- Units normalized: en-dashes → hyphens ("1–4" → "1-4").

## Validation

- 10 random courses/campus: code/title/units sane; prereq codes all present in raw prereq text (10/10 both).
- 0 courses with missing code/title on either campus.

## Structural differences from survey

- UCI: anchor attribute order varies (title before class) — parser matches tag first, then title attr.
- UCSD: minor pages (HMNR) deviate from standard `CODE. Title (units)` format.
- Neither catalog carries quarterly offering data (separate Schedule of Classes — Phase 2).
