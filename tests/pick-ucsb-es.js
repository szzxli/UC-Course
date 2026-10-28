/* 选课引擎 v1 测试：合成图 + 真实 ES 数据 */
"use strict";
const fs = require("fs");
const Engine = require("../web/js/engine.js");
const Pick = require("../web/js/pick.js");
let pass = 0, fail = 0;
function check(label, cond) {
  if (cond) { pass++; }
  else { fail++; console.log("FAIL:", label); }
}
function codes(list) { return list.map(function (x) { return x.code; }); }

/* --- 合成图 --- */
const synCat = {
  "CHEM 1A": { code: "CHEM 1A", title: "A", units: "4", prerequisites_raw: "", prerequisites_courses: [] },
  "CHEM 1B": { code: "CHEM 1B", title: "B", units: "4", prerequisites_raw: "CHEM 1A", prerequisites_courses: ["CHEM 1A"] },
  "CHEM 1C": { code: "CHEM 1C", title: "C", units: "4", prerequisites_raw: "CHEM 1B", prerequisites_courses: ["CHEM 1B"] },
  "PHYS 6A": { code: "PHYS 6A", title: "P", units: "4", prerequisites_raw: "MATH 2A or MATH 3A", prerequisites_courses: ["MATH 2A", "MATH 3A"] },
  "GEOG 5": { code: "GEOG 5", title: "G", units: "4", prerequisites_raw: "", prerequisites_courses: ["GEOG 3"] },
  "MATH 2A": { code: "MATH 2A", title: "M2A", units: "4", prerequisites_raw: "", prerequisites_courses: [] },
  "MATH 2B": { code: "MATH 2B", title: "M2B", units: "4", prerequisites_raw: "MATH 2A", prerequisites_courses: ["MATH 2A"] },
  "MATH 3A": { code: "MATH 3A", title: "M3A", units: "4", prerequisites_raw: "", prerequisites_courses: [] },
  "MATH 3B": { code: "MATH 3B", title: "M3B", units: "4", prerequisites_raw: "MATH 3A", prerequisites_courses: ["MATH 3A"] },
  "ECON 1": { code: "ECON 1", title: "E1", units: "4", prerequisites_raw: "", prerequisites_courses: [] },
  "ECON 2": { code: "ECON 2", title: "E2", units: "4", prerequisites_raw: "", prerequisites_courses: [] },
  "ENV S 193DS": { code: "ENV S 193DS", title: "DS", units: "4", prerequisites_raw: "", prerequisites_courses: [] }
};
const chainReq = [{ id: "chain", type: "required", courses: ["CHEM 1A", "CHEM 1B", "CHEM 1C"] }];
let r = Pick.compute({ requirements: chainReq, catalog: synCat, have: [], planned: [] });
check("chain: only 1A recommended", JSON.stringify(codes(r.recommended)) === '["CHEM 1A"]');
check("chain: blocked order 1B before 1C", JSON.stringify(codes(r.blocked)) === '["CHEM 1B","CHEM 1C"]');
check("chain: 1A chainLen 3 fanout 2 key", r.recommended[0].chainLen === 3 && r.recommended[0].fanout === 2 && r.recommended[0].key === true);
check("chain: 1C chainLen 1 fanout 0 not key", r.blocked[1].chainLen === 1 && r.blocked[1].fanout === 0 && r.blocked[1].key === false);

const orReq = [{ id: "or", type: "required", courses: ["PHYS 6A"] }];
r = Pick.compute({ requirements: orReq, catalog: synCat, have: [], planned: [] });
check("or: blocked with hasOr", r.blocked.length === 1 && r.blocked[0].hasOr === true);
check("or: missing lists both", r.blocked[0].missing.indexOf("MATH 2A") >= 0 && r.blocked[0].missing.indexOf("MATH 3A") >= 0);
r = Pick.compute({ requirements: orReq, catalog: synCat, have: ["MATH 3A"], planned: [] });
check("or: satisfied by one branch", codes(r.recommended).indexOf("PHYS 6A") >= 0);

const flatReq = [{ id: "flat", type: "required", courses: ["GEOG 5"] }];
r = Pick.compute({ requirements: flatReq, catalog: synCat, have: [], planned: [] });
check("flat fallback: blocked when raw empty", r.blocked.length === 1);
r = Pick.compute({ requirements: flatReq, catalog: synCat, have: ["GEOG 3"], planned: [] });
check("flat fallback: any-of satisfies", codes(r.recommended).indexOf("GEOG 5") >= 0);

