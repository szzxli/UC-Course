#!/usr/bin/env node
/* UCSB 6 专业排课冒烟测试：接线后
 * 断言：排课可行性（Bio/Psych/Econ/Math 3 年；CS/EE 3 年容量不足、4 年可行）、
 * EE 拆分后 13 项要求全覆盖、开放池通用块、0 学分课不进选修池、
 * 先修顺序、学期学分上限、一课不双计、地图节点/边计数。 */
"use strict";
const assert = require("node:assert");
const E = require("../web/js/engine.js");
const fs = require("node:fs");

const MAJORS = [
  ["ucsb-computer-science", "ucsb-computer-science", 4, 100, 187],
  ["ucsb-electrical-engineering", "ucsb-electrical-engineering", 4, 133, 280],
  ["ucsb-biology", "ucsb-biology", 3, 153, 545],
  ["ucsb-psychology", "ucsb-psychology", 3, 119, 153],
  ["ucsb-economics", "ucsb-economics", 3, 82, 144],
  ["ucsb-mathematics", "ucsb-mathematics", 3, 36, 71],
];

function placedMap(plan) {
  const m = {};
  plan.terms.forEach((t, i) => t.courses.forEach((c) => { m[E.normCode(c.code)] = i; }));
  return m;
}
function checkOrder(plan, catalog, have, campus) {
  const placed = placedMap(plan);
  const haveSet = new Set((have || []).map(E.normCode));
  const scheduled = new Set(Object.keys(placed));
  let checked = 0;
  plan.terms.forEach((t, ti) => t.courses.forEach((c) => {
    const cat = catalog[E.normCode(c.code)];
    if (!cat || c.generic) return;
    const tree = E.parsePrereq(cat.prerequisites_raw || "", campus);
    if (!tree || tree.fallback) return;
    checked++;
    const st = (function f(node) {
      if (!node) return "SAT";
      if (node.code) {
        const nc = E.normCode(node.code);
        if (haveSet.has(nc)) return "SAT";
        if (placed[nc] !== undefined && placed[nc] < ti) return "SAT";
        if (scheduled.has(nc)) return "PENDING";
        return "EXTERNAL";
      }
      const ss = node.items.map(f);
      if (node.op === "AND") return ss.includes("PENDING") ? "PENDING" : "SAT";
      return ss.includes("SAT") ? "SAT" : (ss.includes("PENDING") ? "PENDING" : "EXTERNAL");
    })(tree);
    assert.notStrictEqual(st, "PENDING", `${c.code} 在第 ${ti} 学期排入时先修未满足`);
  }));
  return checked;
}

