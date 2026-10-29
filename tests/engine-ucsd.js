#!/usr/bin/env node
/* UCSD 6 专业排课冒烟测试：接线后
 * 断言：3 年均可行、无 UCSB GE 填充课、无 UCSB GE 覆盖、选修要求均有覆盖（EE 只选
 * 一个 depth 方向 + 职业选修 2 个通用块、生物实验 2 个通用块）、先修顺序、学期学分
 * 上限、一课不双计、地图节点/边计数、DROP 旧码不入目录、分布/学分下限警告。 */
"use strict";
const assert = require("node:assert");
const E = require("../web/js/engine.js");

const MAJORS = [
  ["ucsd-computer-science", "ucsd-computer-science"],
  ["ucsd-electrical-engineering", "ucsd-electrical-engineering"],
  ["ucsd-biology", "ucsd-biology"],
  ["ucsd-psychology", "ucsd-psychology"],
  ["ucsd-economics", "ucsd-economics"],
  ["ucsd-mathematics", "ucsd-mathematics"],
  // 数计专业文件与引擎文件名不同（引擎为手写树的 ucsd-mathcs.json）
  ["ucsd-mathematics-computer-science", "ucsd-mathcs"],
];
const BAD_GE = ["WRIT 2", "WRIT 107EP", "ENV S 136O", "ENV S 160", "ENV S 130A", "ENV S 189", "ENV S 173"];
// 退役/改号码：OR 组内丢弃，绝不入目录（见 build_ucsd_engine.py DROP）
const DROP = ["MATH 20F", "MATH 21C", "MATH 21D", "MATH 15A", "CSE 150", "CSE 151", "CSE 7",
  "CHEM 140A", "CHEM 140B", "CHEM 140C", "CHEM 140AH", "CHEM 140BH", "CHEM 140CH",
  "CHEM 143A", "CHEM 143AM", "HDP 1", "HDP 110", "MATH 20", "MATH 31"];

