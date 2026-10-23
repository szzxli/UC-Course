/* UC SmartPick 共享工具 */
"use strict";
var LS = "ucsp_";
function Sget(k, fb) { try { var v = localStorage.getItem(LS + k); return v === null ? fb : JSON.parse(v); } catch (e) { return fb; } }
function Sset(k, v) { try { localStorage.setItem(LS + k, JSON.stringify(v)); } catch (e) {} }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
function navActive(p) { document.querySelectorAll(".tabbar a").forEach(function (a) { a.classList.toggle("active", a.dataset.page === p); }); }
/* 课号归一化：MAE 08 -> MAE 8 */
function normCode(code) { return String(code || "").trim().replace(/\b0+(\d)/g, "$1").replace(/\s+/g, " "); }
/* 学分解析：区间取上限 "2-4" -> 4 */
function unitsNum(u) {
  var m = String(u || "4").match(/(\d+(?:\.\d+)?)/g);
  if (!m) return 4;
  return Math.max.apply(null, m.map(Number));
}
/* ---- 换校区统一规则（首页/查课/转学三页共用）----
   校区绑定的状态：major/major2 意向专业、myCourses 选课清单、
   have 已修、draft 排课草稿、transferCC。有存量时先 confirm
   （msg 由调用方按当前语言传入），确认后一并清空，不静默带过去。 */
function campusBoundCount() {
  return Sget("myCourses", []).length + Object.keys(Sget("have", {})).length;
}
function resetCampusBound(newCampus) {
  Sset("campus", newCampus);
  Sset("major", "");
  Sset("major2", "");
  Sset("myCourses", []);
  Sset("have", {});
  Sset("draft", []);
  Sset("transferCC", "");
}
/* 返回 true = 已切换到 newCampus；false = 没变（同校区或用户取消）。
   取消时调用方负责把控件值改回 Sget("campus")。 */
function switchCampus(newCampus, msg) {
  var cur = Sget("campus", "UCI");
  if (newCampus === cur) return false;
  if ((campusBoundCount() > 0 || Sget("major", "")) && !confirm(msg)) return false;
  resetCampusBound(newCampus);
  return true;
}
