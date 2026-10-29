/* UC-Course UCSD 七学院 GE 接入验证：结构 + 中文层 + 关键课单 + 快照覆盖（仅报告） */
"use strict";
const fs = require("fs");
const path = require("path");
const WEB = "/home/hatch/workspace/uc-course/web";
const DATA = "/home/hatch/workspace/uc-course";
function load(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}
function norm(s) { return String(s || "").trim().replace(/-/g, " ").replace(/\s+/g, " ").toUpperCase(); }

const EXPECT = {
  revelle: { sections: 7, reqs: 7 },
  muir: { sections: 3, reqs: 6 },
  marshall: { sections: 7, reqs: 7 },
  warren: { sections: 4, reqs: 6 },
  roosevelt: { sections: 8, reqs: 8 },
  sixth: { sections: 3, reqs: 10 },
  seventh: { sections: 3, reqs: 7 },
};
const snap = load(path.join(DATA, "data/raw/ucsd-courses.json"));
const have = new Set(snap.map((c) => norm(c.code)));

for (const [key, exp] of Object.entries(EXPECT)) {
  console.log("== ucsd-" + key + " ==");
  const src = load(path.join(DATA, "data/ge/ucsd-" + key + ".json"));
  const web = load(path.join(WEB, "data/ge/ucsd-" + key + ".json"));
  ok("source 与 web 副本一致", JSON.stringify(src) === JSON.stringify(web));
  ok("campus=UCSD", src.campus === "UCSD");
  ok("checked=2026-10-28", src.checked === "2026-10-28");
  ok(exp.sections + " 个 section", src.sections.length === exp.sections,
     src.sections.map((s) => s.id).join(","));
  const reqs = src.sections.flatMap((s) => s.requirements);
  ok(exp.reqs + " 项要求", reqs.length === exp.reqs, String(reqs.length));
  ok("每 section 有 title_zh + note_zh",
     src.sections.every((s) => s.title_zh && s.note_zh));
  ok("每项有 name_zh", reqs.every((r) => r.name_zh));
  ok("每项有 note 就有 note_zh", reqs.every((r) => !r.note || r.note_zh));
  const byId = Object.fromEntries(reqs.map((r) => [r.id, r]));
  if (key === "revelle") {
    ok("HUM 1-5", JSON.stringify(byId.hum.courses) === JSON.stringify(["HUM 1", "HUM 2", "HUM 3", "HUM 4", "HUM 5"]));
    ok("数学 count=3 含 MATH 10A/20A", byId.math.count === 3 && byId.math.courses.includes("MATH 10A") && byId.math.courses.includes("MATH 20A"));
    ok("自然科学 count=5 含 BILD/CHEM/PHYS", byId.natsci.count === 5 && byId.natsci.courses.includes("BILD 1") && byId.natsci.courses.includes("CHEM 6A") && byId.natsci.courses.includes("PHYS 2A"));
    ok("社会科学 count=2", byId.social.count === 2);
  }
  if (key === "muir") {
    ok("MCWP 40/50", JSON.stringify(byId.mcwp.courses) === JSON.stringify(["MCWP 40", "MCWP 50"]));
    ok("序列 3+3+6", byId["seq-i"].count === 3 && byId["seq-ii"].count === 3 && byId["seq-iii"].count === 6);
  }
  if (key === "marshall") {
    ok("DOC 1/2/3", JSON.stringify(byId.doc.courses) === JSON.stringify(["DOC 1", "DOC 2", "DOC 3"]));
    ok("自然科学 count=3", byId.natsci.count === 3);
    ok("广度 count=4", byId.breadth.count === 4);
  }
  if (key === "warren") {
    ok("WCWP 10A/10B", JSON.stringify(byId.wcwp.courses) === JSON.stringify(["WCWP 10A", "WCWP 10B"]));
    ok("伦理 PHIL/POLI 27/28", byId.ethics.courses.includes("PHIL 27") && byId.ethics.courses.includes("POLI 28"));
    ok("专攻 12 / 区域 6", byId.poc.count === 12 && byId.area.count === 6);
  }
  if (key === "roosevelt") {
    ok("MMW 11-15", JSON.stringify(byId.mmw.courses) === JSON.stringify(["MMW 11", "MMW 12", "MMW 13", "MMW 14", "MMW 15"]));
    ok("定量 count=2 自然 count=2", byId.quant.count === 2 && byId.natsci.count === 2);
    ok("PHYS 5/7/9/13 已停开不列入", !byId.natsci.courses.some((c) => ["PHYS 5", "PHYS 7", "PHYS 9", "PHYS 13"].includes(c)));
    ok("区域 count=3", byId.regional.count === 3);
  }
  if (key === "sixth") {
    ok("CAT 1/2/3", JSON.stringify(byId.cat.courses) === JSON.stringify(["CAT 1", "CAT 2", "CAT 3"]));
    ok("广度 1+2+2+2+1+1+2=11", byId.it.count === 1 && byId.social.count === 2 && byId.narrative.count === 2 && byId.analytical.count === 2 && byId.structured.count === 1 && byId.data.count === 1 && byId.artmaking.count === 2);
    ok("CAT 125", byId.cat125.courses.includes("CAT 125"));
  }
  if (key === "seventh") {
    ok("SYN 1/2/100", JSON.stringify(byId.syn.courses) === JSON.stringify(["SYN 1", "SYN 2", "SYN 100"]));
    ok("备选 5 区各 2", ["alt-arts", "alt-humanities", "alt-nateng", "alt-quant", "alt-social"].every((id) => byId[id].count === 2));
    ok("高影响 count=1", byId.highimpact.count === 1);
  }
  const miss = [...new Set(reqs.flatMap((r) => r.courses))].filter((c) => !have.has(norm(c)));
  console.log("  INFO snapshot-missing (" + miss.length + "): " + miss.join(", "));
}

console.log(fail === 0 ? "ucsd ge tests OK" : "ucsd ge tests FAILED: " + fail);
process.exit(fail === 0 ? 0 : 1);
