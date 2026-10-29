#!/usr/bin/env python3
"""Build UCSD engine catalogs (data/engine/ucsd-*.json + web/data/engine/ucsd-*.json).

Method (2026-10-29, along scripts/build_uci_engine.py):
- Seeds = every course code in the six UCSD major files (courses + options
  leaves, recursively). Closure = tree iteration: parse each member's raw with
  web/js/engine.js parsePrereq(raw, 'UCSD') via node, take leaves, repeat to
  a fixpoint. Each member's introducer (the course whose tree pulled it in,
  or 'major file') is recorded for the audit log.
- Prerequisites come from the UCSD snapshot's prerequisites_raw ONLY as a
  starting point. The snapshot's semicolons are a scraping flattening
  artifact, NOT catalog and/or structure, and restriction/credit clauses
  (restricted to majors, may not receive credit for both, corequisite,
  coschedule, credit for one of) parse as phantom prereqs. Every member's
  tree is therefore fixed by OVERWRITE below (verified 2026-27
  catalog.ucsd.edu department pages, see scripts/ucsd_overwrite_notes.md),
  or, for members whose snapshot raw parses cleanly (no semicolons, no
  Recommend/credit/restriction residue, no DROP codes), adopted from the
  snapshot and flagged in the screen report for review.
- OR-only retired/renamed codes in DROP are pruned (UCSD Math-CS precedent:
  dropping an OR alternative never blocks a path). A DROP code in a REQUIRED
  (AND/single) position fails the build loudly. NOTE on CHEM 140A/140B:
  the BIOL notes draft said "old-code leaf kept", but the standing rule
  (summary 2026-10-29, Math-CS precedent) is DROP from OR groups, so the
  BIBC 100/102 trees here drop 140A/140B; honors variants 40AH/40BH are
  CURRENT courses and stay as code-only leaves.
- Every stored raw is re-parsed and must deep-equal the pruned tree, so the
  runtime parser reproduces exactly what was curated here.
- Acyclicity is OR-aware: only REQUIRED edges (AND positions) form the
  depth graph. COGS 118A<->118B are mutual OR leaves ("may be taken in
  either order") and are NOT a hard cycle; engine.js buildPlan tolerates
  this (treeEarliest returns -1 for an OR leaf with no in-plan alternative,
  treated as satisfied). A required-edge cycle fails the build.
- MATHCS consistency: every code shared with the shipped
  web/data/engine/ucsd-mathcs.json must parse to the same tree; MATH 31AH
  stays the placement entry (raw '', as shipped) -- do NOT re-derive it as
  AND(20A, 20B).
- UNVERIFIED flags (kept in comments + build log, NOT silently resolved):
  BIEB 100 (no 2026-27 BIOL entry; archive numbers NOT adopted), MAE 9
  (replaced by MAE 8), MAE 124 (curriculum-listed, no course-page entry),
  PSYC 195P (no PSYC-page entry; units 4 from the major-file note only),
  POLI 5 (same-course family, own entry unchecked), ESYS 103 (MAE 124
  crosslist, unchecked), CHEM 40AH/40BH + PSYC 181GS (honors/section codes
  with no standalone page entry, kept as code-only OR leaves).

Usage: python3 scripts/build_ucsd_engine.py [--screen]
  --screen: print the closure audit (source, snapshot raw, flags) and stop
  without writing files. Run this first; fill gaps; then build.
"""
import json, subprocess, sys, os, itertools
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, 'data/raw/ucsd-courses.json')
ENGINE_JS = os.path.join(ROOT, 'web/js/engine.js')
MATHCS = os.path.join(ROOT, 'web/data/engine/ucsd-mathcs.json')

MAJORS = {
    'ucsd-computer-science': 'Computer Science (B.S.)',
    'ucsd-electrical-engineering': 'Electrical Engineering (B.S.)',
    'ucsd-biology': 'Biology (B.S.)',
    'ucsd-psychology': 'Psychology (B.A.)',
    'ucsd-economics': 'Economics (B.A.)',
    'ucsd-mathematics': 'Mathematics (B.S.)',
}

