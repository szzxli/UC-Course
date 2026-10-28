/* UC-Course UCSB 接入验证：数据完整性 + web 加载路径模拟 + 排课引擎实测 */
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

const vm = require("vm");
const psrc = fs.readFileSync(path.join(WEB, "js/planner.js"), "utf8")
  .replace(/if \(typeof module.*$/, "");
vm.runInThisContext(psrc, { filename: "planner.js" });

console.log("== 1. UCSB 原始数据完整性 ==");
const idx = load(path.join(RAW, "index.json"));
const full = load(path.join(RAW, "ucsb-courses.json"));
ok("index total_courses.ucsb == ucsb-courses.json length",
   idx.total_courses.ucsb === full.length, idx.total_courses.ucsb + " vs " + full.length);
let shardSum = 0;
idx.ucsb.forEach(f => { shardSum += load(path.join(RAW, f)).length; });
ok("shard sum == total", shardSum === idx.total_courses.ucsb, shardSum + "");
ok("all courses campus=UCSB + schema keys", full.every(c =>
  c.campus === "UCSB" && ["dept", "code", "title", "units", "description",
    "prerequisites_raw", "prerequisites_courses"].every(k => k in c)), "");
const withPre = full.filter(c => c.prerequisites_courses.length).length;
console.log("  courses with parsed prereqs:", withPre);

console.log("== 2. web 搜索索引（courses.html 加载路径） ==");
const man = load(path.join(WEB, "data/search/ucsb/manifest.json"));
ok("manifest count == total", man.count === idx.total_courses.ucsb, man.count + "");
let INDEX = [];
man.files.forEach(f => { INDEX = INDEX.concat(load(path.join(WEB, "data/search/ucsb", f))); });
ok("idx entries == total", INDEX.length === idx.total_courses.ucsb, INDEX.length + "");
ok("all idx entries c=UCSB", INDEX.every(e => e.c === "UCSB"), "");
function doSearch(q) {
  q = q.trim().toLowerCase();
  return INDEX.filter(c => c.code.toLowerCase().indexOf(q) >= 0 ||
    c.t.toLowerCase().indexOf(q) >= 0).slice(0, 30);
}
ok("search 'CMPSC 16' finds CMPSC 16", doSearch("CMPSC 16").some(c => c.code === "CMPSC 16"), "");
ok("search 'problem solving' finds CMPSC courses",
   doSearch("problem solving").some(c => c.code.indexOf("CMPSC") === 0), "");
ok("search 'POL S 1' finds POL S 1", doSearch("POL S 1").some(c => c.code === "POL S 1"), "");

console.log("== 3. 课程详情（按 f 拉 raw 分片） ==");
const e16 = INDEX.find(c => c.code === "CMPSC 16");
const shard = load(path.join(WEB, "data/raw", e16.f));
const full16 = shard.find(c => c.code === e16.code);
ok("detail record found in shard " + e16.f, !!full16, "");
ok("detail has description + prereq fields",
   !!full16 && typeof full16.description === "string" && Array.isArray(full16.prerequisites_courses), "");
console.log("  CMPSC 16 prereqs:", JSON.stringify(full16 && full16.prerequisites_courses));

console.log("== 4. UCSB 专业（major.html 加载路径） ==");
const midx = load(path.join(WEB, "data/majors/index.json"));
const ucsbMajors = midx.filter(m => m.campus === "UCSB");
ok("7 UCSB majors in index", ucsbMajors.length === 7, "got " + ucsbMajors.length);
const cmapAll = {};
INDEX.forEach(c => { cmapAll[norm(c.code)] = c; });
let missingReqCourses = [];
ucsbMajors.forEach(m => {
  const md = load(path.join(WEB, "data/majors", m.file));
  ok(m.file + " loads, requirements=" + md.requirements.length,
     !!(md.major && md.requirements && md.requirements.length === m.requirement_count), "");
  md.requirements.forEach(r => {
    (r.courses || []).concat((r.options || []).flat()).forEach(c => {
      if (!cmapAll[norm(c)]) missingReqCourses.push(m.file + ": " + c);
    });
  });
});
console.log("  major course refs not in UCSB catalog:", missingReqCourses.length,
  missingReqCourses.slice(0, 10).join(" | "));

console.log("== 5. 排课实测（UCSB CS prereq+required, maxU=16） ==");
const cs = load(path.join(WEB, "data/majors/ucsb-computer-science.json"));
let plan = [];
cs.requirements.filter(r => r.type === "prereq" || r.type === "required").forEach(r => {
  (r.courses || []).forEach(c => {
    const k = norm(c);
    if (plan.some(x => norm(x.code) === k)) return;
    const e = cmapAll[k];
    plan.push({ code: c, u: e ? e.u : "4", pre: e ? (e.pre || []) : [] });
  });
});
console.log("  plan courses:", plan.length);
const r5 = scheduleQuarters(plan, 16, 12, { missingPrereq() { return ""; }, noRoom() { return ""; } });
const scheduled = [];
r5.quarters.forEach((q, i) => q.courses.forEach(c => scheduled.push({ code: c, q: i })));
ok("all courses scheduled", scheduled.length === plan.length, scheduled.length + "/" + plan.length);
let overCap = [];
r5.quarters.forEach((q, i) => { if (q.units > 16) overCap.push("Q" + i + ":" + q.units); });
ok("no quarter over 16u", overCap.length === 0, overCap.join(","));
const pos = {}; scheduled.forEach(s => { pos[norm(s.code)] = s.q; });
let preViol = [];
plan.forEach(c => (c.pre || []).forEach(p => {
  const pk = norm(p);
  if (pos[pk] !== undefined && pos[pk] >= pos[norm(c.code)]) preViol.push(c.code + "<-" + p);
}));
console.log("  prereq ordering notes (incl. possible corequisites):", preViol.length, preViol.slice(0, 5).join("; "));

console.log("\nRESULT: " + pass + " pass, " + fail + " fail");
process.exit(fail ? 1 : 0);
