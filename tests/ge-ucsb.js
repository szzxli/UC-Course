/* UC-Course UCSB GE 接入验证：结构 + 中文层 + 课程代码覆盖 */
"use strict";
const fs = require("fs");
const path = require("path");
const WEB = "/home/hatch/workspace/uc-course/web";
const DATA = "/home/hatch/workspace/uc-course";
function load(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
function norm(s) { return String(s || "").trim().replace(/\b0+(\d)/g, "$1").replace(/\s+/g, " "); }
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

console.log("== UCSB GE 数据 ==");
const src = load(path.join(DATA, "data/ge/ucsb.json"));
const web = load(path.join(WEB, "data/ge/ucsb.json"));
ok("source 与 web 副本一致", JSON.stringify(src) === JSON.stringify(web));
ok("campus=UCSB degree=B.S.", src.campus === "UCSB" && src.degree === "B.S.");
ok("4 个 section", src.sections.length === 4, src.sections.map(s => s.id).join(","));
const reqs = src.sections.flatMap(s => s.requirements);
ok("15 项要求", reqs.length === 15, String(reqs.length));
ok("每项有 name_zh", reqs.every(r => r.name_zh));
ok("每项有 note 就有 note_zh", reqs.every(r => !r.note || r.note_zh));
ok("每 section 有 title_zh + note_zh", src.sections.every(s => s.title_zh && s.note_zh));
const byId = Object.fromEntries(reqs.map(r => [r.id, r]));
ok("A1 3 门 WRIT 2/2E/2LK", JSON.stringify(byId.a1.courses) === JSON.stringify(["WRIT 2", "WRIT 2E", "WRIT 2LK"]));
ok("A1/A2 count=1", byId.a1.count === 1 && byId.a2.count === 1);
ok("C/D/E/F/G 门数 3/2/2/1/1",
   byId.c.count === 3 && byId.d.count === 2 && byId.e.count === 2 && byId.f.count === 1 && byId.g.count === 1);
ok("Special 门数 Writing 6 / NWC 1 / QNT 1 / ETH 1",
   byId.writing.count === 6 && byId["world-cultures"].count === 1 &&
   byId.quantitative.count === 1 && byId.ethnicity.count === 1);
ok("B/ELWR/AHI/IGETC 为说明型（无 count、无课程）",
   ["b", "elwr", "ahi", "igetc"].every(id => byId[id].count == null && byId[id].courses.length === 0));
ok("无 European Traditions 必修项", !reqs.some(r => r.id.includes("european")));

console.log("== 课程代码覆盖（对照 2026-27 目录） ==");
const full = load(path.join(DATA, "data/raw/ucsb-courses.json"));
const codes = new Set(full.map(c => norm(c.code)));
const listed = reqs.flatMap(r => r.courses || []);
const missing = listed.filter(c => !codes.has(norm(c)));
ok("A1/A2 全部课程在目录中", missing.length === 0, missing.join(","));
ok("A2 含 ENGL 10 系列", ["ENGL 10", "ENGL 10AC", "ENGL 10EM", "ENGL 10LC"].every(c => byId.a2.courses.includes(c)));

console.log("== GE 页与导航（四页整合后：GE 为毕业要求页的一区） ==");
const reqHtml = fs.readFileSync(path.join(WEB, "requirements.html"), "utf8");
ok("requirements.html 经 geFile() 读 data/ge/（非 UCSD 仍为 campus 小写，UCSD 为 ucsd-学院）",
  reqHtml.includes('fetch("data/ge/" + geFile() + ".json")') &&
  reqHtml.includes('if (CAMPUS === "UCSD") return "ucsd-" + Sget("ucsdCollege", "revelle")') &&
  reqHtml.includes('return CAMPUS.toLowerCase();'));
ok("requirements.html 含 4-tab 导航", (reqHtml.match(/data-page="/g) || []).length === 4);
ok("requirements.html 含 GE 区", reqHtml.includes('id="sec-ge"'));
for (const p of ["index.html", "courses.html", "plan.html"]) {
  const s = fs.readFileSync(path.join(WEB, p), "utf8");
  ok(p + " 有毕业要求 tab", s.includes('href="requirements.html" data-page="requirements"'));
}
for (const loc of ["zh-CN", "zh-TW", "en", "es"]) {
  const d = load(path.join(WEB, "data/i18n", loc + ".json"));
  ok(loc + " i18n 含 nav.ge + ge.*", !!d.nav.ge && !!d.ge.pickCount && !!d.ge.openPool && !!d.index.geTitle && !!d.major.goGe);
}

console.log(`\nGE: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