# Verified current-text overwrites (source: catalog.ucsd.edu 2026-27 department
# pages; full audit trail in scripts/ucsd_overwrite_notes.md).
OVERWRITE = {
    # ---- MATH ----
    'MATH 3B': '', 'MATH 3C': 'MATH 3B', 'MATH 4C': 'MATH 3C',
    'MATH 10A': 'MATH 3C or MATH 4C',
    'MATH 10B': 'MATH 10A or MATH 20A',
    'MATH 10C': 'MATH 10A or MATH 20A',
    'MATH 11': 'MATH 10B or MATH 20B',
    'MATH 18': 'MATH 4C or MATH 10A or MATH 20A',
    'MATH 20A': 'MATH 4C or MATH 10A',
    'MATH 20B': 'MATH 20A or MATH 10B or MATH 10C',
    'MATH 20C': 'MATH 20B',
    'MATH 20D': 'MATH 20C or MATH 31BH and MATH 18 or MATH 31AH',
    'MATH 20E': 'MATH 18 or MATH 31AH and MATH 20C or MATH 31BH',
    'MATH 31AH': '',  # placement entry, matches shipped ucsd-mathcs.json
    'MATH 31BH': 'MATH 31AH', 'MATH 31CH': 'MATH 31BH',
    'MATH 95': '',
    'MATH 100A': 'MATH 31CH or MATH 109', 'MATH 100B': 'MATH 100A',
    'MATH 102': 'MATH 18 or MATH 31AH and MATH 20C',
    'MATH 103A': 'MATH 31CH or MATH 109',
    'MATH 103B': 'MATH 103A or MATH 100A',
    'MATH 109': 'MATH 18 or MATH 31AH and MATH 20C',
    'MATH 120A': 'MATH 20E or MATH 31CH',
    'MATH 140A': 'MATH 31CH or MATH 109',
    'MATH 142A': 'MATH 31CH or MATH 109',
    'MATH 142B': 'MATH 142A or MATH 140A',
    'MATH 144': 'MATH 140B or MATH 142B',
    'MATH 154': 'MATH 31CH or MATH 109',
    'MATH 155A': 'MATH 18 or MATH 31AH and MATH 20C',
    'MATH 158': 'MATH 31CH or MATH 109',
    'MATH 170A': 'MATH 18 or MATH 31AH and MATH 20C or MATH 31BH and CSE 20 or MATH 31CH or MATH 109',
    'MATH 170B': 'MATH 170A',
    'MATH 170C': 'MATH 20D and MATH 170B',
    'MATH 171A': 'MATH 18 or MATH 31AH and MATH 20C',
    'MATH 171B': 'MATH 20C or MATH 31BH and MATH 171A',
    'MATH 173A': 'MATH 20C or MATH 31BH and MATH 18 or MATH 31AH',
    'MATH 173B': 'DSC 123A or MATH 173A',
    'MATH 180A': 'MATH 20C or MATH 31BH',
    'MATH 180B': 'MATH 20D and MATH 18 or MATH 31AH and MATH 109 or MATH 31CH and MATH 180A',
    'MATH 181A': 'MATH 180A and MATH 18 or MATH 31AH and MATH 20C',
    'MATH 183': 'MATH 20C or MATH 31BH',
    'MATH 184': 'MATH 31CH or MATH 109',
    'MATH 185': 'MATH 181A or ECON 120B and MATH 18 or MATH 31AH and MATH 20C or MATH 31BH',
    'MATH 186': 'MATH 20C or MATH 31BH',
    'MATH 188': 'MATH 31CH or MATH 109 and MATH 18 or MATH 31AH and MATH 100A or MATH 103A',
    'MATH 189': 'MATH 18 or MATH 31AH and MATH 20C and BENG 134 or CSE 103 or ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 183 or MATH 186 or SE 125',
    # ---- CSE ----
    'CSE 4GS': 'MATH 10A or MATH 20A', 'CSE 6GS': 'MATH 10A or MATH 20A',
    'CSE 5': '', 'CSE 5R': '', 'CSE 6R': '', 'CSE 8A': '', 'CSE 11': '',
    'CSE 12': 'CSE 8B or CSE 11',
    'CSE 15L': 'CSE 8B or CSE 11 or CSE 12 or DSC 30',
    'CSE 20': 'CSE 11 or CSE 6R or CSE 8A or CSE 8B or ECE 15',
    'CSE 21': 'CSE 20 or MATH 31CH',
    'CSE 25': 'COGS 18 or CSE 11 or CSE 6R or CSE 8A or CSE 8B or DSC 20',
    'CSE 29': 'CSE 11 or CSE 8B or ECE 15',
    'CSE 30': 'CSE 15L or CSE 29 or ECE 15',
    'CSE 100': 'CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 and CSE 15L or CSE 29 or ECE 15',
    'CSE 100R': 'CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 and CSE 15L or CSE 29 or ECE 15',
    'CSE 101': 'CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 or DSC 30',
    'CSE 103': 'MATH 20B and CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188',
    'CSE 105': 'CSE 12 and CSE 20 or MATH 109 or MATH 31CH and CSE 21 or MATH 100A or MATH 103A or MATH 154 or MATH 158 or MATH 184 or MATH 188',
    'CSE 109': 'CSE 15L or CSE 29',
    'CSE 110': 'CSE 100 or CSE 100R',
    'CSE 120': 'CSE 15L or CSE 29 and CSE 30 and CSE 100 or CSE 100R and CSE 101',
    'CSE 130': 'CSE 12 and CSE 100 or CSE 100R and CSE 105',
    'CSE 131': 'CSE 30 and CSE 100 or CSE 100R and CSE 105 and CSE 130',
    'CSE 140': 'CSE 30 or ECE 30',
    'CSE 150A': 'CSE 12 or DSC 40B and CSE 15L or CSE 29 or DSC 80 and COGS 118D or CSE 103 or ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 180B or MATH 181A or MATH 183 or MATH 186 and MATH 20A and MATH 18 or MATH 31AH',
    'CSE 151A': 'CSE 12 or DSC 40B and CSE 15L or CSE 29 or DSC 80 and COGS 118D or CSE 103 or ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 180B or MATH 181A or MATH 183 or MATH 186 and MATH 18 or MATH 31AH and MATH 20C or MATH 31BH',
    'CSE 158': 'CSE 12 or DSC 40B and CSE 15L or CSE 29 or DSC 80 and BENG 100 or BENG 134 or COGS 118D or CSE 103 or ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 180B or MATH 181A or MATH 183 or MATH 186',
    'CSE 158R': 'CSE 12 or DSC 40B and CSE 15L or CSE 29 or DSC 80 and BENG 100 or BENG 134 or COGS 118D or CSE 103 or ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 180B or MATH 181A or MATH 183 or MATH 186',
    # ---- ECE ----
    'ECE 5': '', 'ECE 15': '', 'ECE 25': '',
    'ECE 16': 'CSE 8B or CSE 11 or ECE 15 or MAE 8',
    'ECE 17': 'CSE 8B or CSE 11 or ECE 15',
    'ECE 18': 'CSE 8B or CSE 11 or ECE 15',
    'ECE 30': 'ECE 15 and ECE 25',
    'ECE 35': 'MATH 18 and MATH 20A and MATH 20B and PHYS 2A',
    'ECE 45': 'ECE 35', 'ECE 65': 'ECE 5 and ECE 35',
    'ECE 100': 'MATH 20D and ECE 45 and ECE 65',
    'ECE 101': 'ECE 45', 'ECE 102': 'ECE 65 and ECE 100',
    'ECE 103': 'ECE 65 and PHYS 2D or PHYS 4D and PHYS 4E',
    'ECE 107': 'MATH 20D and MATH 20E and PHYS 2A and PHYS 2B and PHYS 2C and ECE 45; or MATH 20D and MATH 20E and PHYS 4A and PHYS 4B and PHYS 4C and ECE 45',
    'ECE 108': 'ECE 25 or CSE 140 and ECE 45 and ECE 30 or CSE 30',  # 系页 L129 原文逗号作 AND，与 118 式并列结构一致
    'ECE 109': 'MATH 20A and MATH 20B and MATH 20C or MATH 31BH',
    'ECE 111': 'ECE 25 or CSE 140',
    'ECE 116': 'CSE 8B or CSE 11 or ECE 15 or MAE 8 and ECE 5 and ECE 18',
    'ECE 140A': 'CSE 8B or CSE 11 or ECE 15',
    'ECE 141A': 'ECE 17 and CSE 30 or ECE 30',
    'ECE 153': 'ECE 109',
    'ECE 155': 'ECE 101 or BENG 122A and ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 180B or MATH 183 or MATH 186 and ECE 153',
    'ECE 157A': 'ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 180B or MATH 183 or MATH 186 and ECE 161A',
    'ECE 161A': 'ECE 101', 'ECE 163': 'ECE 101 and ECE 102', 'ECE 164': 'ECE 102',
    'ECE 172A': 'ECE 101',
    'ECE 174': 'MATH 18 or MATH 31AH and ECE 15', 'ECE 175A': 'ECE 109 and ECE 174',
    # ---- ECON ----
    'ECON 1': '', 'ECON 2': 'ECON 1', 'ECON 3': 'ECON 1', 'ECON 4': '', 'ECON 5': '',
    'ECON 100A': 'ECON 1 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 100B': 'ECON 100A', 'ECON 100C': 'ECON 100B',
    'ECON 101': 'ECON 100B or ECON 102',
    'ECON 102': 'ECON 1 or ECON 100B and ECON 2 or ECON 3 or MATH 20C',
    'ECON 103': 'ECON 102 or ECON 110B or ECON 173A',
    'ECON 106': 'ECON 100B and ECON 102',
    'ECON 107': 'ECON 2 or ECON 100B and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 109': 'ECON 100C or MATH 31CH or MATH 109; or CSE 20 and MATH 20C',
    'ECON 110A': 'ECON 1 and ECON 3 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 110B': 'ECON 1 and ECON 3 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 112': 'ECON 110B and ECON 120B or MATH 181B',
    'ECON 113': 'ECON 100C or MATH 140A or MATH 142A and MATH 18 or MATH 31AH',
    'ECON 116': 'ECON 2 or ECON 100B', 'ECON 117': 'ECON 100A',
    'ECON 118': 'ECON 2 or ECON 100A and MATH 10A or MATH 20A',
    'ECON 119': 'ECON 2 or ECON 100A and MATH 10A or MATH 20A',
    'ECON 120A': 'ECON 1 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 120B': 'ECON 120A or ECE 109 or MAE 108 or MATH 180A or MATH 183 or MATH 186',
    'ECON 120C': 'ECON 120B or MATH 181B',
    'ECON 121': 'ECON 120B or MATH 181B and ECON 120C or ECON 5 or POLI 5 or POLI 5D',
    'ECON 122': 'ECON 120B or MATH 181B and MATH 18 or MATH 31AH',
    'ECON 125': 'PSYC 60 or MATH 183 or MATH 181A or MATH 11 or ECON 120A or MATH 186 or ECE 109 or MAE 108',
    'ECON 129': 'ECON 110A and ECON 120A or ECE 109 or MAE 108 or MATH 180A or MATH 183 or MATH 186',
    'ECON 130': 'ECON 2 or ECON 100A', 'ECON 131': 'ECON 2 or ECON 100A',
    'ECON 132': 'ECON 1 and ECON 2 or ECON 3 or ECON 100A or ECON 131 or ESYS 103 or MAE 124 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 133': 'ECON 1 and ECON 2 or ECON 3 or ECON 100A or ECON 131 or ESYS 103 or MAE 124 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 134': 'ECON 100A', 'ECON 136': 'ECON 100B',
    'ECON 137': 'ECON 100C and ECON 120C', 'ECON 138': 'ECON 1',
    'ECON 139': 'ECON 2 or ECON 100B', 'ECON 140': 'ECON 2 or ECON 100B',
    'ECON 141': 'ECON 100C', 'ECON 143': 'ECON 100C',
    'ECON 150': 'ECON 100C', 'ECON 151': 'ECON 100C', 'ECON 152': 'ECON 100C',
    'ECON 153': 'ECON 100C',
    'ECON 142': 'ECON 100B or ECON 109',
    'ECON 144': 'ECON 2 or ECON 100A', 'ECON 145': 'ECON 2 or ECON 100A',
    'ECON 146': 'ECON 110B',
    'ECON 147': 'ECON 2 or ECON 100A and ECON 120B or MATH 181B',
    'ECON 149': 'MATH 109 or ECON 100A or CSE 21 or CSE 20 or MATH 154 or MATH 188 or MATH 184',
    'ECON 162': 'ECON 1 and ECON 3', 'ECON 164': 'ECON 1 and ECON 3',
    'ECON 165': 'ECON 1 and ECON 3', 'ECON 167': 'ECON 1 and ECON 3',
    'ECON 168': 'ECON 1 and ECON 3', 'ECON 181': 'ECON 1 and ECON 3',
    'ECON 186': 'ECON 1 and ECON 3',
    'ECON 169': 'ECON 3 and ECON 100A',
    'ECON 171': 'ECON 100A and ECE 109 or MAE 108 or MATH 181A or ECON 120A or MATH 180A or MATH 183 or MATH 186 or MATH 180B',
    'ECON 172A': 'ECON 100A and ECON 120A or ECE 109 or MATH 180A or MATH 183 or MATH 186 and MATH 18 or MATH 31AH',
    'ECON 172B': 'ECON 172A or MATH 171A',
    'ECON 173A': 'ECON 100A and ECON 120B or MATH 181B and MATH 18 or MATH 31AH',
    'ECON 173B': 'ECON 4 or MGT 4 and ECON 173A',
    'ECON 174': 'ECON 173A',
    'ECON 175': 'ECON 1 and ECON 3 and MATH 10C or MATH 20C or MATH 31BH',
    'ECON 176': 'ECON 120C', 'ECON 178': 'ECON 120C', 'ECON 182': 'ECON 100C',
    'ECON 183': 'ECON 110B',
    'ECON 184': 'ECON 120B or MATH 181B', 'ECON 185': 'ECON 120B or MATH 181B',
    'ECON 190': 'ECON 100A and ECE 109 or ECON 120A or MATH 181A or MATH 186 or MATH 183 or MAE 108 or MATH 180A',
}

