#!/usr/bin/env python3
"""选课智能引擎试点数据：从 UCSB 目录快照中抽出引擎所需的全部课程记录。

引擎只需要候选课的完整记录（代码、标题、学分、先修原文、扁平先修列表），
不需要 13,555 门全量课程。候选集 = 环境科学专业要求课（含各选项组）
+ Area A 写作课（ENGL 10 系列、WRIT 50/50E/2/2E/2LK、WRIT 105/107/109 系列）
+ GE 指定课（136O、160、130A、189、173）。
输出 data/engine/ucsb-es.json 与 web/data/engine/ucsb-es.json（两份一致）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(code):
    import re
    return re.sub(r"\b0+(\d)", r"\1", " ".join(str(code).split()))


def main():
    raw = json.load(open(os.path.join(ROOT, "data/raw/ucsb-courses.json")))
    by = {norm(c["code"]): c for c in raw}
    mj = json.load(open(os.path.join(ROOT, "data/majors/ucsb-environmental-science.json")))

    codes = set()
    for r in mj["requirements"]:
        codes.update(norm(c) for c in r["courses"])
        for g in r.get("options", []):
            codes.update(norm(c) for c in g)
    # Area A
    for c in ["ENGL 10", "ENGL 10AC", "ENGL 10EM", "ENGL 10LC",
              "WRIT 50", "WRIT 50E", "WRIT 2", "WRIT 2E", "WRIT 2LK"]:
        codes.add(norm(c))
    for code in by:
        if code.startswith("WRIT 105") or code.startswith("WRIT 107") or code.startswith("WRIT 109"):
            codes.add(code)
    # GE 指定课
    for c in ["ENV S 136O", "ENV S 160", "ENV S 130A", "ENV S 189", "ENV S 173"]:
        codes.add(norm(c))

    missing = sorted(c for c in codes if c not in by)
    if missing:
        print("missing from catalog:", missing, file=sys.stderr)
        sys.exit(1)
    courses = []
    for code in sorted(codes):
        c = by[code]
        courses.append({
            "code": code,
            "title": c.get("title", ""),
            "units": c.get("units", ""),
            "prerequisites_raw": c.get("prerequisites_raw", ""),
            "prerequisites_courses": [norm(x) for x in (c.get("prerequisites_courses") or [])],
        })
    out = {"campus": "UCSB", "major": "Environmental Studies (B.S.)",
           "checked": "2026-10-27", "n_courses": len(courses), "courses": courses}
    for path in ("data/engine/ucsb-es.json", "web/data/engine/ucsb-es.json"):
        full = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"engine data: {len(courses)} courses -> data/engine/ucsb-es.json + web/data/engine/ucsb-es.json")


if __name__ == "__main__":
    main()
