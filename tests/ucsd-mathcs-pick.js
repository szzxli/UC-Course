#!/usr/bin/env node
/* UCSD 数学-计算机科学（MA30）智能选课试点测试：
 * 专业文件结构、先修树解析（官方手写树）、选课推荐场景、先修满足判定。 */
"use strict";
const assert = require("node:assert");
const fs = require("node:fs");
const E = require("../web/js/engine.js");
const P = require("../web/js/pick.js");

const major = require("../data/majors/ucsd-mathematics-computer-science.json");
const webMajor = require("../web/data/majors/ucsd-mathematics-computer-science.json");
const eng = require("../data/engine/ucsd-mathcs.json");
const webEng = require("../web/data/engine/ucsd-mathcs.json");

assert.strictEqual(JSON.stringify(major), JSON.stringify(webMajor), "major data/web copies identical");
assert.strictEqual(JSON.stringify(eng), JSON.stringify(webEng), "engine data/web copies identical");
assert.strictEqual(major.requirements.length, 14, "14 requirements");
assert.strictEqual(major.requirements.filter((r) => r.type === "elective").length, 3, "3 elective pools");

const catalog = {};
eng.courses.forEach((c) => { catalog[E.normCode(c.code)] = c; });
assert.strictEqual(eng.courses.length, 34, "34 catalog courses (27 fixed + 7 closure)");

// 先修树：非空原文必须解析出有效树（不 fallback、不为 null），且不含自身
eng.courses.forEach((c) => {
  if (!c.prerequisites_raw) return;
  const t = E.parsePrereq(c.prerequisites_raw);
  assert.ok(t && !t.fallback, c.code + " tree parses");
  assert.ok(!E.treeLeafCodes(t, []).includes(E.normCode(c.code)), c.code + " no self-prereq");
});

// 先修满足判定抽查（官方规则）
function sat(code, have) {
  const t = E.parsePrereq(catalog[E.normCode(code)].prerequisites_raw || "");
  return E.treeSatisfied(t, new Set(have.map(E.normCode)));
}
assert.strictEqual(sat("CSE 100", ["CSE 12", "CSE 15L", "MATH 154"]), true, "CSE 100 via MATH 154");
assert.strictEqual(sat("CSE 100", ["CSE 12", "CSE 15L"]), false, "CSE 100 needs discrete group");
assert.strictEqual(sat("CSE 100", ["CSE 12", "CSE 29", "CSE 21"]), true, "CSE 100 via CSE 21 + CSE 29");
assert.strictEqual(sat("CSE 105", ["CSE 12", "CSE 20", "CSE 21"]), true, "CSE 105 via CSE 20 + CSE 21");
assert.strictEqual(sat("CSE 105", ["CSE 12", "CSE 21"]), false, "CSE 105 needs middle group");
assert.strictEqual(sat("MATH 188", ["MATH 109", "MATH 18", "MATH 100A"]), true, "MATH 188 via 109+18+100A");
assert.strictEqual(sat("MATH 20D", ["MATH 31BH", "MATH 31AH"]), true, "MATH 20D honors path");
assert.strictEqual(sat("MATH 20D", ["MATH 20C", "MATH 18"]), true, "MATH 20D standard path");

// 选课推荐场景
function recCodes(have) {
  return P.compute({ requirements: major.requirements, catalog, have, planned: [] })
    .recommended.map((x) => x.code);
}
assert.deepStrictEqual(
  recCodes([]).sort(),
  ["CSE 11", "MATH 31AH"].sort(),
  "empty have recommends the 2 entry points (MATH 20A now requires MATH 4C or MATH 10A per MATH catalog page, no longer an empty-have entry)"
);
const ldDone = ["MATH 18", "MATH 20A", "MATH 20B", "MATH 20C", "MATH 20D", "MATH 20E",
  "CSE 11", "CSE 15L", "CSE 12"];
const r2 = recCodes(ldDone);
["MATH 109", "MATH 180A", "MATH 183"].forEach((c) => assert.ok(r2.includes(c), "LD done recommends " + c));
const r3 = recCodes(ldDone.concat(["MATH 109"]));
["MATH 100A", "MATH 103A", "MATH 154", "MATH 158", "MATH 184"].forEach((c) =>
  assert.ok(r3.includes(c), "LD+109 recommends " + c));
assert.ok(!recCodes(ldDone).includes("CSE 100"), "CSE 100 blocked until discrete group done");

console.log("UCSD-MATHCS: all assertions passed");
