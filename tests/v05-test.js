/* UC-Course v0.5 实测：真实数据端到端验证 */
"use strict";
const fs = require("fs");
const path = require("path");
const WEB = "/home/hatch/workspace/uc-course/web";
const RAW = "/home/hatch/workspace/uc-course/data/raw";

function load(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
function norm(s) { return String(s || "").trim().replace(/\b0+(\d)/g, "$1").replace(/\s+/g, " "); }
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

/* planner.js 逻辑（vm 载入全局，避开 module 导出） */
const vm = require("vm");
const psrc = fs.readFileSync(path.join(WEB, "js/planner.js"), "utf8")
  .replace(/if \(typeof module.*$/, "");
vm.runInThisContext(psrc, { filename: "planner.js" });

console.log("== 1. 专业数据完整性 ==");
const midx = load(path.join(WEB, "data/majors/index.json"));
ok("18 majors in index", midx.length === 18, "got " + midx.length);
let allReqCourses = {};
midx.forEach(m => {
  const md = load(path.join(WEB, "data/majors", m.file));
  ok(m.file + " schema", !!(md.major && md.requirements && md.requirements.length), "");
  (md.requirements || []).forEach(r => {
    ok(m.file + "/" + r.id + " type valid", ["required", "elective", "prereq"].includes(r.type), r.type);
    (r.courses || []).forEach(c => { allReqCourses[m.campus + "|" + norm(c)] = true; });
  });
});

console.log("== 2. 双专业重叠 (UCSD Math + UCSD CS) ==");
function reqAll(md, r) {
  const s = {};
  (r.courses || []).forEach(c => { s[norm(c)] = c; });
  (r.options || []).forEach(g => g.forEach(c => { s[norm(c)] = c; }));
  return Object.keys(s).map(k => s[k]);
}
function reqSet(md) {
  const s = {};
  (md.requirements || []).forEach(r => reqAll(md, r).forEach(c => {
    const k = norm(c); (s[k] = s[k] || []).push(r.name);
  }));
  return s;
}
const math = load(path.join(WEB, "data/majors/ucsd-mathematics.json"));
const cs = load(path.join(WEB, "data/majors/ucsd-computer-science.json"));
const s1 = reqSet(math), s2 = reqSet(cs);
const ov = Object.keys(s1).filter(k => s2[k]);
ok("overlap found", ov.length > 0, "n=" + ov.length);
console.log("  overlap sample:", ov.slice(0, 8).join(", "));
ok("overlap has MATH 18/20A", ov.includes("MATH 18") || ov.includes("MATH 20A"), ov.slice(0,5).join(","));

console.log("== 3. 排课实测 (UCSD Math 必修, maxU=16) ==");
/* 载入 UCSD 搜索索引做先修回填 */
const man = load(path.join(WEB, "data/search/ucsd/manifest.json"));
let cmap = {};
man.files.forEach(f => {
  load(path.join(WEB, "data/search/ucsd", f)).forEach(c => { cmap[norm(c.code)] = c; });
});
console.log("  index courses:", Object.keys(cmap).length);
let plan = [];
math.requirements.filter(r => r.type === "required").forEach(r =>
  reqAll(math, r).forEach(c => {
    const k = norm(c);
    if (plan.some(x => norm(x.code) === k)) return;
    const e = cmap[k];
    plan.push({ code: c, u: e ? e.u : "4", pre: e ? (e.pre || []) : [] });
  }));
console.log("  required courses in plan:", plan.length);
const missingPre = plan.filter(c => { const e = cmap[norm(c.code)]; return !e; });
console.log("  courses w/o index data:", missingPre.length, missingPre.map(c=>c.code).join(","));
const r = scheduleQuarters(plan, 16, 12, { missingPrereq(){return "";}, noRoom(){return "";} });
const scheduled = [];
r.quarters.forEach((q, i) => q.courses.forEach(c => scheduled.push({ code: c, q: i })));
ok("all courses scheduled", scheduled.length === plan.length, scheduled.length + "/" + plan.length);
const pos = {}; scheduled.forEach(s => pos[norm(s.code)] = s.q);
let preViol = [];
plan.forEach(c => (c.pre || []).forEach(p => {
  const pk = norm(p);
  if (pos[pk] !== undefined && pos[pk] >= pos[norm(c.code)]) preViol.push(c.code + "<-" + p);
}));
ok("no prereq violations", preViol.length === 0, preViol.slice(0,3).join("; "));
let overCap = [];
r.quarters.forEach((q, i) => { if (q.units > 16) overCap.push("Q" + i + ":" + q.units); });
ok("no quarter over 16u", overCap.length === 0, overCap.join(","));
const cp = criticalPath(plan);
console.log("  critical path: minQuarters=" + cp.minQuarters + " chain=" + cp.chain.slice(0,6).join("->") + (cp.chain.length>6?"...":""));
ok("critical path sane", cp.minQuarters >= 2 && cp.minQuarters <= 12, "");

console.log("== 4. 时间线数学 ==");
const units = plan.reduce((s, c) => s + parseUnits(c.u), 0);
[2,3,4].forEach(y => {
  const q = y * 3, pace = units / q, hrs = pace * 3;
  console.log(`  ${y}yr: ${q}q pace=${pace.toFixed(1)}u/wk-hrs=${Math.round(hrs)} minQ=${cp.minQuarters} -> ${cp.minQuarters > q ? "INFEASIBLE" : pace > 16 ? "TIGHT" : "OK"}`);
});

console.log("== 5. AP/CC 徽标解析 ==");
const cidx = load(path.join(WEB, "data/credits/index.json"));
let badgeCodes = new Set();
["UCI","UCSD"].forEach(cp2 => {
  (cidx[cp2].ap || []).forEach(f => load(path.join(WEB, "data/credits", f)).forEach(a =>
    (a.courses || []).forEach(c => badgeCodes.add(cp2 + "|" + norm(c)))));
  (cidx[cp2].cc || []).forEach(f => { const o = load(path.join(WEB, "data/credits", f)); Object.keys(o).forEach(c => badgeCodes.add(cp2 + "|" + norm(c))); });
});
console.log("  badge courses:", badgeCodes.size);
let badgeNoData = [];
badgeCodes.forEach(k => {
  const [cp2, code] = k.split("|");
  const raw = load(path.join(RAW, cp2.toLowerCase() + "-courses.json"));
  if (!raw.some(c => norm(c.code) === code)) badgeNoData.push(code);
});
ok("badge codes resolve (<=4 known prereq-only)", badgeNoData.length <= 4, badgeNoData.join(","));

console.log("== 6. have-set 排除 ==");
const have = { "MATH 20A": true, "MATH 20B": true };
const plan2 = plan.filter(c => !have[norm(c.code)]);
const r2 = scheduleQuarters(plan2, 16, 12, { missingPrereq(){return "";}, noRoom(){return "";} });
const s2n = r2.quarters.reduce((s,q)=>s+q.courses.length,0);
ok("have-set excluded from schedule", s2n === plan2.length && !r2.quarters.some(q=>q.courses.includes("MATH 20A")), s2n + "/" + plan2.length);

console.log(`\nRESULT: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