const optReq = [{ id: "calc", type: "required", courses: ["MATH 2A", "MATH 2B", "MATH 3A", "MATH 3B"],
  options: [["MATH 2A", "MATH 2B"], ["MATH 3A", "MATH 3B"]] }];
r = Pick.compute({ requirements: optReq, catalog: synCat, have: ["MATH 2A"], planned: [] });
check("options path chosen: only 2B needed", JSON.stringify(codes(r.recommended).concat(codes(r.blocked))) === '["MATH 2B"]');
r = Pick.compute({ requirements: optReq, catalog: synCat, have: [], planned: [] });
check("options unstarted: all four needed", codes(r.recommended).concat(codes(r.blocked)).sort().join(",") === "MATH 2A,MATH 2B,MATH 3A,MATH 3B");
check("options unstarted: altGroups tagged", r.recommended.every(function (x) { return x.altGroups.length > 0; }));

const takeOneReq = [{ id: "econ", type: "required", courses: ["ECON 1", "ECON 2"], options: [["ECON 1"], ["ECON 2"]] }];
r = Pick.compute({ requirements: takeOneReq, catalog: synCat, have: ["ECON 1"], planned: [] });
check("take-one satisfied", r.recommended.length === 0 && r.blocked.length === 0);

const equivReq = [{ id: "eq", type: "required", courses: ["ENV S 193DS"] }];
r = Pick.compute({ requirements: equivReq, catalog: synCat, have: ["ENV S 126"], planned: [] });
check("equiv partner counts as have", r.recommended.length === 0 && r.blocked.length === 0);

/* --- 真实 ES 数据 --- */
const major = JSON.parse(fs.readFileSync(__dirname + "/../web/data/majors/ucsb-environmental-science.json", "utf8"));
const engData = JSON.parse(fs.readFileSync(__dirname + "/../web/data/engine/ucsb-es.json", "utf8"));
const cat = {};
engData.courses.forEach(function (c) { cat[Engine.normCode(c.code)] = c; });
r = Pick.compute({ requirements: major.requirements, catalog: cat, have: [], planned: [] });
check("real: recommended non-empty", r.recommended.length > 0);
check("real: blocked non-empty", r.blocked.length > 0);
check("real: ENV S 1 recommended (no prereq)", codes(r.recommended).indexOf("ENV S 1") >= 0);
check("real: sorted by chainLen desc", r.recommended.every(function (x, i, a) { return i === 0 || a[i - 1].chainLen >= x.chainLen; }));
check("real: every recommended satisfies its tree", r.recommended.every(function (x) {
  const c = cat[Engine.normCode(x.code)] || {};
  let tree = Engine.parsePrereq(c.prerequisites_raw || "");
  if (tree && tree.fallback) tree = null;
  if (!tree && (c.prerequisites_courses || []).length) {
    const flat = c.prerequisites_courses.map(Engine.normCode);
    tree = flat.length === 1 ? { code: flat[0] } : { op: "OR", items: flat.map(function (cc) { return { code: cc }; }) };
  }
  return Engine.treeSatisfied(tree, new Set());
}));
check("real: B-1 remaining 32 with empty have", r.b1 && r.b1.remaining === 32);
check("real: has C note", r.hasC === true);
const r2 = Pick.compute({ requirements: major.requirements, catalog: cat, have: [], planned: [] });
check("real: deterministic order", JSON.stringify(codes(r.recommended)) === JSON.stringify(codes(r2.recommended)));
const r3 = Pick.compute({ requirements: major.requirements, catalog: cat, have: ["ENV S 1"], planned: [] });
check("real: have course leaves needed set", codes(r3.recommended).indexOf("ENV S 1") < 0 && codes(r3.blocked).indexOf("ENV S 1") < 0);
console.log("real stats: needed=" + r.stats.needed + " rec=" + r.stats.recommended + " blocked=" + r.stats.blocked + " maxChain=" + r.stats.maxChain);
console.log("real top recommended: " + codes(r.recommended).slice(0, 10).join(", "));
console.log(`PICK: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
