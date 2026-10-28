#!/usr/bin/env node
/* 选课智能引擎测试：UCSB 环境科学试点
 * 断言：覆盖完整、先修顺序、学期学分上限、学期数、总学分合理区间、关键课、不可行情形。 */
"use strict";
const assert = require("node:assert");
const E = require("../web/js/engine.js");
const major = require("../data/majors/ucsb-environmental-science.json");
const eng = require("../data/engine/ucsb-es.json");

const catalog = {};
eng.courses.forEach((c) => { catalog[E.normCode(c.code)] = c; });

function placedMap(plan) {
  const m = {};
  plan.terms.forEach((t, i) => t.courses.forEach((c) => { m[E.normCode(c.code)] = i; }));
  return m;
}
function checkOrder(plan, have) {
  /* 对每个已排课程：其先修树在更早学期已满足，或缺失部分已在 warnings 中声明 */
  const placed = placedMap(plan);
  const haveSet = new Set((have || []).map(E.normCode));
  const scheduled = new Set(Object.keys(placed));
  let checked = 0;
  plan.terms.forEach((t, ti) => t.courses.forEach((c) => {
    const cat = catalog[E.normCode(c.code)];
    if (!cat || c.generic) return;
    const tree = E.parsePrereq(cat.prerequisites_raw || "");
    if (!tree || tree.fallback) return;
    checked++;
    /* 用三值语义复核：AND 子项须 SAT 或 EXTERNAL；OR 须有 SAT 或全 EXTERNAL */
    const status = (function st(node) {
      if (!node) return "SAT";
      if (node.code) {
        const nc = E.normCode(node.code);
        if (haveSet.has(nc)) return "SAT";
        if (placed[nc] !== undefined && placed[nc] < ti) return "SAT";
        if (scheduled.has(nc)) return "PENDING";
        return "EXTERNAL";
      }
      if (node.wildcard !== undefined) {
        let sat = false, pend = false;
        Object.keys(placed).forEach((k) => {
          const m = k.match(/^(.+?)\s+(\d+)([A-Z]*)$/);
          if (m && (!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0) && placed[k] < ti) sat = true;
          if (m && (!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0) && placed[k] >= ti) pend = true;
        });
        if (sat) return "SAT";
        if (pend) return "PENDING";
        return "EXTERNAL";
      }
      const ss = node.items.map(st);
      if (node.op === "AND") return ss.includes("PENDING") ? "PENDING" : "SAT";
      return ss.includes("SAT") ? "SAT" : (ss.includes("PENDING") ? "PENDING" : "EXTERNAL");
    })(tree);
    assert.notStrictEqual(status, "PENDING", `${c.code} 在第 ${ti} 学期排入时先修未满足`);
  }));
  return checked;
}

function run(name, input, asserts) {
  const plan = E.buildPlan(input, { major, catalog });
  console.log(`--- ${name}: feasible=${plan.feasible} terms=${plan.terms.length} totalUnits=${plan.totalUnits} unscheduled=${plan.unscheduled.length} criticalPath=${plan.criticalPathTerms} minTermsByLoad=${plan.minTermsByLoad}`);
  asserts(plan);
  return plan;
}

/* 1）3 年、每学期 20 学分：按 2026-27 数据与 GE 双计，计划约 183 学分，9 学期×20 学分 = 180 容量，
 *    差 3 学分排不下——引擎应如实报不可行，并给出差额（这是正确行为，不是 bug） */
run("3yr cap20 (infeasible by design)", { years: 3, maxUnits: 20, startTerm: 0, have: [] }, (plan) => {
  assert.strictEqual(plan.feasible, false, "3 年 20 学分应排不下（183 > 180）");
  assert.ok(plan.extraTerms >= 1, "应报出差额学期数");
  assert.ok(plan.unscheduled.length > 0, "应列出未排入课程");
  const p3 = plan;
  /* 即使不可行，已排部分仍应满足先修顺序与学分上限 */
  p3.terms.forEach((t) => assert.ok(t.units <= 20, `学期 ${t.label} 超学分上限：${t.units}`));
  checkOrder(p3, []);
});

