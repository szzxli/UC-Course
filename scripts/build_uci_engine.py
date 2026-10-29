#!/usr/bin/env python3
"""Build UCI engine catalogs (data/engine/uci-*.json + web/data/engine/uci-*.json).

Method (2026-10-28, see MEMORY):
- Seeds + closure from /tmp/uci_catalog_plan.json (computed from major files +
  snapshot; closure counts: CS 116, EE 83, Bio 99, Psych 109, Econ 36, Math 33).
- Prerequisites come from the snapshot's prerequisites_raw, parsed at build time
  by web/js/engine.js parsePrereq(raw, 'UCI') via node.
- Curated overrides below replace snapshot text with VERIFIED current
  (2026-27 catalogue.uci.edu) text, or with hand-distributed equivalents where
  the parser flattens nested and/or groups (see engine.js parsePrereq limits).
- OR-only snapshot-missing leaves in DROP are pruned (UCSD Math-CS precedent:
  dropping an OR alternative never blocks a path). A DROP leaf in a REQUIRED
  (AND/single) position fails the build loudly instead of being silently cut.
- Every stored raw is re-parsed and must deep-equal the pruned tree, so the
  runtime parser reproduces exactly what was curated here.
- CHEM 1X raw is emptied: its "prerequisites" are exam-eligibility prose, not
  course requirements (it alone produced CHEM 600/3/P25/P66/P68/S02/MATH
  27/700/A02/Z43 phantom leaves).
- "Recommended:" clauses are stripped by the parser itself (recommendations
  are not requirements); PSY 123D keeps COGS 9B, PSY 188S / PHYSICS 7C /
  BIO SCI E112L have no remaining required text and are stored empty.
- UNVERIFIED flags (kept in comments + build log, NOT silently resolved):
  COMPSCI 114 (search page twice blank; snapshot tree uses current codes only),
  COMPSCI 177 (search page unavailable; inventory shows no prereq line;
  snapshot tree uses current codes only), SWE 124 (no prereq inferred from
  same-title COMPSCI 137, which is verified empty).
"""
import json, subprocess, sys, os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, 'data/raw/uci-courses.json')
# Closure plan: workspace copy is authoritative (survives /tmp wipes); /tmp
# copy is the legacy location the builder used to read. Regenerate the
# workspace copy whenever major files change (see closure method note above).
PLAN_WS = os.path.join(ROOT, 'scripts/uci_catalog_plan.json')
PLAN = PLAN_WS if os.path.exists(PLAN_WS) else '/tmp/uci_catalog_plan.json'

# Verified current-text overwrites (source: catalogue.uci.edu 2026-27 search
# pages fetched 2026-10-28, or the official course inventory where noted).
OVERWRITE = {
    # CS search pages 2026-10-28
    'COMPSCI 115': 'I&C SCI 6B and (I&C SCI 6N or MATH 3A) and STATS 67 and I&C SCI 51 and (SWE 43 or IN4MATX 43); or I&C SCI 6B and (I&C SCI 6N or MATH 3A) and STATS 7 and STATS 120A and I&C SCI 51 and (SWE 43 or IN4MATX 43)',
    'COMPSCI 116': 'I&C SCI 6D and (MATH 3A or I&C SCI 6N) and MATH 2B and I&C SCI 46',
    'COMPSCI 117': 'I&C SCI 6D and (MATH 3A or I&C SCI 6N) and MATH 2B and I&C SCI 46 and (COMPSCI 112 or COMPSCI 116 or COMPSCI 171 or COMPSCI 178)',
    'COMPSCI 118': '(I&C SCI 6N or MATH 3A) and I&C SCI 33',
    'COMPSCI 141': '(I&C SCI 51 or EECS 31) and I&C SCI 46',
    'COMPSCI 122C': 'COMPSCI 122A and (I&C SCI 53 or COMPSCI 143A)',
    'COMPSCI 111': 'I&C SCI 46 and I&C SCI 6D and (MATH 3A or I&C SCI 6N)',
    'COMPSCI 112': 'I&C SCI 46 and (MATH 3A or I&C SCI 6N)',
    'COMPSCI 165': 'COMPSCI 161',
    'SWE 117': 'SWE 43 and I&C SCI 33',
    'SWE 115': '(I&C SCI 45J or I&C SCI 45C or I&C SCI 46) and SWE 43',
    # Verified empty (search page shows no Prerequisite line)
    'COMPSCI 134': '', 'COMPSCI 162': '', 'COMPSCI 122B': '',
    'COMPSCI 137': '', 'COMPSCI 143A': '', 'COMPSCI 142A': '',
    'BIO SCI E112L': '',
    # Recommended-only current text (7C) / recommended-only snapshot (154C
    # handled by parser stripping; listed here for explicitness)
    'PHYSICS 7C': '',
    # Recommended 9C is defunct; 9B remains
    'PSY 123D': 'COGS 9B',
    'PSY 188S': '',
    # Eligibility prose, not course prereqs
    'CHEM 1X': '',
    # Inferred, UNVERIFIED: same-title COMPSCI 137 verified empty
    'SWE 124': '',
    # Hand-distributed equivalents of verified current texts (parser flattens
    # nested or(and(...)) groups; distribution law restores the exact tree).
    # CHEM 1LD snapshot: (1C and 1LC) or 1LE is NOT in CNF; distributing gives
    # (1C or 1LE) and (1LC or 1LE); 1LE is in DROP, so the stored tree is
    # exactly AND(1C, 1LC) — the standard general-chemistry-lab path.
    'CHEM 1LD': 'CHEM 1C or CHEM 1LE and CHEM 1LC or CHEM 1LE',    # 123A current: (2A or AP..) and (2B or AP..) and 3A and (120C or 130C)
    #   and ((100A and 100B and 100C) or (105A and 105B and 105C))
    'ECON 123A': '(MATH 2A) and (MATH 2B) and MATH 3A and (STATS 120C or MATH 130C) and ECON 100A and ECON 100B and ECON 100C; or MATH 2A and MATH 2B and MATH 3A and (STATS 120C or MATH 130C) and ECON 105A and ECON 105B and ECON 105C',
    # 171 current (inventory = snapshot raw): 46 and (2B or AP..) and
    #   (67 or ((7 or AP..) and 120A))
    'COMPSCI 171': 'I&C SCI 46 and MATH 2B and STATS 67; or I&C SCI 46 and MATH 2B and STATS 7 and STATS 120A',
    # 178 current (search page 2026-10-28): 6B and 6D and (6N or 3A) and
    #   (2B or AP..) and (67 or ((7 or AP..) and 120A))
    'COMPSCI 178': 'I&C SCI 6B and I&C SCI 6D and (I&C SCI 6N or MATH 3A) and MATH 2B and STATS 67; or I&C SCI 6B and I&C SCI 6D and (I&C SCI 6N or MATH 3A) and MATH 2B and STATS 7 and STATS 120A',
}

