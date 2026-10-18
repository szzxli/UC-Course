# UC 智选 (UC SmartPick) — Project Spec (Draft v0.2)

Date: 2026-10-17
Status: Name and MVP campuses decided. Awaiting repo creation + Phase 1 kickoff.

## 1. Positioning

- **transfer-os** covers pre-transfer: CC → UC course planning (ASSIST workflow layer).
- **This project** covers post-admission: UC → graduation, driven by post-grad goals.
- Clean boundary, no overlap. transfer-os ends at SIR; this project starts at enrollment.

## 2. Users

All UC students: freshmen + transfer admits; Chinese international + domestic California students.

## 3. The Wedge

Goal-driven course selection. The same major requires different course strategies depending on the goal:

- **Grad school / PhD track**: research-for-credit, graduate-level courses, GPA protection in major, faculty relationships.
- **Internship / employment track**: practical/project courses, recruiting-season timing, skill-adjacent electives.

No existing tool (ASSIST, campus Degree Planner) does goal→strategy mapping. That is the differentiator — not "AI scheduling" as a gimmick.

## 4. MVP Feature List

1. **Goal profiler** — 读研/直博 vs 实习/就业 vs undecided; drives all downstream suggestions.
2. **Degree requirement tracker** — major + GE + unit requirements, per campus per major (deterministic).
3. **Prereq-aware quarter planner** — deterministic engine: topological sort on prereq chains, unit caps per quarter.
4. **What-if analysis** — "if I take X instead of Y, what breaks?" (deterministic).
5. **AI advisor layer (BYOK)** — trade-off explanations, manual-vs-system schedule comparison, exception handling ("this course got cancelled — what now?"). Default: DeepSeek (accessible in China, cheap). Key stays in the product's local input box, never in chat.

## 5. Data: The Real Cost

ASSIST does not cover UC-internal courses. A new pipeline is required:

| Source | Content | Cadence |
|---|---|---|
| UC campus general catalogs (9 campuses) | Course descriptions, units, prereq chains | Annual |
| Schedule of classes (9 campuses) | Quarterly offerings | Quarterly |
| Department major requirement sheets | Degree requirements per major | Annual |

This is the biggest cost of the project — ongoing maintenance, not one-time. MVP campuses (decided 2026-10-17): UCLA, UCB, UCSD, UCI, UCSB.

## 6. Architecture

- Same proven pattern: static frontend + JSON data chunks, zero backend for MVP.
- **Rules engine (local JS)**: requirement checking, prereq validation, scheduling. Cheap, deterministic, correct by construction.
- **AI advisor (BYOK)**: only the advisory layer. Never generates the schedule itself (hallucination risk on hard constraints).
- No real-time enrollment/seat data in MVP (no source). No professor ratings in MVP.

## 7. Non-Goals (MVP)

- Real-time seat/enrollment monitoring.
- Native mobile app.
- UCR/UCM (add after the big three validate).

## 8. Open Decisions

1. ~~Project name~~ — decided: UC 智选 / UC SmartPick.
2. ~~MVP campuses~~ — decided: UCLA, UCB, UCSD, UCI, UCSB.
3. ~~Repo: user creates (same as transferos-China — no permission to create repos).~~ — decided: **UC Course** (user creates, then grants App access). ⏳ PENDING.
4. Data ToS: verify scraping terms for each UC catalog before building the pipeline.

## 9. Phasing

- Phase 0: Spec approval (this doc).
- Phase 1: Data pipeline — catalog + prereq extraction for MVP campuses.
- Phase 2: Rules engine + planner UI.
- Phase 3: AI advisor layer (BYOK).