/* 1b）3 年、每学期 21 学分：应可行（183 ≤ 189），且优化器应选 GE 最优组合 */
const p3 = run("3yr cap21", { years: 3, maxUnits: 21, startTerm: 0, have: [] }, (plan) => {
  assert.strictEqual(plan.feasible, true, "3 年 21 学分应可行，未排入：" + plan.unscheduled.join("、"));
  assert.ok(plan.terms.length <= 9, "学期数 ≤9");
  plan.terms.forEach((t) => assert.ok(t.units <= 21, `学期 ${t.label} 超学分上限：${t.units}`));
  assert.strictEqual(plan.totalUnits, 183, `总学分应为 183（专业 162 + GE 新增 21），实际 ${plan.totalUnits}`);
  /* 专业要求全覆盖：每条非选修要求至少 1 门；B-1 ≥32 学分；C 区 4 块 */
  plan.coverage.major.forEach((r) => assert.ok(r.courses.length > 0, `专业要求 ${r.id} 未覆盖`));
  const b1 = plan.coverage.major.find((r) => r.id === "b-1");
  const b1Units = b1.courses.reduce((s, c) => s + E.unitsNum((catalog[E.normCode(c)] || {}).units), 0);
  assert.ok(b1Units >= 32, `B-1 应 ≥32 学分，实际 ${b1Units}`);
  assert.ok(b1.courses.every((c) => E.unitsNum((catalog[E.normCode(c)] || {}).units) > 0), "B-1 不应含 0 学分课");
  /* 一课不双计：专业覆盖中无重复代码 */
  const seen = new Set();
  plan.coverage.major.forEach((r) => r.courses.forEach((c) => {
    if (c.indexOf("C 区") === 0) return;
    const nc = E.normCode(c);
    assert.ok(!seen.has(nc), `课程 ${nc} 被两个专业要求复用`);
    seen.add(nc);
  }));
  /* 优化器行为：微积分取 3A+3B（8 学分 < 2A+2B 10 学分）；A-2 只取 1 门（126 永久号）；
   * 专题预备取 RG ST 14（ETH+AHI+Writing 三重覆盖）、7 选 1 取 PHIL 4（E 区） */
  const byId = Object.fromEntries(plan.coverage.major.map((r) => [r.id, r.courses]));
  assert.deepStrictEqual(byId["calculus"].map(E.normCode).sort(), ["MATH 3A", "MATH 3B"], "微积分应取 3A+3B");
  assert.deepStrictEqual(byId["2"].map(E.normCode), ["ENV S 126"], "A-2 应只取 126");
  assert.deepStrictEqual(byId["preparation-for-the-major-2"].map(E.normCode), ["RG ST 14"], "16 选 1 应取 RG ST 14");
  assert.deepStrictEqual(byId["preparation-for-the-major"].map(E.normCode), ["PHIL 4"], "7 选 1 应取 PHIL 4");
  /* GE 覆盖：C/D/E 各有课；F/G/A 指定课在计划中 */
  const ge = Object.fromEntries(plan.coverage.ge.map((r) => [r.id, r.courses]));
  assert.ok(ge.areaC.length > 0 && ge.areaD.length > 0 && ge.areaE.length > 0, "GE C/D/E 应有覆盖");
  const allScheduled = new Set();
  plan.terms.forEach((t) => t.courses.forEach((c) => allScheduled.add(E.normCode(c.code))));
  ["WRIT 2", "WRIT 107EP", "ENV S 136O", "ENV S 160"].forEach((c) => assert.ok(allScheduled.has(E.normCode(c)), `GE 指定课 ${c} 应在计划中`));
  /* 关键课含 EEMB 2（最大扇出） */
  assert.ok(plan.keyCourses.some((k) => E.normCode(k.code) === "EEMB 2"), "关键课应含 EEMB 2");
  const n = checkOrder(plan, []);
  console.log(`    order-checked courses: ${n}`);
});

/* 2）4 年、每学期 15 学分：12×15 = 180 < 183，同样差 3 学分排不下 */
run("4yr cap15 (infeasible by design)", { years: 4, maxUnits: 15, startTerm: 0, have: [] }, (plan) => {
  assert.strictEqual(plan.feasible, false, "4 年 15 学分应排不下（183 > 180）");
  assert.ok(plan.extraTerms >= 1, "应报出差额学期数");
});

/* 2b）4 年、每学期 16 学分：宽松场景应可行且学期更轻 */
run("4yr cap16", { years: 4, maxUnits: 16, startTerm: 0, have: [] }, (plan) => {
  assert.strictEqual(plan.feasible, true, "4 年 16 学分应可行，未排入：" + plan.unscheduled.join("、"));
  plan.terms.forEach((t) => assert.ok(t.units <= 16, `学期 ${t.label} 超学分上限：${t.units}`));
  checkOrder(plan, []);
});

/* 3）3 年、每学期 12 学分：应不可行，并给出建议年数 */
run("3yr cap12 (infeasible)", { years: 3, maxUnits: 12, startTerm: 0, have: [] }, (plan) => {
  assert.strictEqual(plan.feasible, false, "3 年 12 学分应排不下");
  assert.ok(plan.suggestedYears > 3, "应建议更长年数");
  assert.ok(plan.unscheduled.length > 0, "应列出未排入课程");
});

/* 4）已修课程：已修 ENV S 1/2/3 + CHEM 1A 应减少总学分、不重排 */
run("3yr with have", { years: 3, maxUnits: 20, startTerm: 0, have: ["ENV S 1", "ENV S 2", "ENV S 3", "CHEM 1A"] }, (plan) => {
  assert.strictEqual(plan.feasible, true, "含已修的 3 年计划应可行");
  const allScheduled = new Set();
  plan.terms.forEach((t) => t.courses.forEach((c) => allScheduled.add(E.normCode(c.code))));
  ["ENV S 1", "ENV S 2", "ENV S 3", "CHEM 1A"].forEach((c) => assert.ok(!allScheduled.has(E.normCode(c)), `已修 ${c} 不应重排`));
  assert.ok(plan.totalUnits < p3.totalUnits, `已修应减少总学分（${plan.totalUnits} < ${p3.totalUnits}）`);
  checkOrder(plan, ["ENV S 1", "ENV S 2", "ENV S 3", "CHEM 1A"]);
});

/* 5）外语 UCSB 修课途径：4 年计划中应含 3 门外语块 */
run("4yr langAtUCSB", { years: 4, maxUnits: 20, startTerm: 0, have: [], langAtUCSB: true }, (plan) => {
  assert.strictEqual(plan.feasible, true, "4 年外语途径应可行，未排入：" + plan.unscheduled.join("、"));
  assert.ok(plan.terms.some((t) => t.courses.some((c) => c.code.indexOf("外语") === 0)), "外语块应在计划中");
});

console.log("engine tests OK");