# OR-only snapshot-missing leaves, pruned per UCSD Math-CS precedent.
# IN4MATX 43 is deliberately NOT here: COMPSCI 115's verified current text
# lists it, so it stays as a code-only leaf node.
DROP = {
    'CHEM H2A', 'CHEM H2B', 'CHEM H2C', 'CHEM H52C', 'CHEM H52LA',
    'CHEM H52LB', 'CHEM H2LA', 'CHEM H2LB', 'CHEM M3C',
    'CHEM 3', 'CHEM 600', 'CHEM P25', 'CHEM P66', 'CHEM P68', 'CHEM S02',
    'MATH 27', 'MATH 700', 'MATH A02', 'MATH Z43',
    # Phantom from PHYSICS 3LC snapshot raw ('AP80' misread as a PHYSICS code);
    # 3LC's real prereq is PHYSICS 3A alone.
    'PHYSICS P80',
    'I&C SCI 32A', 'ENGR 10', 'CSE 31', 'CSE 46',
    'MATH 4', 'MATH 133A', 'CHEM 1LE', 'PHY SCI 5', 'COGS 9C',
}

ENGINE_JS = os.path.join(ROOT, 'web/js/engine.js')

PARSE_HELPER = r'''
const E = require(process.argv[1]);
const fs = require('fs');
const snap = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const by = {};
snap.forEach(c => { by[E.normCode(c.code)] = c; });
const reqs = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = {};
for (const code of reqs) {
  const raw = by[code] ? (by[code].prerequisites_raw || '') : '';
  out[code] = E.parsePrereq(raw, 'UCI');
}
console.log(JSON.stringify(out));
'''

