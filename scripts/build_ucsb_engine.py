#!/usr/bin/env python3
"""UCSB 6 专业引擎目录建造器（第三批）。

口径（沿 UCI/UCSD 建造器，适配 UCSB）：
- 种子 = 专业文件 requirements 的 courses + options 全部叶子（data/majors 版为准，
  data/ 与 web/data/ 两份须一致，由 data-cogchain 保证）。
- 闭包 = 树式迭代：parsePrereq(raw, 'UCSB') → 取叶 → 补课 → 重 parse 至不动点。
  每成员记录引入者（introduced_by），审计用。
- UCSB 快照 raw 的特点：系名多为单词（Mathematics/Computer Science/Physics…，
  基础 DEPT_MAP 已覆盖；旧码 CS 8、单词 Engineering 3 走 engine.js 的 UCSB 校区映射），
  成绩短语（with a grade of C or better / minimum grade of C）与同期短语
  （may be taken concurrently）由解析器剥离；AP/分数短语剥离；非课程备选
  （如 significant prior programming experience）无叶、自然丢弃（树因此偏严，
  属已知近似，与 UCSD consent 剥离同类）。
- 区间：2A-B、34LA-LB、3AH-BH（荣誉变体共用尾缀，engine.js 已修）。
- 断言：prune 仅允许在 OR 内丢弃 + 单孩折叠 + OR 去重；DROP 叶出现在必修位置即停工；
  serialize（先 flatten_tree）后 re-parse 深等；OR 感知无环（互为 OR 叶不算环）。
- --screen：只审计不写文件。审计输出：闭包规模、快照外叶子、含 Recommend 的 raw、
  含通配（AA-ZZ）的树、re-parse 不等项。
- MANUAL：快照外但现行有效的课（如 CHEM 通用实验课），须以 catalog.ucsb.edu 为准
  逐项填标题/学分/先修原文；OVERWRITE：快照原文有误的课，以系页/目录页为准重写。
  未逐页核实的快照叶审采用项须在汇报中明标，不得写成已核实。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_JS = os.path.join(ROOT, "web/js/engine.js")

MAJORS = [
    "ucsb-computer-science",
    "ucsb-electrical-engineering",
    "ucsb-biology",
    "ucsb-psychology",
    "ucsb-economics",
    "ucsb-mathematics",
]

# 快照外但现行有效的课：标题/学分/先修原文以 catalog.ucsb.edu 为准。
# （CHEM 1AL/1BL/1CL/2AC/2BC/2CC 待浏览器核查任务回填，在此之前建造器拒绝写盘。）
MANUAL = {}

# 快照原文有误、须重写的课：code -> 定稿 raw（空串表示无先修）。
OVERWRITE = {
    # 15BL 原文括号提及自身（同期 lab）致自环；去括号后为 15A + 15B（15B 同期按引擎严格口径作先修，同 UCSD 同期处理）。
    "ENV S 15BL": "Environmental Studies 15A and 15B",
    # CMPSC 9 系原文含空格 W 码：CMPSC W8（= 快照 CMPSCW 8）、ENGR W3（= 快照 ENGR W 3，
    # 解析器无法区分于 ENGR 3）；W 变体与原课同名入门课，OR 组内弃 ENGR W 3、留可表示的 CMPSCW 8。
    "CMPSC 9": "CMPSC 8 or CMPSCW 8 or ENGR 3 or ECE 3 with a grade of C or better.",
    "CMPSCW 9": "CMPSC 8 or CMPSCW 8 or ENGR 3 or ECE 3 with a grade of C or better.",
    # CHEM 6AL 原文含已停开普通化学实验分支（1AL/1BL/1CL、2AC/2BC/2CC 六码均不在现行课程目录，
    # 项目页亦只作无链接纯文本）；删死分支、只留现行可验证分支 2AL + 2BL，其余元素沿快照原文。
    "CHEM 6AL": "Chemistry 2AL and 2BL; 109A or 109AH or 130A with a minimum grade of a C-; and Chemistry 109B or 109BH or 130B (may be taken concurrently).",
    # PSY 197A 原文为资格散文（full major 身份、已修 UD PSY 学分、GPA、导师协议），无课程先修；
    # 解析器从散文数字误造幻影码（'3 finalized UD PSY courses (12 units)' → PSY 3/PSY 12、
    # '3.5 UD PSY GPA' → PSY 5UD），同 UCI CHEM 1X 先例置空。
    "PSY 197A": "",
}

# OR 组内可丢弃的旧码/备选（出现在必修位置即停工）。
DROP = {
    # CHEM 1AL：仅见于 EEMB/ENV S 119/128/133/152/171 的 OR 备选（与 1A/1B/15A/15B 并列），
    # 本身不在现行课程目录；同组其余备选保留。
    "CHEM 1AL",
    # 2026-27 现行目录无条目的旧码（浏览器逐码核查，39 码全为 NOT FOUND，无停开注释、无已确认等价码）：
    # 以下 37 码在各树中仅现于 OR 备选位，丢弃后同组现行备选保留；PSY 3 另见 197A（已 OVERWRITE 置空）；
    # PSY 12 / PSY 5UD 不在此表——二者只由 197A 资格散文误解析而来，随 197A 置空一并消失。
    "MATH 3AH", "MATH 3BH", "MATH 3BI", "MATH 3C", "MATH 3CI",
    "MATH 5A", "MATH 5AI", "MATH 5B", "MATH 5BI", "MATH 5C", "MATH 6AI",
    "CMPSC 30", "CMPSC 48", "CMPSC 56",
    "ECE 2A", "ECE 2B", "ECE 2C", "ECE 124A", "ECE 124B",
    "ENGR 154", "ENGR 154A", "PSTAT 121A", "PHYS 105A", "ME 173",
    "CHEM 107A", "CHEM 107B", "CHEM 107C", "ENV S 100", "MCDB 126A",
    "PSY 110A", "PSY 110B", "PSY 3", "PSY 5",
    "ECON 100A", "ECON 104A", "ECON 104B", "ECON 105",
}


def norm(code):
    return re.sub(r"\b0+(\d)", r"\1", " ".join(str(code).split()))


def node_parse_all(raws):
    """批量调 node：输入 {code: raw}，返回 {code: tree}。tree 为 None 表示无约束。"""
    js = r"""