def _distribute(groups):
    """Distribute AND-of-ORs into '; or'-joined segments the parser reads back.

    groups: list of groups; each group is a list of alternatives; each
    alternative is a list of course codes joined by ' and '. Returns the raw
    string whose parse is exactly AND(OR(...), OR(...), ...) over the groups.
    """
    segs = []
    for combo in itertools.product(*groups):
        parts = []
        for alt in combo:
            parts.append(' and '.join(alt))
        segs.append(' and '.join(parts))
    out = []
    for i, s in enumerate(segs):
        out.append(('or ' + s) if i > 0 else s)
    return '; '.join(out)

OVERWRITE2 = {
    # ---- PSYC ----
    'PSYC 1': '', 'PSYC 2': '', 'PSYC 3': '', 'PSYC 3R': '', 'PSYC 4': '',
    'PSYC 6': '', 'PSYC 7': '', 'PSYC 42': '', 'PSYC 60': '',
    'PSYC 70': 'PSYC 60',
    'PSYC 71': 'COGS 14B or PSYC 60 or MATH 11 and PSYC 70 or COGS 14A',
    'PSYC 81': 'COGS 14B or PSYC 60 or MATH 11 and PSYC 70 or COGS 14A',
    'PSYC 113': 'PSYC 60 or COGS 14B or MATH 11 and PSYC 70 or COGS 14A and COGS 101A or COGS 107A or COGS 107B or COGS 107C or PSYC 102 or PSYC 106 or PSYC 108',
    'PSYC 114': 'PSYC 60 or COGS 14B or MATH 11 and PSYC 70 or COGS 14A',
    'PSYC 118': 'PSYC 60 or COGS 14B or MATH 11 and PSYC 70 or COGS 14A',
    'PSYC 193L': 'PSYC 60 or COGS 14B or MATH 11 and PSYC 70 or COGS 14A',
    'PSYC 115A': 'PSYC 60', 'PSYC 115B': 'PSYC 115A',
    'PSYC 116A': 'PSYC 70 and PSYC 100',
    'PSYC 116B': 'PSYC 116A', 'PSYC 116C': 'PSYC 116B',
    'PSYC 117': 'PSYC 60 or COGS 14B and PSYC 70 or COGS 14A',
    'PSYC 124': '',  # recommended-only (Recommended preparation: PSYC 100)
    'PSYC 126': 'PSYC 100 and PSYC 124',
    'PSYC 127': 'PSYC 60 and PSYC 70 and PSYC 172',
    'PSYC 132': '',  # recommended-only
    'PSYC 133': 'BILD 1 or COGS 107B or PSYC 106',
    'PSYC 133R': 'BILD 1 or COGS 107B or PSYC 106',
    'PSYC 136': 'PSYC 101 or PSYC 105',
    'PSYC 150': 'COGS 101A or COGS 107C or PSYC 102 or PSYC 108',
    'PSYC 151': 'COGS 14B or MATH 11 or PSYC 60',
    'PSYC 156': 'PSYC 101 or HDS 1',  # recommended PSYC 60 stripped
    'PSYC 160': 'PSYC 106',
    'PSYC 162': '',  # recommended-only
    'PSYC 171': 'BILD 12 or COGS 107B or COGS 17 or PSYC 106 or PSYC 181 or PSYC 181GS or PSYC 2',
    'PSYC 172': '',  # recommended-only
    'PSYC 175': 'COGS 14B or MATH 11 or PSYC 60 and COGS 14A or PSYC 70',
    'PSYC 181': '',
    'PSYC 187': '',  # recommended-only
    'PSYC 189': 'BILD 2 or COGS 101A or COGS 107B or PSYC 102 or PSYC 106',
    # ---- CHEM (140-series retired codes dropped from OR groups) ----
    'CHEM 4': '', 'CHEM 6A': 'CHEM 4 or MATH 3C', 'CHEM 6AH': 'MATH 4C or MATH 10A',
    'CHEM 6B': 'CHEM 6A or CHEM 6AH', 'CHEM 6BH': 'CHEM 6AH and MATH 20A',
    'CHEM 6C': 'CHEM 6B or CHEM 6BH', 'CHEM 6CH': 'CHEM 6BH and MATH 20B',
    'CHEM 7L': 'CHEM 6B or CHEM 6BH', 'CHEM 7LM': 'CHEM 6B or CHEM 6BH',
    'CHEM 12': 'CHEM 11',
    'CHEM 40A': 'CHEM 6B or CHEM 6BH', 'CHEM 40B': 'CHEM 40A', 'CHEM 40C': 'CHEM 40B',
    'CHEM 41A': 'CHEM 6B or CHEM 6BH', 'CHEM 41B': 'CHEM 41A', 'CHEM 41C': 'CHEM 41B',
    'CHEM 43A': 'CHEM 7L or CHEM 7LM and CHEM 40A or CHEM 40AH or CHEM 41A',
    'CHEM 43AM': 'CHEM 7L or CHEM 7LM and CHEM 40A or CHEM 40AH or CHEM 41A',
    'CHEM 100A': 'CHEM 6C or CHEM 6CH and CHEM 7L or CHEM 7LM',
    'CHEM 108': 'CHEM 43A or CHEM 43AM and CHEM 114A',
    'CHEM 109': 'CHEM 43A or CHEM 43AM and CHEM 114A',
    'CHEM 114A': 'CHEM 40A or CHEM 41A', 'CHEM 114AR': 'CHEM 40A or CHEM 41A',
    'CHEM 114B': 'CHEM 40B or CHEM 40BH or CHEM 41B and CHEM 114A',
    'CHEM 114C': 'CHEM 114A or BIBC 100',
    'CHEM 114D': 'CHEM 114A and CHEM 114B and CHEM 114C',
    'CHEM 116': 'CHEM 41C or CHEM 40B and CHEM 114A', 'CHEM 118': 'CHEM 114A',
    'CHEM 120A': 'CHEM 6C or CHEM 6CH and CHEM 40A or CHEM 41A',
    'CHEM 141': 'CHEM 40A or CHEM 40AH or CHEM 41A',
    'CHEM 142': 'CHEM 40B or CHEM 40BH or CHEM 41B and BIBC 100 or BILD 1 or CHEM 114A',
    'CHEM 143B': 'CHEM 43A or CHEM 43AM and CHEM 40B or CHEM 41B',
    'CHEM 143C': 'CHEM 43A or CHEM 43AM and CHEM 40B or CHEM 40BH or CHEM 41B',
    'CHEM 145': 'CHEM 40B or CHEM 40BH or CHEM 41B',
    'CHEM 151': 'CHEM 40A or CHEM 40AH or CHEM 41A',
    'CHEM 152': 'CHEM 40B or CHEM 41C', 'CHEM 154': 'CHEM 40B or CHEM 41C',
    # ---- PHYS ----
    'PHYS 1A': 'MATH 10A or MATH 20A', 'PHYS 1AL': 'MATH 10A or MATH 20A',
    'PHYS 1B': 'PHYS 1A or PHYS 2A and MATH 10B or MATH 20B',
    'PHYS 1BL': 'PHYS 1A or PHYS 2A and PHYS 1AL or PHYS 2BL and MATH 10B or MATH 20B',
    'PHYS 1C': 'PHYS 1B or PHYS 2B and MATH 10B or MATH 20B',
    'PHYS 1CL': 'PHYS 1B or PHYS 2B and PHYS 1BL or PHYS 2CL and MATH 10B or MATH 20B',
    'PHYS 2A': 'MATH 10A or MATH 10B or MATH 20A or MATH 20B or MATH 20C or MATH 31BH',
    'PHYS 2B': 'PHYS 2A or PHYS 4A and MATH 20B or MATH 20C or MATH 31BH',
    'PHYS 2BL': 'PHYS 2A or PHYS 4A',
    'PHYS 2C': 'PHYS 2A or PHYS 4A and MATH 20C or MATH 31BH',
    'PHYS 2CL': 'PHYS 2A or PHYS 4A and PHYS 2B or PHYS 4C',
    'PHYS 2D': 'PHYS 2A or PHYS 4A; and PHYS 2B; and MATH 20D',
    'PHYS 4A': 'MATH 20A', 'PHYS 4B': 'PHYS 4A and MATH 20A and MATH 20B',
    'PHYS 4C': _distribute([
        [['PHYS 4A', 'PHYS 4B'], ['PHYS 2A', 'PHYS 2B', 'PHYS 2C']],
        [['MATH 20A', 'MATH 20B', 'MATH 20C'], ['MATH 31BH']],
        [['MATH 18'], ['MATH 31AH']],
    ]),
    'PHYS 4D': _distribute([
        [['PHYS 4A', 'PHYS 4B', 'PHYS 4C'], ['PHYS 4C', 'PHYS 2A', 'PHYS 2B', 'PHYS 2C']],
        [['MATH 20A', 'MATH 20B', 'MATH 20C'], ['MATH 31BH']],
        [['MATH 20E'], ['MATH 31CH']],
        [['MATH 18'], ['MATH 31AH']],
    ]),
    'PHYS 4E': _distribute([
        [['PHYS 4A', 'PHYS 4B', 'PHYS 4C', 'PHYS 4D'], ['PHYS 4A', 'PHYS 4C', 'PHYS 4D', 'PHYS 2A', 'PHYS 2B', 'PHYS 2C']],
        [['MATH 20A', 'MATH 20B', 'MATH 20C'], ['MATH 31BH']],
        [['MATH 20D']],
        [['MATH 20E'], ['MATH 31CH']],
        [['MATH 18'], ['MATH 31AH']],
    ]),
    # ---- COGS ----
    'COGS 14B': 'COGS 14A',
    'COGS 101A': 'COGS 1', 'COGS 101B': 'COGS 1',
    'COGS 101C': 'COGS 1 and COGS 14A',
    'COGS 102A': 'COGS 1 and COGS 10', 'COGS 102B': 'COGS 102A',
    'COGS 102C': 'COGS 102B',
    'COGS 107A': 'BILD 12 or COGS 17', 'COGS 107B': 'COGS 107A',
    'COGS 107C': 'COGS 107B',
    'COGS 108': 'CSE 11 or CSE 8A or COGS 18 or DSC 10 or MAE 8',
    'COGS 109': 'COGS 14B and MATH 18 or MATH 31AH and COGS 18 or CSE 8A or CSE 11',
    'COGS 110': 'COGS 1 or HDS 1',
    'COGS 115': 'BILD 10 or BILD 12 or COGS 107A or COGS 107B or COGS 17 or HDS 110',
    'COGS 116': 'COGS 107A and COGS 107B or PSYC 106',
    'COGS 117': 'COGS 1',
    'COGS 118A': 'COGS 18 or CSE 8B or CSE 11 and MATH 18 or MATH 31AH and MATH 20E and MATH 180A and COGS 108 or COGS 109 or COGS 118B or CSE 158 or ECE 174 or ECE 175A',
    'COGS 118B': 'BILD 62 or COGS 18 or CSE 11 or CSE 8B and MATH 18 or MATH 31AH and MATH 20E and ECE 109 or ECON 120A or MAE 108 or MATH 180A or MATH 183 or MATH 186 and COGS 108 or COGS 109 or COGS 118A or COGS 188 or CSE 150A or CSE 151A or CSE 158 or CSE 158R or DSC 148 or ECE 174 or ECE 175A',
    'COGS 118C': 'MATH 18 or MATH 31AH; and COGS 14B or PSYC 60; and COGS 108 or COGS 109',
    'COGS 118D': 'MATH 18 or MATH 31AH and MATH 180A or MATH 183 or MATH 186 or ECE 109 or ECON 120A or MAE 108 and COGS 108 or COGS 109 or COGS 118A or COGS 118B or COGS 188 or CSE 150A or CSE 151A or CSE 158 or CSE 158R or DSC 148 or ECE 174 or ECE 175A',
    'COGS 119': 'COGS 14B or MATH 11 or PSYC 60',
    'COGS 137': 'COGS 14B or MATH 11 or PSYC 60',
    'COGS 120': 'COGS 108 or CSE 12 or DSC 30 and COGS 1 or COGS 10 or DSGN 1 or ENG 100D',
    'COGS 121': 'COGS 120 or CSE 170 and COGS 18 or CSE 8B or CSE 11 or DSC 30',
    'COGS 122': 'DSGN 100 or COGS 187B or COGS 187A or COGS 120 or CSE 170',
    'COGS 123': 'COGS 102C or COGS 120 or COGS 187A or COGS 187B or DSGN 1',
    'COGS 124': 'COGS 127 or COGS 121',
    'COGS 125': 'CSE 11 or CSE 8B and COGS 120 or CSE 170',
    'COGS 126': 'COGS 120 or COGS 121 or CSE 170',
    'COGS 127': 'VIS 41 or VIS 30 or DSGN 1 or COGS 1',
    'COGS 128': 'COGS 10 or DSGN 1 and COGS 108',
    'COGS 138': 'BILD 62 or COGS 18 or CSE 6R or CSE 8A and COGS 118C or COGS 189 or COGS 120 or ECE 45 or MATH 144',
    'COGS 142': 'COGS 14A', 'COGS 144': 'COGS 14A and COGS 14B',
    'COGS 150': 'COGS 14A and COGS 14B or MATH 11 or PSYC 60',
    'COGS 157': 'COGS 101A or COGS 101B or COGS 101C',
    'COGS 165': 'COGS 107B or COGS 107C or PSYC 106 or PSYC 108',
    'COGS 169': 'COGS 1 and COGS 107A',
    'COGS 170': 'COGS 17 or BILD 12', 'COGS 172': 'COGS 107A', 'COGS 176': 'COGS 107A',
    'COGS 175': 'COGS 101A or COGS 107A',
    'COGS 178': 'COGS 107A and COGS 107B',
    'COGS 179': 'COGS 107A or COGS 17 or BILD 12',
    'COGS 180': 'BILD 12 or COGS 17 and BILD 62 or COGS 18 or CSE 6R or CSE 8A and COGS 14A',
    'COGS 181': 'COGS 18 or CSE 11 or CSE 8B and MATH 18 or MATH 31AH and MATH 20E and MATH 180A and COGS 118A or COGS 118B or CSE 151A or CSE 158 or ECE 174 or ECE 175A',
    'COGS 182': 'COGS 18 or CSE 11 or CSE 8B and MATH 18 or MATH 31AH and MATH 180A and COGS 108 or COGS 109 or COGS 118B or CSE 150A or CSE 150B or CSE 151A or CSE 151B or CSE 158 or ECE 174 or ECE 175A',
    'COGS 183': 'COGS 118A or COGS 118B or COGS 109', 'COGS 185': 'COGS 118A',
    'COGS 186': 'COGS 108 or COGS 109',
    'COGS 187A': 'COGS 18 or CSE 11 or CSE 8A and COGS 10 or DSGN 1',
    'COGS 187B': 'COGS 187A',
    'COGS 188': 'COGS 109 or COGS 118A or COGS 118B',
    'COGS 189': 'COGS 108 or COGS 109 or COGS 118A or COGS 118B',
    'COGS 184': 'COGS 17 or COGS 107A or COGS 107B or COGS 107C or BILD 12',
    # ---- BIOL ----
    'BILD 1': '', 'BILD 3': '', 'BILD 4': '', 'BILD 5': '', 'BILD 12': '',
    'BILD 62': '', 'BILD 2': 'BILD 1',
    'BIBC 100': 'BENG 120 or CHEM 40A or CHEM 41A and BENG 120 or CHEM 40B or CHEM 41B',
    'BIBC 102': 'BENG 120 or CHEM 40A or CHEM 41A and BENG 120 or CHEM 40B or CHEM 41B',
    'BICD 100': 'BILD 1 and BILD 3',
    'BICD 110': 'BIBC 100 or BIBC 102 or CHEM 114A or CHEM 114B',
    'BIEB 121': 'BIEB 100 or MATH 11 or SIO 187 and BILD 3 and BILD 4',
    'BIEB 134': 'BILD 3', 'BIEB 135': 'BILD 3 and BILD 4',
    'BIEB 143': 'BIEB 100 or BIEB 150',
    'BIMM 100': 'BILD 1 and BIBC 103 or BILD 4 or BILD 70 or BIMM 101 and BENG 120 or CHEM 40A or CHEM 40AH or CHEM 41A and BENG 120 or CHEM 40B or CHEM 40BH or CHEM 41B',
    'BIMM 101': 'BILD 1 and BILD 4',
    'BIMM 110': 'BICD 100 or BICD 100R and BIMM 100 and BIBC 100 or BIBC 102 or CHEM 114A or CHEM 114B',
    'BIMM 120': 'BILD 3 and BIBC 100 or BIBC 102 or CHEM 114A or CHEM 114B and BIMM 100',
    'BIMM 143': 'BILD 1 and BILD 4 or BIEB 123 or BIMM 101',
    'BIMM 181': 'CSE 100 or CSE 100R and CSE 101 and BIMM 100 or CHEM 114C',
    'BIMM 182': 'CSE 100 or CSE 100R',
    # ---- BENG / DSC / SE / SIO / LIGN / MAE / HDS ----
    'BENG 100': 'MATH 18 or MATH 31AH and MATH 20C or MATH 31BH',
    'BENG 120': 'CHEM 6A and CHEM 6B',
    'BENG 134': 'MATH 20D and MATH 18 or MATH 31AH and BENG 100',
    'DSC 10': '', 'DSC 20': 'DSC 10', 'DSC 30': 'DSC 20',
    'DSC 40A': 'DSC 10 and MATH 20C or MATH 31BH and MATH 18 or MATH 31AH',
    'DSC 40B': 'DSC 20 and DSC 40A', 'DSC 80': 'DSC 30 and DSC 40A',
    'DSC 100': 'DSC 40B and DSC 80',
    'DSC 120': 'MATH 18 or MATH 31AH and MATH 20C or MATH 31BH and DSC 80',
    'DSC 123A': 'MATH 20C or MATH 31BH and MATH 18 or MATH 31AH',
    'DSC 148': 'DSC 40B or CSE 12 and DSC 80 or CSE 15L or CSE 29 and MATH 180A or MATH 180B or MATH 181A or MATH 183 or MATH 186 or CSE 103 or ECE 109 or ECON 120A or MAE 108',
    'SE 125': 'MATH 18 or MATH 31AH and MATH 20D',
    'SIO 128': 'BILD 1 or BILD 2 or BILD 3', 'SIO 134': 'BILD 3', 'SIO 187': 'BILD 3',
    'LIGN 167': 'MATH 10C or MATH 20C or MATH 31BH',
    'MAE 8': 'MATH 20A and MATH 20B', 'MAE 108': 'MATH 18',
    'MAE 40': 'MATH 20D and MATH 31AH or MATH 18 and PHYS 2B',  # snapshot 20F dropped explicitly
    'HDS 1': '', 'HDS 110': 'HDS 1 or PSYC 101',
    'BIBC 103': 'BILD 1',  # snapshot note text leaks self + CHEM 108 credit-exclusion
    'PHYS 2DL': 'PHYS 2BL or PHYS 2CL',  # Recommended preparation: 2D/4E stripped (parser cannot strip 'Recommended preparation:')
    'ECON 135': 'ECON 2 or ECON 100A and MATH 10A or MATH 20A',
    'SYN 1': '',  # remote/in-person cross-ref: SYN 1R is the same course, not a prereq
    'ECE 166': 'ECE 102 and ECE 107',  # snapshot stale (102 only); page L406
    'ECE 181': 'ECE 103 and ECE 107',  # snapshot stale (103 only); page L457-458
    'ECE 183': 'ECE 103 and ECE 107',  # snapshot stale (103 only); page L469-470
}
OVERWRITE.update(OVERWRITE2)

