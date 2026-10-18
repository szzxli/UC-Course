/* UC SmartPick 排课引擎 — 纯逻辑，可单元测试 */
"use strict";

function parseUnits(u) {
  if (u == null) return 4;
  var m = String(u).match(/(\d+(?:\.\d+)?)/g);
  if (!m) return 4;
  var nums = m.map(Number);
  return Math.max.apply(null, nums); /* 区间取上限，保守规划 */
}

/* 拓扑分层：返回每门课的 level（0 = 无先修依赖） */
function topoLevels(courses) {
  var byCode = {}, i, c;
  for (i = 0; i < courses.length; i++) { byCode[courses[i].code] = courses[i]; }
  var level = {}, visiting = {};
  function visit(code, stack) {
    if (level[code] !== undefined) return level[code];
    if (visiting[code]) return 0; /* 环：断开 */
    visiting[code] = true;
    var course = byCode[code], lv = 0, k, p;
    if (course && course.pre) {
      for (k = 0; k < course.pre.length; k++) {
        p = course.pre[k];
        if (byCode[p]) lv = Math.max(lv, visit(p, stack) + 1);
      }
    }
    visiting[code] = false;
    level[code] = lv;
    return lv;
  }
  for (i = 0; i < courses.length; i++) visit(courses[i].code);
  return level;
}

/* 排课：贪心，按拓扑层+课程码排序，每门放进先修已满足且学分未超的最早 quarter
   fmt: 可选 {missingPrereq(code, list), noRoom(code, n)}，默认中文；调用方按 locale 注入 */
function scheduleQuarters(courses, maxUnits, maxQuarters, fmt) {
  maxUnits = maxUnits || 16; maxQuarters = maxQuarters || 12;
  fmt = fmt || {
    missingPrereq: function (code, list) { return code + " 的先修 " + list.join("、") + " 不在选课列表中（假设已修完）"; },
    noRoom: function (code, n) { return code + " 放不进 " + n + " 个 quarter（学分上限太紧）"; }
  };
  var levels = topoLevels(courses);
  var sorted = courses.slice().sort(function (a, b) {
    return (levels[a.code] - levels[b.code]) || (a.code < b.code ? -1 : 1);
  });
  var quarters = []; /* [{units, courses:[]}] */
  var placed = {};   /* code -> quarter idx */
  var warnings = [];
  sorted.forEach(function (c) {
    var need = 0, k, p;
    var missing = [];
    (c.pre || []).forEach(function (pr) {
      if (placed[pr] === undefined) {
        /* 先修不在已选列表里：假设已修完，但提醒 */
        missing.push(pr);
      } else {
        need = Math.max(need, placed[pr] + 1);
      }
    });
    if (missing.length) warnings.push(fmt.missingPrereq(c.code, missing));
    var u = parseUnits(c.u), q = need, done = false;
    while (!done && q < maxQuarters) {
      if (!quarters[q]) quarters[q] = { units: 0, courses: [] };
      if (quarters[q].units + u <= maxUnits) {
        quarters[q].courses.push(c.code);
        quarters[q].units += u;
        placed[c.code] = q;
        done = true;
      } else { q++; }
    }
    if (!done) warnings.push(fmt.noRoom(c.code, maxQuarters));
  });
  return { quarters: quarters, warnings: warnings, levels: levels };
}

if (typeof module !== "undefined") { module.exports = { parseUnits: parseUnits, topoLevels: topoLevels, scheduleQuarters: scheduleQuarters, criticalPath: criticalPath }; }

/* 关键路径：先修链决定的最少 quarter 数 + 最长链条（归一化课号，防环） */
function criticalPath(courses) {
  function nc(s) { return String(s || "").trim().replace(/\b0+(\d)/g, "$1").replace(/\s+/g, " "); }
  var byCode = {}, i;
  for (i = 0; i < courses.length; i++) byCode[nc(courses[i].code)] = courses[i];
  var level = {}, prev = {}, visiting = {};
  function visit(code) {
    if (level[code] !== undefined) return level[code];
    if (visiting[code]) return 0;
    visiting[code] = true;
    var course = byCode[code], lv = 0, k, p, best = null;
    if (course && course.pre) {
      for (k = 0; k < course.pre.length; k++) {
        p = nc(course.pre[k]);
        if (byCode[p]) { var l = visit(p); if (l + 1 > lv) { lv = l + 1; best = p; } }
      }
    }
    visiting[code] = false;
    level[code] = lv; prev[code] = best;
    return lv;
  }
  var maxL = 0, endK = null;
  Object.keys(byCode).forEach(function (k) { var l = visit(k); if (l > maxL) { maxL = l; endK = k; } });
  var chain = [], k = endK, guard = 0;
  while (k && guard++ < 1000) { chain.unshift(byCode[k].code); k = prev[k]; }
  return { minQuarters: maxL + (chain.length ? 1 : 0), chain: chain };
}
