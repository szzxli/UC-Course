"""Invert UC->CC articulation index into CC->UC map for the transfer flow.
Input: web/data/credits/cc-{uci,ucsd-*}.json  {ucCourse: [{cc, course, note}]}
Output: web/data/credits/ccmap-{uci,ucsd}.json {ccName: [{cc: ccCourse, uc: ucCourse}]}
"""
import json, os
BASE = os.path.join(os.path.dirname(__file__), '..', 'web', 'data', 'credits')
def load(campus):
    idx = json.load(open(os.path.join(BASE, 'index.json')))
    out = {}
    for f in idx[campus]['cc']:
        d = json.load(open(os.path.join(BASE, f)))
        for uc, maps in d.items():
            for m in maps:
                out.setdefault(m['cc'], []).append({'cc': m['course'], 'uc': uc, 'note': m.get('note','')})
    # dedupe + sort
    for cc in out:
        seen, uniq = set(), []
        for e in sorted(out[cc], key=lambda x: (x['cc'], x['uc'])):
            k = (e['cc'], e['uc'])
            if k not in seen: seen.add(k); uniq.append(e)
        out[cc] = uniq
    return out
for campus in ('UCI', 'UCSD'):
    m = load(campus)
    p = os.path.join(BASE, 'ccmap-%s.json' % campus.lower())
    json.dump(m, open(p, 'w'), ensure_ascii=False)
    nmap = sum(len(v) for v in m.values())
    print(campus, len(m), 'CCs,', nmap, 'mappings ->', p, os.path.getsize(p)//1024, 'KB')