# Snapshot-missing codes: (title, units, raw). Applied ONLY when the snapshot
# has no entry for the code; the screen report verifies that assumption.
MANUAL = {
    # Verified 2026-10-29: catalog archive + dept mirrors agree; current CSE
    # page anchors #cse8b (see build log for sources).
    'CSE 8B': ('Introduction to Programming and Computational Problem-Solving II', '4', 'CSE 8A'),
    'CHEM 40AH': ('', '', ''), 'CHEM 40BH': ('', '', ''),  # honors variants, no standalone entry
    'PSYC 181GS': ('', '', ''),  # section code in PSYC 171 tree, no page entry
    'PSYC 195P': ('', '4', ''),  # units from major-file note only; prereq UNVERIFIED
    'MAE 9': ('', '', ''),  # replaced by MAE 8; pool seed, kept as code-only
    'MAE 124': ('Environmental Challenges: Science and Solutions', '4', ''),  # title from current MAE curriculum listing; units follow the ESYS 103 crosslist snapshot entry; prereq UNVERIFIED
    'MGT 4': ('Financial Accounting', '4', ''),  # ECON 4 crosslist (ECON page)
    'POLI 5': ('', '', ''),  # same-course family as POLI 5D/ECON 5; own entry unchecked
    'POLI 5D': ('Data Analytics for the Social Sciences', '4', ''),  # ECON 5 crosslist
    'BIEB 100': ('', '', ''),  # no 2026-27 entry; archive numbers NOT adopted
    'MMW 2': ('', '', ''),  # ENG 100D snapshot-listed writing alternative; current status unchecked, OR leaf only
}

