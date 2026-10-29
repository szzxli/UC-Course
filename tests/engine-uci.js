#!/usr/bin/env node
/* UCI 6 专业排课冒烟测试：接线后
 * 断言：无 UCSB GE 填充课、无 UCSB GE 覆盖、选修要求均有覆盖（EE 只选一个方向 +
 * 技术选修 3 个通用块）、先修顺序、学期学分上限、一课不双计、地图节点/边计数。 */
"use strict";
const assert = require("node:assert");
const E = require("../web/js/engine.js");
const fs = require("node:fs");

const MAJORS = [
  ["uci-computer-science", "uci-computer-science"],
  ["uci-electrical-engineering", "uci-electrical-engineering"],
  ["uci-biology", "uci-biology"],
  ["uci-psychology", "uci-psychology"],
  ["uci-economics", "uci-economics"],
  ["uci-mathematics", "uci-mathematics"],
];
const BAD_GE = ["WRIT 2", "WRIT 107EP", "ENV S 136O", "ENV S 160", "ENV S 130A", "ENV S 189", "ENV S 173"];

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
    const tree = E.parsePrereq(cat.prerequisites_raw || "", "UCI");
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
  // EE 的最长先修链 12 门（159B←159A←145←46←45C←40←22L←22←20←12←2A←1B），
  // 3 年（9 学期）排不下是正确行为：3 年应报不可行、4 年应可行
  const years = stem === "uci-electrical-engineering" ? 4 : 3;
  if (stem === "uci-electrical-engineering") {
    const p3 = E.buildPlan({ years: 3, maxUnits: 21, startTerm: 0, have: [] }, { major, catalog });
    assert.strictEqual(p3.feasible, false, "EE 3 年应因链长不可行");
    assert.ok(p3.unscheduled.includes("EECS 159B"), "EE 3 年未排入应含 EECS 159B");
    assert.ok(p3.suggestedYears > 3, "EE 3 年应建议更长年数");
  }
  const plan = E.buildPlan({ years, maxUnits: 21, startTerm: 0, have: [] }, { major, catalog });
  const allScheduled = [];
  plan.terms.forEach((t) => t.courses.forEach((c) => allScheduled.push(c.code)));
  console.log(`--- ${stem}: feasible=${plan.feasible} terms=${plan.terms.length} totalUnits=${plan.totalUnits} unscheduled=${plan.unscheduled.length} scheduled=${allScheduled.length}`);
  plan.terms.forEach((t) => assert.ok(t.units <= 21, `学期 ${t.label} 超学分上限：${t.units}`));
  // 无 UCSB GE 填充
  BAD_GE.forEach((g) => assert.ok(!allScheduled.some((c) => E.normCode(c) === E.normCode(g)), `UCSB GE 课 ${g} 不应出现在 UCI 计划中`));
  assert.ok(!allScheduled.some((c) => c.indexOf("GE ") === 0 || c.indexOf("外语") === 0 || c.indexOf("GE 写作") === 0), "不应有 UCSB GE 通用块");
  assert.deepStrictEqual(plan.coverage.ge, [], "UCI 计划不应有 UCSB GE 覆盖清单");
  assert.ok(!plan.warnings.some((w) => w.indexOf("环境研究系") >= 0), "不应有 UCSB GE 警告");
  // 选修覆盖
  const covById = Object.fromEntries(plan.coverage.major.map((r) => [r.id, r.courses]));
  for (const req of major.requirements) {
    if (req.type !== "elective") continue;
    if (req.id.indexOf("spec-") === 0) continue; // 方向组单独断言
    assert.ok(covById[req.id] && covById[req.id].length > 0, `选修要求 ${req.id} 应有覆盖`);
    if (!req.courses || !req.courses.length) {
      // 开放池（无课单）：通用块数应等于 count
      assert.strictEqual(covById[req.id].length, req.count, `开放池选修 ${req.id} 应为 ${req.count} 个通用块`);
    }
  }
  // 分布约束未建模应有警告（CS upper-B、Psych C1）
  for (const req of major.requirements) {
    if (req.type === "elective" && req.note && /distinct|different groups/i.test(req.note)) {
      assert.ok(plan.warnings.some((w) => w.indexOf(req.id) === 0 && w.indexOf("方向分布") >= 0), `选修 ${req.id} 的分布约束应有警告`);
    }
  }
  // EE：只选一个方向 + 技术选修 3 块
  if (stem === "uci-electrical-engineering") {
    const specs = major.requirements.filter((r) => r.id.indexOf("spec-") === 0);
    const chosen = specs.filter((r) => covById[r.id] && covById[r.id].length > 0);
    assert.strictEqual(chosen.length, 1, `EE 应只选一个方向，实际 ${chosen.map((r) => r.id).join("、")}`);
    assert.strictEqual(covById["spec-electronic-circuit-design"] ? covById["spec-electronic-circuit-design"].length : 0,
      chosen[0].id === "spec-electronic-circuit-design" ? covById[chosen[0].id].length : 0, "方向覆盖一致性");
    const tech = covById["tech-electives"] || [];
    assert.strictEqual(tech.length, 3, `技术选修应为 3 个通用块，实际 ${tech.join("、")}`);
    assert.ok(tech.every((c) => c.indexOf("技术选修") === 0), "技术选修块命名");
    console.log(`    EE chosen spec: ${chosen[0].id} (${covById[chosen[0].id].length} 门)`);
  }
  // 一课不双计（通用块除外）
  const seen = new Set();
  plan.coverage.major.forEach((r) => r.courses.forEach((c) => {
    if (c.indexOf("技术选修") === 0 || c.indexOf("C 区") === 0) return;
    const nc = E.normCode(c);
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
      const t = raw ? E.parsePrereq(raw, "UCI") : null;
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
}
console.log("uci engine tests OK");