for (const [stem, engStem, years, expNodes, expEdges] of MAJORS) {
  const major = require(`../data/majors/${stem}.json`);
  const eng = require(`../data/engine/${engStem}.json`);
  const catalog = {};
  eng.courses.forEach((c) => { catalog[E.normCode(c.code)] = c; });
  if (years === 4) {
    const p3 = E.buildPlan({ years: 3, maxUnits: 21, startTerm: 0, have: [] }, { major, catalog });
    assert.strictEqual(p3.feasible, false, `${stem} 3 年应因容量不足不可行`);
    assert.ok(p3.unscheduled.length > 0, `${stem} 3 年应有未排入项`);
  }
  const plan = E.buildPlan({ years, maxUnits: 21, startTerm: 0, have: [] }, { major, catalog });
  const allScheduled = [];
  plan.terms.forEach((t) => t.courses.forEach((c) => allScheduled.push(c.code)));
  console.log(`--- ${stem}: feasible=${plan.feasible} terms=${plan.terms.length} totalUnits=${plan.totalUnits} unscheduled=${plan.unscheduled.length} scheduled=${allScheduled.length}`);
  assert.strictEqual(plan.feasible, true, `${stem} ${years} 年应可行`);
  assert.deepStrictEqual(plan.unscheduled, [], `${stem} ${years} 年不应有未排入项`);
  plan.terms.forEach((t) => assert.ok(t.units <= 21, `学期 ${t.label} 超学分上限：${t.units}`));
  assert.ok(plan.coverage.ge.length > 0, `${stem} 应有 UCSB GE 覆盖`);
  const covById = Object.fromEntries(plan.coverage.major.map((r) => [r.id, r.courses]));
  // 选修覆盖：开放池通用块数 = count；非开放池选修有覆盖；选修池不含 0 学分课
  for (const req of major.requirements) {
    if (req.type !== "elective") continue;
    assert.ok(covById[req.id] && covById[req.id].length > 0, `选修要求 ${req.id} 应有覆盖`);
    if (!req.courses || !req.courses.length) {
      // 开放池（无课单）：通用块数 = count，或 count 缺失时按 note 的 minimum N units 折算 ceil(N/4)
      const mm = req.note && req.note.match(/minimum (\d+) units?/i);
      const exp = req.count != null ? req.count : (mm ? Math.ceil(Number(mm[1]) / 4) : null);
      if (exp != null) assert.strictEqual(covById[req.id].length, exp, `开放池选修 ${req.id} 应为 ${exp} 个通用块`);
    }
    covById[req.id].forEach((c) => {
      const cat = catalog[E.normCode(c)];
      if (cat) assert.ok(Number(cat.units) > 0, `选修 ${req.id} 不应选中 0 学分课 ${c}`);
    });
  }
  // 分布约束未建模应有警告
  for (const req of major.requirements) {
    if (req.type === "elective" && req.note && /distinct|different groups|at least \d+ courses must be/i.test(req.note)) {
      assert.ok(plan.warnings.some((w) => w.indexOf(req.id) === 0 && w.indexOf("方向分布") >= 0), `选修 ${req.id} 的分布约束应有警告`);
    }
    if (req.type === "elective" && req.note && /minimum (\d+) units?/i.test(req.note)) {
      // 最低学分警告只在已选学分低于下限时出（选满时不出警告才是正确行为）
      const need = Number(req.note.match(/minimum (\d+) units?/i)[1]);
      const got = (covById[req.id] || []).reduce((s, c) => {
        const cat = catalog[E.normCode(c)];
        return s + (cat ? E.unitsNum(cat.units) : 4);
      }, 0);
      if (got < need) assert.ok(plan.warnings.some((w) => w.indexOf(req.id) === 0 && w.indexOf("最低") >= 0), `选修 ${req.id} 已选 ${got} < 下限 ${need}，应有最低学分警告`);
    }
  }
  // 一课不双计（通用块除外）
  const seen = new Set();
  plan.coverage.major.forEach((r) => r.courses.forEach((c) => {
    if (/选修|通用|C 区|领域 B|高年级选修/.test(c)) return;
    const nc = E.normCode(c);
    assert.ok(!seen.has(nc), `课程 ${nc} 被两个专业要求复用`);
    seen.add(nc);
  }));
  const n = checkOrder(plan, catalog, [], major.campus);
  console.log(`    order-checked: ${n}, warnings: ${plan.warnings.length}`);
  // 地图节点/边计数（复现 courses.html 地图 build 逻辑）
  const catByCode = {};
  eng.courses.forEach((c) => { catByCode[E.normCode(c.code)] = c; });
  const reqCodes = {};
  major.requirements.forEach((req) => {
    let codes = (req.courses || []).slice();
    (req.options || []).forEach((g) => { codes = codes.concat(g); });
    codes.forEach((c) => { reqCodes[E.normCode(c)] = true; });
  });
  const nodeSet = {};
  Object.keys(reqCodes).forEach((k) => { if (catByCode[k]) nodeSet[k] = true; });
  const trees = {}, edgeSet = new Set();
  const stack = Object.keys(nodeSet);
  while (stack.length) {
    const cur = stack.pop();
    if (trees.hasOwnProperty(cur)) continue;
    const cc = catByCode[cur];
    let tr = null;
    if (cc) {
      const raw = cc.prerequisites_raw || "";
      const t = raw ? E.parsePrereq(raw, major.campus) : null;
      tr = (t && !t.fallback) ? t : (cc.prerequisites_courses.length ? { op: "OR", items: cc.prerequisites_courses.map((x) => ({ code: E.normCode(x) })) } : null);
    }
    trees[cur] = tr;
    if (!tr) continue;
    const leaves = [];
    (function walk(node, underOr) {
      if (node.code) { leaves.push({ code: E.normCode(node.code), or: underOr }); return; }
      if (node.items) node.items.forEach((x) => walk(x, underOr || node.op === "OR"));
    })(tr, false);
    leaves.forEach((l) => {
      edgeSet.add(l.code + "->" + cur);
      if (!nodeSet[l.code]) { nodeSet[l.code] = true; if (catByCode[l.code]) stack.push(l.code); }
    });
  }
  console.log(`    map nodes=${Object.keys(nodeSet).length} edges=${edgeSet.size}`);
  assert.strictEqual(Object.keys(nodeSet).length, expNodes, `${stem} 地图节点数应为 ${expNodes}`);
  assert.strictEqual(edgeSet.size, expEdges, `${stem} 地图边数应为 ${expEdges}`);
  // 分专业断言
  if (stem === "ucsb-electrical-engineering") {
    assert.deepStrictEqual(covById["preparation-chemistry"], ["CHEM 1A"], "EE 化学三选一应取 CHEM 1A");
    assert.deepStrictEqual(covById["preparation-programming"], ["CMPSC 9"], "EE 编程二选一应取 CMPSC 9");
    assert.deepStrictEqual(covById["preparation-math-a"], ["MATH 3A"], "EE 数学 A 应取 MATH 3A");
    assert.deepStrictEqual(covById["preparation-math-b"], ["MATH 3B"], "EE 数学 B 应取 MATH 3B");
    assert.strictEqual(covById["preparation-ece-core"].length, 4, "EE 核心 4 门");
    assert.strictEqual(covById["preparation-ece10"].length, 6, "EE 10 序列 6 门");
    assert.strictEqual(covById["preparation-math-4"].length, 2, "EE 数学 4 两门全修");
    assert.strictEqual(covById["preparation-math-6"].length, 2, "EE 数学 6 两门全修");
    assert.strictEqual(covById["preparation-physics"].length, 5, "EE 物理 5 门全修");
    assert.strictEqual(covById["preparation-ece130"].length, 2, "EE 130 两门全修");
    assert.strictEqual(covById["required-upper-core"].length, 3, "EE 高年级核心 3 门");
    assert.deepStrictEqual(covById["required-upper-153"], ["ECE 153A"], "EE 153 二选一应取 153A");
    assert.strictEqual(covById["required-upper-188"].length, 3, "EE 毕业设计 3 门全修");
    assert.strictEqual(covById["approved-departmental-electives"].length, 9, "EE 系选修 9 门");
  }
  if (stem === "ucsb-computer-science") {
    assert.strictEqual(covById["science-electives-list-a"].length, 2, "CS 科学清单 A 应为 2 个通用块");
    assert.strictEqual(covById["science-electives-list-b"].length, 3, "CS 科学清单 B 应为 3 个通用块");
    assert.strictEqual(covById["major-field-electives"].length, 14, "CS 专业选修应为 14 门");
  }
  if (stem === "ucsb-psychology") {
    assert.strictEqual(covById["area-c"].length, 1, "Psych area-c 应只选 1 门实验课");
    assert.strictEqual(covById["area-iii-courses"].length, 4, "Psych area-iii 应选 4 门");
    assert.strictEqual(covById["area-b"].length, 2, "Psych area-b 应为 2 个通用块");
    assert.strictEqual(covById["area-d"].length, 5, "Psych area-d 研究组 5 门");
  }
  if (stem === "ucsb-mathematics") {
    assert.strictEqual(covById["upper-division-electives"].length, 3, "Math 高年级选修应为 3 个通用块");
  }
  if (stem === "ucsb-economics") {
    assert.strictEqual(covById["e"].length, 1, "Econ e 应选 1 门");
    assert.strictEqual(covById["d"].length, 6, "Econ d 应选 6 门");
  }
}
console.log("ucsb engine tests OK");