# OR-only retired/renamed codes, pruned per Math-CS precedent. A DROP code in
# a REQUIRED position fails the build. (MATH 20 / MATH 31 are flat-extraction
# artifacts, not courses; HDP 1/110 were renumbered to HDS 1/110.)
DROP = {
    'MATH 20F', 'MATH 21C', 'MATH 21D', 'MATH 15A',
    'CSE 150', 'CSE 151', 'CSE 7',
    'CHEM 140A', 'CHEM 140B', 'CHEM 140C',
    'CHEM 140AH', 'CHEM 140BH', 'CHEM 140CH',
    'CHEM 143A', 'CHEM 143AM',
    'HDP 1', 'HDP 110', 'MATH 20', 'MATH 31',
}

def parse_all(raws):
    """Parse {code: raw} with engine.js parsePrereq(raw, 'UCSD') via node."""
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(raws, f)
        req = f.name
    script = (
        "const E=require(%s);const fs=require('fs');"
        "const data=JSON.parse(fs.readFileSync(%s,'utf8'));"
        "const out={};for(const code of Object.keys(data)){"
        "out[code]=E.parsePrereq(data[code]||'','UCSD');}"
        "console.log(JSON.stringify(out));"
        % (json.dumps(ENGINE_JS), json.dumps(req))
    )
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        raise SystemExit('node parse failed')
    return json.loads(r.stdout)