function placedMap(plan) {
  const m = {};
  plan.terms.forEach((t, i) => t.courses.forEach((c) => { m[E.normCode(c.code)] = i; }));
  return m;
}
function checkOrder(plan, catalog, have) {
  const placed = placedMap(plan);
  const haveSet = new Set((have || []).map(E.normCode));
  const scheduled = new Set(Object.keys(placed));
  let checked = 0;
  plan.terms.forEach((t, ti) => t.courses.forEach((c) => {
    const cat = catalog[E.normCode(c.code)];
    if (!cat || c.generic) return;
    const tree = E.parsePrereq(cat.prerequisites_raw || "", "UCSD");
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

for (const [stem, engStem] of MAJORS) {
  const major = require(`../data/majors/${stem}.json`);
  const eng = require(`../data/engine/${engStem}.json`);
  const catalog = {};
  eng.courses.forEach((c) => { catalog[E.normCode(c.code)] = c; });
  // DROP 旧码不入目录
  DROP.forEach((d) => assert.ok(!catalog[E.normCode(d)], `${stem} 目录不应含退役码 ${d}`));
  const plan = E.buildPlan({ years: 3, maxUnits: 21, startTerm: 0, have: [] }, { major, catalog });
  const allScheduled = [];
  plan.terms.forEach((t) => t.courses.forEach((c) => allScheduled.push(c.code)));
  console.log(`--- ${stem}: feasible=${plan.feasible} terms=${plan.terms.length} totalUnits=${plan.totalUnits} unscheduled=${plan.unscheduled.length} scheduled=${allScheduled.length}`);
  assert.strictEqual(plan.feasible, true, `${stem} 3 年应可行`);
  assert.deepStrictEqual(plan.unscheduled, [], `${stem} 不应有未排入课程`);
  plan.terms.forEach((t) => assert.ok(t.units <= 21, `学期 ${t.label} 超学分上限：${t.units}`));
  // 无 UCSB GE 填充
  BAD_GE.forEach((g) => assert.ok(!allScheduled.some((c) => E.normCode(c) === E.normCode(g)), `UCSB GE 课 ${g} 不应出现在 UCSD 计划中`));
  assert.ok(!allScheduled.some((c) => c.indexOf("GE ") === 0 || c.indexOf("外语") === 0 || c.indexOf("GE 写作") === 0), "不应有 UCSB GE 通用块");
  assert.deepStrictEqual(plan.coverage.ge, [], "UCSD 计划不应有 UCSB GE 覆盖清单");
  assert.ok(!plan.warnings.some((w) => w.indexOf("环境研究系") >= 0), "不应有 UCSB GE 警告");
  // 选修覆盖
  const covById = Object.fromEntries(plan.coverage.major.map((r) => [r.id, r.courses]));
  for (const req of major.requirements) {
    if (req.type !== "elective") continue;
    if (req.id.indexOf("depth-") === 0) continue; // 方向组单独断言
    assert.ok(covById[req.id] && covById[req.id].length > 0, `选修要求 ${req.id} 应有覆盖`);
    if (!req.courses || !req.courses.length) {
      assert.strictEqual(covById[req.id].length, req.count, `开放池选修 ${req.id} 应为 ${req.count} 个通用块`);
    }
  }
  // 分布/学分下限警告（CS upper-elect 标签分布、Psych lower-natsci 互斥、CS lower-cs-extra 最低学分）
  if (stem === "ucsd-computer-science") {
    assert.ok(plan.warnings.some((w) => w.indexOf("upper-elect") === 0 && w.indexOf("方向分布") >= 0), "CS upper-elect 标签分布应有警告");
    assert.ok(plan.warnings.some((w) => w.indexOf("lower-cs-extra") === 0 && w.indexOf("最低 4 学分") >= 0), "CS lower-cs-extra 最低学分应有警告");
  }
  if (stem === "ucsd-psychology") {
    assert.ok(plan.warnings.some((w) => w.indexOf("lower-natsci") === 0 && w.indexOf("方向分布") >= 0), "Psych lower-natsci 互斥应有警告");
  }
  // EE：只选一个 depth 方向 + 职业选修 2 块 + 设计课
  if (stem === "ucsd-electrical-engineering") {
    const depths = major.requirements.filter((r) => r.id.indexOf("depth-") === 0);
    const chosen = depths.filter((r) => covById[r.id] && covById[r.id].length > 0);
    assert.strictEqual(chosen.length, 1, `EE 应只选一个 depth 方向，实际 ${chosen.map((r) => r.id).join("、")}`);
    assert.ok(plan.warnings.some((w) => w.indexOf("方向已选") === 0), "EE 方向已选警告");
    assert.strictEqual((covById["prof-elect"] || []).length, 2, "职业选修应为 2 个通用块");
    assert.ok((covById["design"] || []).length === 1, "设计课应选 1 门");
    console.log(`    EE chosen depth: ${chosen[0].id} (${covById[chosen[0].id].length} 门)`);
  }
  // 生物：实验 2 块 + 专业选修 5 块（通用块近似，方案 A 差 2 学分见汇报）
  if (stem === "ucsd-biology") {
    assert.strictEqual((covById["upper-lab"] || []).length, 2, "生物实验应为 2 个通用块");
    assert.strictEqual((covById["upper-elect"] || []).length, 5, "生物专业选修应为 5 个通用块");
  }
  // 数计：三项 8 学分选修按通用块计入（planBlocks，课单供自选、先修树未核实）
  if (stem === "ucsd-mathematics-computer-science") {
    for (const id of ["ud-app-elect", "ud-comp-elect", "ud-gen-elect"]) {
      assert.strictEqual((covById[id] || []).length, 2, `数计 ${id} 应为 2 个通用块`);
      assert.ok((covById[id] || []).every((c) => !catalog[E.normCode(c)]), `数计 ${id} 应为通用块而非课号`);
    }
  }
  if (stem === "ucsd-mathematics") {
    assert.deepStrictEqual(covById["lower-seq"], ["MATH 31AH", "MATH 31BH", "MATH 31CH", "MATH 20D"], "数学低年级序列应选荣誉序列");
    assert.deepStrictEqual(covById["upper-analysis"], ["MATH 140A", "MATH 140B"], "数学分析应选第一组");
    assert.deepStrictEqual(covById["upper-algebra"], ["MATH 100A", "MATH 100B"], "数学代数应选第一组");
  }
  // 一课不双计（通用块除外：不在目录中的即通用块）
  const seen = new Set();
  plan.coverage.major.forEach((r) => r.courses.forEach((c) => {
    const nc = E.normCode(c);
    if (!catalog[nc]) return;
    assert.ok(!seen.has(nc), `课程 ${nc} 被两个专业要求复用`);
    seen.add(nc);
  }));
  const n = checkOrder(plan, catalog, []);
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
      const t = raw ? E.parsePrereq(raw, "UCSD") : null;
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
  // 地图分组（与 courses.html build() 同规则）
  const groups = {};
  (major.requirements || []).forEach((req) => {
    const codes = (req.courses || []).slice();
    (req.options || []).forEach((g) => codes.push(...g));
    let grp;
    if (req.type === "elective") grp = "elect";
    else if (req.type === "prereq") grp = "low";
    else {
      const idLow = /^(lower|ld-|pure-lower)/i.test(req.id || "");
      const nmLow = /低年級|低年级|lower-division/i.test((req.name_zh || "") + " " + (req.name || ""));
      grp = (idLow || nmLow) ? "low" : "high";
    }
    codes.forEach((c) => { const k = E.normCode(c); (groups[k] = groups[k] || new Set()).add(grp); });
  });
  const seeds = { low: 0, high: 0, elect: 0 };
  Object.values(groups).forEach((gs) => gs.forEach((g) => { if (seeds[g] !== undefined) seeds[g]++; }));
  console.log(`    map group seeds: low=${seeds.low} high=${seeds.high} elect=${seeds.elect}`);
  assert.ok(seeds.low >= 1, `${stem} 低年级分组种子应 >= 1，实得 ${seeds.low}`);
  if (stem === "ucsd-computer-science") assert.ok(seeds.low >= 10, `CS 低年级分组种子应 >= 10，实得 ${seeds.low}`);
  if (stem === "ucsd-mathematics") assert.ok(seeds.low >= 5, `Math 低年级分组种子应 >= 5，实得 ${seeds.low}`);
}
console.log("ucsd engine tests OK");