const E = require(process.argv[1]);
const raws = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = {};
for (const [code, raw] of Object.entries(raws)) {
  const t = raw ? E.parsePrereq(raw, 'UCSB') : null;
  out[code] = (t && !t.fallback) ? t : null;
}
console.log(JSON.stringify(out));
"""
    p = subprocess.run(["node", "-e", js, ENGINE_JS], input=json.dumps(raws).encode(),
                       capture_output=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[:2000])
    return json.loads(p.stdout.decode())


def tree_leaves(tree, under_or=False):
    if tree is None:
        return []
    if "code" in tree:
        return [(tree["code"], under_or)]
    out = []
    for it in tree.get("items", []):
        out.extend(tree_leaves(it, under_or or tree.get("op") == "OR"))
    return out


def flatten_tree(tree):
    """parse 把 ';' 段折成左嵌套同 op 树；摊平成一层（AND/OR 均满足结合律）。
    与 UCSD 建造器同法（PHYS 4C 实测：不摊平则 '; or' 段跨段串扰）。"""
    if tree is None or "code" in tree:
        return tree
    items = []
    for it in tree.get("items", []):
        f = flatten_tree(it)
        if f is not None and "code" not in f and f.get("op") == tree.get("op"):
            items.extend(f["items"])
        else:
            items.append(f)
    return {"op": tree["op"], "items": items}


def prune(tree, under_or=False):
    """DROP 仅在 OR 内丢弃；单孩折叠；OR 去重。
    返回 (new_tree, dropped, dropped_in_required)：必修位丢弃由调用方判停工。"""
    if tree is None or "code" in tree:
        if tree is not None and norm(tree["code"]) in DROP:
            return None, [tree["code"]], (not under_or)
        return tree, [], False
    dropped, bad = [], False
    items = []
    for it in tree.get("items", []):
        p, d, b = prune(it, under_or or tree.get("op") == "OR")
        dropped.extend(d)
        bad = bad or b
        if p is not None:
            items.append(p)
    if tree.get("op") == "OR":
        seen, uniq = set(), []
        for it in items:
            k = json.dumps(it, sort_keys=True)
            if k not in seen:
                seen.add(k)
                uniq.append(it)
        items = uniq
    if not items:
        return None, dropped, bad
    if len(items) == 1:
        return items[0], dropped, bad
    return {"op": tree["op"], "items": items}, dropped, bad


def cnf_clauses(tree):
    """树 → CNF 子句集（每子句为 code frozenset），供语义等价比较与序列化。
    分配律展开 + 吸收律（子句被另一子句包含时删去大子句）。"""
    if tree is None:
        return frozenset()
    if "code" in tree:
        return frozenset([frozenset([norm(tree["code"])])])
    if "wildcard" in tree:
        raise ValueError("wildcard in tree: %r" % (tree,))
    kids = [cnf_clauses(x) for x in tree["items"]]
    if tree.get("op") == "AND":
        out = frozenset()
        for k in kids:
            out = out | k
        return absorb(out)
    # OR：笛卡尔积并集
    out = frozenset([frozenset()])
    for k in kids:
        nxt = set()
        for c1 in out:
            for c2 in k:
                nxt.add(c1 | c2)
        out = frozenset(nxt)
    return absorb(out)


def absorb(clauses):
    cs = list(clauses)
    keep = []
    for c in cs:
        if any(other < c for other in cs if other is not c):
            continue
        keep.append(c)
    return frozenset(keep)


def serialize(tree):
    """树 → 单段 raw 串：CNF 形式（子句间 ' and '、子句内 ' or '）。
    解析器无括号，唯有 CNF 能无损表达任意 and/or 嵌套；存盘的 raw 即此串，
    引擎解析后语义与原树一致（显示的解释链为 CNF 展开形，逻辑等价）。"""
    if tree is None:
        return ""
    clauses = sorted(cnf_clauses(tree), key=lambda c: sorted(c))
    return " and ".join(" or ".join(sorted(c)) for c in clauses)


def tree_equal(a, b):
    """语义等价：双方 CNF 子句集相等（不比较括号结构）。"""
    if a is None or b is None:
        return a is None and b is None
    try:
        return cnf_clauses(a) == cnf_clauses(b)
    except ValueError:
        return False


def check_acyclic_or_aware(catalog):
    """只对必修边查环：OR 叶互指（如 A↔B 互为备选）不算环。"""
    raws = {c: (e.get("prerequisites_raw") or "") for c, e in catalog.items()}
    parsed = node_parse_all({k: v for k, v in raws.items() if v})
    trees = {c: parsed.get(c) for c in catalog}
    def required_edges(tree):
        if tree is None or "code" in tree:
            return []
        if tree.get("op") == "AND":
            out = []
            for it in tree["items"]:
                if "code" in it:
                    out.append(it["code"])
                else:
                    out.extend(required_edges(it))
            return out
        return []  # OR 整组不产生必修边
    visiting, done = set(), set()
    def visit(code, path):
        if code in done:
            return
        if code in visiting:
            raise SystemExit("CYCLE (required edges): " + " -> ".join(path + [code]))
        visiting.add(code)
        for nxt in required_edges(trees.get(norm(code))):
            if norm(nxt) in catalog:
                visit(norm(nxt), path + [code])
        visiting.discard(code)
        done.add(code)
    for code in catalog:
        visit(norm(code), [])


def main():
    screen = "--screen" in sys.argv
    snap = {norm(c["code"]): c for c in json.load(open(os.path.join(ROOT, "data/raw/ucsb-courses.json")))}
    for stem in MAJORS:
        major = json.load(open(os.path.join(ROOT, "data/majors/%s.json" % stem)))
        seeds = set()
        for r in major["requirements"]:
            seeds.update(norm(c) for c in (r.get("courses") or []))
            for g in (r.get("options") or []):
                seeds.update(norm(c) for c in g)
        # 闭包迭代
        catalog = {}
        introduced = {}
        frontier = set(seeds)
        for s in seeds:
            introduced[s] = "seed"
        while frontier:
            batch = {}
            for code in frontier:
                if code in MANUAL:
                    batch[code] = MANUAL[code]["prerequisites_raw"]
                elif code in OVERWRITE:
                    batch[code] = OVERWRITE[code]
                elif code in snap:
                    batch[code] = snap[code].get("prerequisites_raw") or ""
                else:
                    batch[code] = None  # 快照外：先记缺失，闭包后统一裁决
            parsed = node_parse_all({k: v for k, v in batch.items() if v is not None})
            nxt = set()
            for code, tree in parsed.items():
                for leaf, _ in tree_leaves(tree):
                    lc = norm(leaf)
                    if lc not in catalog and lc not in introduced:
                        introduced[lc] = code
                        nxt.add(lc)
            for code in batch:
                if code not in catalog:
                    if code in MANUAL:
                        catalog[code] = dict(MANUAL[code])
                    elif code in OVERWRITE:
                        catalog[code] = {"code": code, "title": (snap.get(code) or {}).get("title", ""),
                                         "units": (snap.get(code) or {}).get("units", ""),
                                         "prerequisites_raw": OVERWRITE[code], "prerequisites_courses": []}
                    elif code in snap:
                        catalog[code] = dict(snap[code])
                    # 快照外且无 MANUAL/OVERWRITE：不入目录，审计时报告
            frontier = nxt
        missing = sorted(c for c in introduced if c not in catalog)
        missing_open = [m for m in missing if m not in MANUAL and m not in DROP]
        missing_dropped = [m for m in missing if m in DROP]
        # 批量 parse + prune + serialize + 批量 re-parse 断言
        final = {}
        problems = []
        raws_all = {c: (e.get("prerequisites_raw") or "") for c, e in catalog.items()}
        parsed_all = node_parse_all({k: v for k, v in raws_all.items() if v})
        pruned_map, new_raw_map = {}, {}
        for code, entry in catalog.items():
            raw = raws_all[code]
            tree = flatten_tree(parsed_all[code]) if raw else None
            if tree is not None:
                pruned, dropped, bad = prune(tree)
                if bad:
                    problems.append("%s: DROP leaf in required position: %s" % (code, dropped))
                try:
                    new_raw = serialize(pruned) if pruned is not None else ""
                except ValueError as e:
                    problems.append("%s: %s (needs manual OVERWRITE)" % (code, e))
                    new_raw = ""
                    pruned = None
                pruned_map[code] = pruned
                new_raw_map[code] = new_raw
            else:
                pruned_map[code] = None
                new_raw_map[code] = ""
        reparsed = node_parse_all({k: v for k, v in new_raw_map.items() if v})
        for code, entry in catalog.items():
            pruned = pruned_map[code]
            new_raw = new_raw_map[code]
            if pruned is not None:
                re = flatten_tree(reparsed[code]) if new_raw else None
                if not tree_equal(pruned, re):
                    problems.append("%s: re-parse mismatch\n  pruned=%s\n  re=%s" % (code, json.dumps(pruned), json.dumps(re)))
                final[code] = {"code": code, "title": entry.get("title", ""), "units": entry.get("units", ""),
                               "prerequisites_raw": new_raw,
                               "prerequisites_courses": [c for c, _ in tree_leaves(pruned)] if pruned else []}
            else:
                final[code] = {"code": code, "title": entry.get("title", ""), "units": entry.get("units", ""),
                               "prerequisites_raw": "", "prerequisites_courses": []}
        print("%s: seeds=%d closure=%d with_prereq=%d missing_open=%d missing_dropped=%d problems=%d" % (
            stem, len(seeds), len(final), sum(1 for c in final.values() if c["prerequisites_raw"]),
            len(missing_open), len(missing_dropped), len(problems)))
        if missing_open:
            print("  MISSING:", missing_open)
        if missing_dropped:
            print("  MISSING-DROPPED (OR-only, pruned):", missing_dropped)
        for p in problems[:10]:
            print("  PROBLEM:", p)
        # 审计项：含 Recommend 的 raw、含通配的树
        rec = [c for c, e in final.items() if "ecommend" in (e["prerequisites_raw"] or "")]
        if rec:
            print("  RECOMMEND-raw:", rec)
        if screen:
            continue
        if missing_open:
            print("  !! refusing to write: missing codes without MANUAL/DROP entry", file=sys.stderr)
            sys.exit(1)
        if problems:
            print("  !! refusing to write: re-parse problems", file=sys.stderr)
            sys.exit(1)
        check_acyclic_or_aware(final)
        out = {"campus": "UCSB", "major": stem, "checked": "2026-10-29",
               "n_courses": len(final), "courses": [final[c] for c in sorted(final)]}
        for base in ("data/engine", "web/data/engine"):
            with open(os.path.join(ROOT, base, "%s.json" % stem), "w") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
        print("  wrote %s (%d courses)" % (stem, len(final)))


if __name__ == "__main__":
    main()