def leaves(tree, acc=None):
    if acc is None:
        acc = []
    if not tree:
        return acc
    if 'code' in tree:
        acc.append(tree['code'])
    elif 'items' in tree:
        for it in tree['items']:
            leaves(it, acc)
    return acc

def prune(tree, code):
    """Prune DROP leaves inside OR nodes; fail on DROP in required position."""
    if not tree or 'fallback' in tree:
        return None
    if 'code' in tree:
        if tree['code'] in DROP:
            raise SystemExit(
                'DROP leaf %s in REQUIRED position for %s (tree %s)'
                % (tree['code'], code, json.dumps(tree)))
        return {'code': tree['code']}
    op = tree['op']
    items = []
    for it in tree['items']:
        if 'code' in it and it['code'] in DROP:
            if op != 'OR':
                raise SystemExit(
                    'DROP leaf %s in %s position for %s'
                    % (it['code'], op, code))
            continue
        items.append(prune(it, code))
    items = [i for i in items if i is not None]
    if op == 'OR':
        seen, ded = set(), []
        for i in items:
            k = json.dumps(i, sort_keys=True)
            if k not in seen:
                seen.add(k)
                ded.append(i)
        items = ded
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    return {'op': op, 'items': items}

def flatten_tree(t):
    """Collapse nested same-op nodes (parse folds '; or' segments into
    left-nested ORs; serialize needs a flat OR of ANDs to round-trip)."""
    if t is None or 'code' in t:
        return t
    items = []
    for x in t['items']:
        fx = flatten_tree(x)
        if fx is not None and 'op' in fx and fx['op'] == t['op']:
            items.extend(fx['items'])
        elif fx is not None:
            items.append(fx)
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    return {'op': t['op'], 'items': items}

