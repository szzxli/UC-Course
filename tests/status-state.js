/* 状态核验指纹（B2）：none -> ok -> stale 转换 + 草稿不计入指纹 */
"use strict";
const fs = require("fs");
const store = {};
global.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
const code = fs.readFileSync(__dirname + "/../web/js/app.js", "utf8").replace('"use strict";', "");
(0, eval)(code);
let pass = 0, fail = 0;
function check(label, cond) {
  if (cond) { pass++; }
  else { fail++; console.log("FAIL:", label); }
}
check("initial none", statusState().state === "none");
Sset("campus", "UCSB"); Sset("major", "ucsb-environmental-science.json"); Sset("goal", "grad");
Sset("have", { "ENV S 1": true, "CHEM 1A": true }); Sset("transferCC", "De Anza");
check("before confirm none", statusState().state === "none");
Sset("statusCheck", { at: "2026-10-28T00:00:00.000Z", fp: statusFingerprint() });
check("after confirm ok", statusState().state === "ok");
Sset("have", { "ENV S 1": true, "CHEM 1A": true, "ENV S 2": true });
check("have change -> stale", statusState().state === "stale");
Sset("have", { "ENV S 1": true, "CHEM 1A": true });
check("revert -> ok", statusState().state === "ok");
Sset("major2", "ucsb-mathematics.json");
check("major2 change -> stale", statusState().state === "stale");
Sset("statusCheck", { at: "2026-10-28T00:00:00.000Z", fp: statusFingerprint() });
Sset("myCourses", [{ code: "X" }]);
check("draft change keeps ok", statusState().state === "ok");
Sset("goal", "job");
check("goal change -> stale", statusState().state === "stale");
console.log(`STATUS: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
