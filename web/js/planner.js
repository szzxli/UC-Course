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

/* 排课：贪心，按拓扑层+课程码排序，每门放进先修已满足且学分未超的最早 quarter */
function scheduleQuarters(courses, maxUnits, maxQuarters) {
  maxUnits = maxUnits || 16; maxQuarters = maxQuarters || 12;
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
    if (missing.length) warnings.push(c.code + " 的先修 " + missing.join("、") + " 不在选课列表中（假设已修完）");
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
    if (!done) warnings.push(c.code + " 放不进 " + maxQuarters + " 个 quarter（学分上限太紧）");
  });
  return { quarters: quarters, warnings: warnings, levels: levels };
}

var GOAL_TIPS = {
  grad: [
    "GPA 优先：难课分散到不同 quarter，别把两门硬课放一起",
    "选 1–2 门 graduate-level 课，申研/直博是加分项",
    "找 research for credit（199 课），比多上一门课值钱",
  ],
  job: [
    "项目课优先：能写进简历的课排前面",
    "Recruiting 季（秋招）那两个 quarter 别排太满，留时间面试",
    "先修链尽早打通，实习要求的技术栈课优先",
  ],
  undecided: [
    "先按毕业要求排，难课分散",
    "大二结束前决定方向：两条路的选课分叉点在高阶课",
  ],
};

if (typeof module !== "undefined") { module.exports = { parseUnits: parseUnits, topoLevels: topoLevels, scheduleQuarters: scheduleQuarters, GOAL_TIPS: GOAL_TIPS }; }