def serialize(tree):
    """Serialize a pruned tree to parser raw (same convention as UCI builder)."""
    if tree is None:
        return ''
    if 'code' in tree:
        return tree['code']
    op = tree['op']
    def branch_text(b):
        if 'code' in b:
            return b['code']
        if b['op'] == 'OR':
            return ' or '.join(branch_text(x) for x in b['items'])
        if b['op'] == 'AND':
            return ' and '.join(branch_text(x) for x in b['items'])
        raise SystemExit('bad branch %s' % json.dumps(b))
    if op == 'AND':
        return ' and '.join(branch_text(b) for b in tree['items'])
    if op == 'OR':
        segs = []
        for i, b in enumerate(tree['items']):
            t = branch_text(b)
            segs.append(('or ' + t) if i > 0 else t)
        return '; '.join(segs)
    raise SystemExit('bad op %s' % op)

def tree_equal(a, b):
    def flat(t):
        if t is None or 'code' in t:
            return t
        items = []
        for x in t['items']:
            fx = flat(x)
            if fx is not None and 'op' in fx and fx['op'] == t['op']:
                items.extend(fx['items'])
            else:
                items.append(fx)
        items = [i for i in items if i is not None]
        if not items:
            return None
        if len(items) == 1:
            return items[0]
        return {'op': t['op'], 'items': items}
    a, b = flat(a), flat(b)
    if a is None or b is None:
        return a is None and b is None
    if 'code' in a or 'code' in b:
        return a == b
    if a.get('op') != b.get('op'):
        return False
    if len(a['items']) != len(b['items']):
        return False
    if a['op'] == 'OR':
        return sorted(json.dumps(x, sort_keys=True) for x in a['items']) == \
               sorted(json.dumps(x, sort_keys=True) for x in b['items'])
    return all(tree_equal(x, y) for x, y in zip(a['items'], b['items']))

def required_leaves(tree):
    """Leaves on REQUIRED edges only: AND unions children, OR contributes none."""
    if not tree or 'fallback' in tree:
        return set()
    if 'code' in tree:
        return {tree['code']}
    if tree['op'] == 'AND':
        out = set()
        for it in tree['items']:
            out |= required_leaves(it)
        return out
    return set()  # OR: alternatives are optional, no required edge

def collect_codes(node, acc):
    if isinstance(node, str):
        acc.append(node)
    elif isinstance(node, list):
        for x in node:
            collect_codes(x, acc)

def seeds_for(stem):
    d = json.load(open(os.path.join(ROOT, 'web/data/majors/%s.json' % stem)))
    seeds = []
    for r in d['requirements']:
        collect_codes(r.get('courses', []), seeds)
        collect_codes(r.get('options', []), seeds)
    return list(OrderedDict.fromkeys(seeds))

def compute_closure(stem):
    """Tree-iteration closure. Returns (closure, introducer, raws, sources)."""
    snap = json.load(open(SNAP))
    by = {c['code']: c for c in snap}
    seeds = seeds_for(stem)
    bad = [s for s in seeds if s in DROP]
    if bad:
        raise SystemExit('%s: DROP code listed as major-file seed: %s' % (stem, bad))
    known = {}   # code -> introducer
    queue = []
    for s in seeds:
        known[s] = 'major file'
        queue.append(s)
    raws, sources = {}, {}
    while queue:
        batch = queue
        queue = []
        for code in batch:
            if code in OVERWRITE:
                raws[code] = OVERWRITE[code]
                sources[code] = 'OVERWRITE'
            elif code in by:
                raws[code] = by[code].get('prerequisites_raw', '') or ''
                sources[code] = 'snapshot'
            elif code in MANUAL:
                raws[code] = MANUAL[code][2]
                sources[code] = 'MANUAL'
            elif code in DROP:
                raws[code] = ''
                sources[code] = 'DROP'
            else:
                raws[code] = ''
                sources[code] = 'MISSING'
        trees = parse_all({c: raws[c] for c in batch})
        for code in batch:
            for leaf in leaves(trees[code]):
                if leaf not in known:
                    known[leaf] = code
                    queue.append(leaf)
    return known, raws, sources

