/* UC SmartPick 共享工具 */
"use strict";
var LS = "ucsp_";
function Sget(k, fb) { try { var v = localStorage.getItem(LS + k); return v === null ? fb : JSON.parse(v); } catch (e) { return fb; } }
function Sset(k, v) { try { localStorage.setItem(LS + k, JSON.stringify(v)); } catch (e) {} }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
function navActive(p) { document.querySelectorAll(".tabbar a").forEach(function (a) { a.classList.toggle("active", a.dataset.page === p); }); }