def parse_all(codes, raws):
    """Parse raws (dict code->raw) with engine.js; returns dict code->tree."""
    import tempfile
    # Write a temp snapshot-shaped file carrying the overridden raws
    snap = json.load(open(SNAP))
    by = {c['code']: c for c in snap}
    tmp = []
    for code, raw in raws.items():
        base = dict(by.get(code, {'code': code, 'title': '', 'units': ''}))
        base['prerequisites_raw'] = raw
        tmp.append(base)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(tmp, f)
        tmp_snap = f.name
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(PARSE_HELPER.replace("process.argv[1]", "'%s'" % ENGINE_JS))
        helper = f.name
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(list(raws.keys()), f)
        req = f.name
    # Simpler: inline node script via -e with files as args
    script = (
        "const E=require(%r);const fs=require('fs');"
        "const snap=JSON.parse(fs.readFileSync(%r,'utf8'));"
        "const by={};snap.forEach(c=>{by[E.normCode(c.code)]=c;});"
        "const req=JSON.parse(fs.readFileSync(%r,'utf8'));"
        "const out={};for(const code of req){const raw=by[code]?(by[code].prerequisites_raw||''):'';out[code]=E.parsePrereq(raw,'UCI');}"
        "console.log(JSON.stringify(out));"
        % (ENGINE_JS, tmp_snap, req)
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
            continue  # drop OR alternative
        items.append(prune(it, code))
    items = [i for i in items if i is not None]
    # dedupe identical leaves inside OR
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

def serialize(tree):
    """Serialize a pruned tree (depth<=2 after distribution) to parser raw."""
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
        # one segment: parser splits on ' and ' first, so inline "a or b"
        # groups survive as OR nodes and the tree stays flat
        return ' and '.join(branch_text(b) for b in tree['items'])
    if op == 'OR':
        segs = []
        for i, b in enumerate(tree['items']):
            t = branch_text(b)
            segs.append(('or ' + t) if i > 0 else t)
        return '; '.join(segs)
    raise SystemExit('bad op %s' % op)

def tree_equal(a, b):
    # OR/AND are associative: flatten nested same-op nodes before comparing,
    # since segment joining re-nests OR trees (semantically identical).
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
        # order-insensitive for OR children
        return sorted(json.dumps(x, sort_keys=True) for x in a['items']) == \
               sorted(json.dumps(x, sort_keys=True) for x in b['items'])
    return all(tree_equal(x, y) for x, y in zip(a['items'], b['items']))

def main():
    plan = json.load(open(PLAN))
    snap = json.load(open(SNAP))
    by = {c['code']: c for c in snap}
    majors = {
        'uci-computer-science': 'Computer Science (B.S.)',
        'uci-electrical-engineering': 'Electrical Engineering (B.S.)',
        'uci-biology': 'Biological Sciences (B.S.)',
        'uci-psychology': 'Psychology (B.A.)',
        'uci-economics': 'Economics (B.A.)',
        'uci-mathematics': 'Mathematics (B.S.)',
    }
    out_files = []
    for stem, display in majors.items():
        closure = plan[stem]['closure']
        raws = {}
        for code in closure:
            raws[code] = OVERWRITE.get(code, (by.get(code) or {}).get('prerequisites_raw', ''))
        trees = parse_all(closure, raws)
        courses = []
        for code in sorted(closure):
            tree = trees[code]
            pruned = prune(tree, code) if tree and 'fallback' not in tree else None
            raw = serialize(pruned)
            # re-parse check: stored raw must reproduce the pruned tree
            check = parse_all([code], {code: raw})[code]
            if isinstance(check, dict) and 'fallback' in check:
                check = None  # empty raw -> fallback sentinel == no requirement
            if not tree_equal(check, pruned):
                raise SystemExit(
                    're-parse mismatch for %s:\n pruned=%s\n reparsed=%s\n raw=%r'
                    % (code, json.dumps(pruned), json.dumps(check), raw))
            info = by.get(code) or {}
            courses.append({
                'code': code,
                'title': info.get('title', ''),
                'units': str(info.get('units', '')),
                'prerequisites_raw': raw,
                'prerequisites_courses': list(OrderedDict.fromkeys(leaves(pruned))),
            })
        # acyclicity: every edge must go from a course to a strictly deeper one
        codes = {c['code'] for c in courses}
        tree_map = {c['code']: c['prerequisites_courses'] for c in courses}
        depth = {}
        def dep(code, stack):
            if code in depth:
                return depth[code]
            if code in stack:
                raise SystemExit('cycle involving %s' % code)
            stack = stack | {code}
            d = 0
            for p in tree_map.get(code, []):
                if p in codes:
                    d = max(d, dep(p, stack) + 1)
            depth[code] = d
            return d
        for code in codes:
            dep(code, set())
        doc = {
            'campus': 'UCI',
            'major': display,
            'checked': '2026-10-28',
            'n_courses': len(courses),
            'courses': courses,
        }
        for dest in (os.path.join(ROOT, 'data/engine/uci-%s.json' % stem[4:]),
                     os.path.join(ROOT, 'web/data/engine/uci-%s.json' % stem[4:])):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write('\n')
            out_files.append(dest)
        print('%s: %d courses, %d with prereqs, %d code-only leaves (IN4MATX 43 kept: %s)'
              % (stem, len(courses),
                 sum(1 for c in courses if c['prerequisites_courses']),
                 sum(1 for c in courses for p in c['prerequisites_courses'] if p not in codes),
                 any('IN4MATX 43' in c['prerequisites_courses'] for c in courses)))
    print('wrote', len(out_files), 'files')

if __name__ == '__main__':
    main()