def flag_snapshot(raw):
    flags = []
    if ';' in raw:
        flags.append('SEMICOLON')
    if 'Recommend' in raw or 'recommend' in raw:
        flags.append('RECOMMEND')
    return flags

def screen(stem):
    known, raws, sources = compute_closure(stem)
    snap = json.load(open(SNAP))
    by = {c['code']: c for c in snap}
    print('=== %s: seeds=%d closure=%d' % (
        stem, len(seeds_for(stem)), len(known)))
    missing = [c for c, s in sources.items() if s == 'MISSING']
    print('MISSING (not snapshot/OVERWRITE/MANUAL/DROP): %s' % (missing or 'none'))
    shadowed = [c for c in MANUAL if c in by]
    print('MANUAL shadowed by snapshot entry: %s' % (shadowed or 'none'))
    print('--- closure members NOT in OVERWRITE (adopted-from-snapshot review) ---')
    review = [c for c in sorted(known) if sources[c] in ('snapshot', 'MANUAL', 'DROP')]
    trees = parse_all({c: raws[c] for c in review})
    for code in review:
        src = sources[code]
        sraw = (by.get(code) or {}).get('prerequisites_raw', '') if src == 'snapshot' else ''
        flags = flag_snapshot(sraw) if src == 'snapshot' else []
        import re
        m = re.search(r'(\d+)', code.split(' ')[-1])
        if m and int(m.group(1)) >= 200:
            flags.append('200+')
        lv = leaves(trees[code])
        if code in lv:
            flags.append('SELF-LOOP')
        if any(l in DROP for l in lv):
            flags.append('HAS-DROP-LEAF')
        print('%-14s via %-22s src=%-8s flags=%s\n    snap_raw=%r\n    leaves=%s'
              % (code, known[code], src, ','.join(flags) or '-',
                 sraw[:220], lv))
    print('--- OVERWRITE codes in closure: %d ---' %
          sum(1 for c in sources.values() if c == 'OVERWRITE'))

def build(stem, display):
    known, raws, sources = compute_closure(stem)
    missing = [c for c, s in sources.items() if s == 'MISSING']
    if missing:
        raise SystemExit('%s: snapshot-missing codes need MANUAL entries: %s '
                         '(introducers: %s)'
                         % (stem, missing,
                            {c: known[c] for c in missing}))
    snap = json.load(open(SNAP))
    by = {c['code']: c for c in snap}
    trees = parse_all(raws)
    courses = []
    for code in sorted(known):
        if code in DROP:
            continue  # retired/renamed codes are never directory members
        tree = trees[code]
        pruned = prune(tree, code) if tree and 'fallback' not in tree else None
        pruned = flatten_tree(pruned)
        raw = serialize(pruned)
        check = parse_all({code: raw})[code]
        if isinstance(check, dict) and 'fallback' in check:
            check = None
        if not tree_equal(check, pruned):
            raise SystemExit(
                're-parse mismatch for %s:\n pruned=%s\n reparsed=%s\n raw=%r'
                % (code, json.dumps(pruned), json.dumps(check), raw))
        info = by.get(code)
        if info is None and code in MANUAL:
            title, units = MANUAL[code][0], MANUAL[code][1]
        elif info is not None:
            title, units = info.get('title', ''), str(info.get('units', ''))
        else:
            title, units = '', ''
        courses.append({
            'code': code,
            'title': title,
            'units': units,
            'prerequisites_raw': raw,
            'prerequisites_courses': list(OrderedDict.fromkeys(leaves(pruned))),
        })
    # OR-aware acyclicity on required edges only
    codes = {c['code'] for c in courses}
    req_map = {c['code']: (required_leaves(
        parse_all({c['code']: c['prerequisites_raw']})[c['code']])
        & codes) for c in courses}
    depth = {}
    def dep(code, stack):
        if code in depth:
            return depth[code]
        if code in stack:
            raise SystemExit('REQUIRED-edge cycle involving %s' % code)
        stack = stack | {code}
        d = 0
        for p in req_map.get(code, []):
            d = max(d, dep(p, stack) + 1)
        depth[code] = d
        return d
    for code in codes:
        dep(code, set())
    doc = {
        'campus': 'UCSD',
        'major': display,
        'checked': '2026-10-29',
        'n_courses': len(courses),
        'courses': courses,
    }
    outs = []
    for dest in (os.path.join(ROOT, 'data/engine/%s.json' % stem),
                 os.path.join(ROOT, 'web/data/engine/%s.json' % stem)):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'w') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write('\n')
        outs.append(dest)
    # MATHCS consistency: shared codes must parse to the same tree
    mc = json.load(open(MATHCS))
    mc_map = {c['code']: c for c in mc['courses']}
    shared = [c for c in courses if c['code'] in mc_map]
    if shared:
        new_trees = parse_all({c['code']: c['prerequisites_raw'] for c in shared})
        mc_trees = parse_all({c['code']: mc_map[c['code']]['prerequisites_raw']
                              for c in shared})
        for c in shared:
            a, b = new_trees[c['code']], mc_trees[c['code']]
            if isinstance(a, dict) and 'fallback' in a:
                a = None
            if isinstance(b, dict) and 'fallback' in b:
                b = None
            if not tree_equal(a, b):
                raise SystemExit(
                    'MATHCS mismatch for %s:\n new=%s\n mathcs=%s'
                    % (c['code'], json.dumps(a), json.dumps(b)))
    print('%s: %d courses, %d with prereqs, mathcs-shared %d OK'
          % (stem, len(courses),
             sum(1 for c in courses if c['prerequisites_courses']), len(shared)))
    return outs

def main():
    screen_only = '--screen' in sys.argv
    if screen_only:
        for stem in MAJORS:
            screen(stem)
        return
    outs = []
    for stem, display in MAJORS.items():
        outs += build(stem, display)
    used = set()
    for stem in MAJORS:
        known, _, _ = compute_closure(stem)
        used |= set(known)
    dead = sorted(set(OVERWRITE) - used)
    if dead:
        print('WARNING: OVERWRITE codes not in any closure (dead, review): %s' % dead)
    print('wrote', len(outs), 'files')

if __name__ == '__main__':
    main()
