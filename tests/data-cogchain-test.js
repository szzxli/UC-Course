/* UC-Course 认知链修复（2026-10-23）数据层针对性用例：
   H2 专业中文层覆盖、K4 先修自含清零、四语词典对齐 + 页面引用键存在性 */
"use strict";
const fs = require("fs");
const path = require("path");
const WEB = "/home/hatch/workspace/uc-course/web";
const ROOT = "/home/hatch/workspace/uc-course";

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}
function load(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
function norm(s) { return String(s || "").trim().replace(/\b0+(\d)/g, "$1").replace(/\s+/g, " "); }

console.log("== H2: 20 个专业要求名/备注中文层 ==");
const midx = load(path.join(WEB, "data/majors/index.json"));
ok("20 majors", midx.length === 20, "got " + midx.length);
midx.forEach(m => {
  const web = load(path.join(WEB, "data/majors", m.file));
  const src = load(path.join(ROOT, "data/majors", m.file));
  ok(m.file + " web/data 与 data 两份同步", JSON.stringify(web) === JSON.stringify(src));
  web.requirements.forEach(r => {
    ok(m.file + "/" + r.id + " name_zh 有中文", !!r.name_zh && /[一-鿿]/.test(r.name_zh), r.name_zh || "(missing)");
    if (r.note) ok(m.file + "/" + r.id + " note_zh 有中文", !!r.note_zh && /[一-鿿]/.test(r.note_zh), "(missing)");
    /* 事实字段未被改动：name/note/courses/options 原样保留的抽查在 git diff 层做，
       这里只保证 zh 字段不覆盖原字段 */
    ok(m.file + "/" + r.id + " name 原文保留", typeof r.name === "string" && r.name.length > 0);
  });
});

console.log("== K4: 三校搜索索引先修自含清零 ==");
["uci", "ucsd", "ucsb"].forEach(camp => {
  const man = load(path.join(WEB, "data/search", camp, "manifest.json"));
  let bad = [], tot = 0;
  man.files.forEach(f => {
    load(path.join(WEB, "data/search", camp, f)).forEach(c => {
      tot++;
      if ((c.pre || []).map(norm).includes(norm(c.code))) bad.push(c.code);
    });
  });
  ok(camp + " 自含 = 0", bad.length === 0, bad.slice(0, 5).join(","));
  ok(camp + " 索引门数与 manifest 一致", tot === man.count, tot + "/" + man.count);
  const raw = load(path.join(ROOT, "data/raw", camp + "-courses.json"));
  const rawBad = raw.filter(c => (c.prerequisites_courses || []).map(norm).includes(norm(c.code)));
  ok(camp + " 原始数据自含 = 0", rawBad.length === 0, rawBad.slice(0, 3).map(c => c.code).join(","));
});

console.log("== i18n: 四语对齐 + 页面引用键存在 ==");
function flat(d, prefix, out) {
  out = out || {};
  Object.keys(d).forEach(k => {
    const kk = prefix ? prefix + "." + k : k;
    if (d[k] && typeof d[k] === "object" && !Array.isArray(d[k])) flat(d[k], kk, out);
    else out[kk] = d[k];
  });
  return out;
}
const dicts = {};
["zh-CN", "en", "zh-TW", "es"].forEach(loc => { dicts[loc] = flat(load(path.join(WEB, "data/i18n", loc + ".json"))); });
const refKeys = Object.keys(dicts["zh-CN"]).sort();
["en", "zh-TW", "es"].forEach(loc => {
  ok(loc + " 与 zh-CN 键集对齐", JSON.stringify(Object.keys(dicts[loc]).sort()) === JSON.stringify(refKeys),
    "n=" + Object.keys(dicts[loc]).length);
});
/* 扫描页面/脚本引用的键：data-i18n、data-i18n-ph、I18N.t("...") 静态部分 */
const srcFiles = ["index.html", "courses.html", "major.html", "plan.html", "trajectory.html", "transfer.html",
  "js/app.js", "js/i18n.js", "js/chat.js", "js/major.js", "js/planner.js"];
const referenced = new Set();
srcFiles.forEach(f => {
  const s = fs.readFileSync(path.join(WEB, f), "utf8");
  let m;
  const re1 = /data-i18n(?:-ph)?="([^"]+)"/g;
  while ((m = re1.exec(s))) referenced.add(m[1]);
  const re2 = /I18N\.t\("([^"]+)"/g;
  while ((m = re2.exec(s))) { if (!/[{]/.test(m[1])) referenced.add(m[1]); }
  const re3 = /t\("(chat\.[^"]+)"/g;
  while ((m = re3.exec(s))) referenced.add(m[1]);
});
/* 动态键（tips.*、plan.yr*、courses.campus*、title/brand/nav 等）单列白名单前缀 */
const dynamicPrefixes = ["tips.", "plan.yr", "courses.campus"];
const missing = [...referenced].filter(k =>
  !(k in dicts["zh-CN"]) && !dynamicPrefixes.some(p => k.startsWith(p)));
ok("页面静态引用键全部存在于词典", missing.length === 0, missing.join(","));
["tips.grad", "tips.job", "tips.undecided", "tips.names.grad", "plan.yr2", "plan.yr3", "plan.yr4",
 "courses.campusUCI", "courses.campusUCSD", "courses.campusUCSB"].forEach(k => {
  ok("动态键存在 " + k, k in dicts["zh-CN"]);
});

console.log(`\nRESULT: ${pass} pass, ${fail} fail`);
process.exit(fail ? 1 : 0);
