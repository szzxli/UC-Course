/* UC-Course 认知链修复（2026-10-23）UI 端到端用例（jsdom 真实加载页面）：
   K1 plan 客服按钮点测、K2 plan 切 English 运行时复测、
   H1 换校区确认清状态、M3 删课保草稿、H3 口径声明、
   K5 轨迹读草稿 + 排不下明示、M2 导入横幅、H2/K3/M5 专业页、
   M1 校区归属校验、K6 转学页按钮文案随语言、L5 空清单不跳页 */
"use strict";
const fs = require("fs");
const path = require("path");
const http = require("http");
const { JSDOM } = require("/home/hatch/workspace/tools/jsdomtest/node_modules/jsdom");
const WEB = "/home/hatch/workspace/uc-course/web";

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}
function load(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }
function mime(f) {
  return f.endsWith(".html") ? "text/html" : f.endsWith(".js") ? "text/javascript"
    : f.endsWith(".json") ? "application/json" : f.endsWith(".css") ? "text/css" : "text/plain";
}

const server = http.createServer((req, res) => {
  const p = path.join(WEB, decodeURIComponent(req.url.split("?")[0]));
  fs.readFile(p, (err, buf) => {
    if (err) { res.writeHead(404); res.end("nf"); return; }
    res.writeHead(200, { "Content-Type": mime(p) + "; charset=utf-8" });
    res.end(buf);
  });
});

function waitFor(fn, ms, label) {
  return new Promise((resolve, reject) => {
    const t0 = Date.now();
    (function poll() {
      let v;
      try { v = fn(); } catch (e) { v = null; }
      if (v) return resolve(v);
      if (Date.now() - t0 > ms) return reject(new Error("timeout: " + label));
      setTimeout(poll, 60);
    })();
  });
}

let BASE = "";
async function openPage(page, seeds, confirmResult) {
  const dom = new JSDOM("", {
    url: BASE + "/" + page,
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
  });
  return dom;
}
function makePage(page, opts) {
  opts = opts || {};
  const html = fs.readFileSync(path.join(WEB, page), "utf8");
  const dom = new JSDOM(html, {
    url: BASE + "/" + page,
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = function (url, o) {
        return fetch(new URL(url, window.location.href).href, o);
      };
      window.__alerts = [];
      window.alert = function (m) { window.__alerts.push(String(m)); };
      window.confirm = function () { return opts.confirm !== false; };
      window.Element.prototype.scrollIntoView = function () {};
      Object.keys(opts.ls || {}).forEach(k => {
        window.localStorage.setItem("ucsp_" + k, JSON.stringify(opts.ls[k]));
      });
      if (opts.lang) window.localStorage.setItem("ucsp_lang", opts.lang);
    },
  });
  return dom;
}
function ls(window, k, fb) {
  const v = window.localStorage.getItem("ucsp_" + k);
  return v === null ? fb : JSON.parse(v);
}
function fire(window, el, type) {
  el.dispatchEvent(new window.Event(type, { bubbles: true }));
}

async function main() {
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  BASE = "http://127.0.0.1:" + server.address().port;
  const en = load(path.join(WEB, "data/i18n/en.json"));

  /* ---------- K1: plan 页客服按钮点测 ---------- */
  console.log("== K1 plan 客服按钮 ==");
  {
    const dom = makePage("plan.html", { ls: { campus: "UCI", myCourses: [{ code: "MATH 2A", u: "4", pre: [], campus: "UCI" }] } });
    const w = dom.window;
    await waitFor(() => w.document.getElementById("ucspChatBtn"), 8000, "chat btn");
    ok("K1 客服按钮已生成", true);
    w.document.getElementById("ucspChatBtn").click();
    const panel = w.document.getElementById("ucspChatPanel");
    ok("K1 点击后面板打开", panel.hidden === false);
    await waitFor(() => panel.querySelectorAll(".chatmsg").length >= 1, 5000, "hello msg");
    const input = panel.querySelector("input");
    input.value = "AP能抵什么课";
    panel.querySelector(".chatinput button").click();
    await waitFor(() => panel.querySelectorAll(".chatmsg").length >= 3, 5000, "answer msg");
    ok("K1 提问后有机器人回复", panel.querySelectorAll(".chatmsg.bot").length >= 2);
    dom.window.close();
  }

  /* ---------- K2: plan 切 English 运行时复测 ---------- */
  console.log("== K2 plan English ==");
  {
    const dom = makePage("plan.html", {
      lang: "en",
      ls: { campus: "UCI", myCourses: [
        { code: "MATH 2A", u: "4", pre: [], campus: "UCI" },
        { code: "MATH 2B", u: "4", pre: [], campus: "UCI" },
        { code: "MATH 2D", u: "4", pre: [], campus: "UCI" }] },
    });
    const w = dom.window;
    await waitFor(() => w.document.querySelectorAll("#myList .course-row").length === 3, 8000, "mine rendered");
    w.document.querySelectorAll("script").forEach(s => s.remove()); /* 断言只看渲染文本，不扫脚本源码 */
    const bodyText = w.document.body.textContent;
    ok("K2 英文界面渲染（Target years）", bodyText.includes("Target years"));
    ok("K2 无未解析键/undefined", !/plan\.(years|scopeNote)|\bundefined\b/.test(bodyText),
      bodyText.slice(0, 200));
    const assess = w.document.getElementById("tAssess").textContent;
    ok("K2 英文口径声明出现", /covers only the 3 course/.test(assess), assess.slice(0, 120));
    w.document.getElementById("genBtn").click();
    await waitFor(() => w.document.querySelectorAll("#out .qblock").length >= 1, 5000, "draft blocks");
    ok("K2 生成排课后草稿箱渲染", true);
    dom.window.close();
  }

  /* ---------- H1: 首页换校区（确认 / 取消两路） ---------- */
  console.log("== H1 换校区 ==");
  const seedH1 = { campus: "UCI", major: "uci-computer-science.json", major2: "",
    myCourses: [{ code: "MATH 2A", u: "4", pre: [], campus: "UCI" }, { code: "MATH 2B", u: "4", pre: [], campus: "UCI" }],
    have: { "MATH 2A": true }, draft: [["MATH 2A"]] };
  {
    const dom = makePage("index.html", { ls: seedH1, confirm: true });
    const w = dom.window;
    const sel = await waitFor(() => {
      const s = w.document.getElementById("campus");
      return s && w.document.querySelectorAll("#majorSel option").length > 1 ? s : null;
    }, 8000, "majors loaded");
    sel.value = "UCSD"; fire(w, sel, "change");
    ok("H1 确认后清单清空", ls(w, "myCourses", []).length === 0);
    ok("H1 确认后已修清空", Object.keys(ls(w, "have", {})).length === 0);
    ok("H1 确认后专业清空", ls(w, "major", "x") === "");
    ok("H1 确认后草稿清空", (ls(w, "draft", []) || []).length === 0);
    ok("H1 校区已切换", ls(w, "campus", "") === "UCSD");
    dom.window.close();
  }
  {
    const dom = makePage("index.html", { ls: seedH1, confirm: false });
    const w = dom.window;
    const sel = await waitFor(() => {
      const s = w.document.getElementById("campus");
      return s && w.document.querySelectorAll("#majorSel option").length > 1 ? s : null;
    }, 8000, "majors loaded");
    sel.value = "UCSD"; fire(w, sel, "change");
    ok("H1 取消后清单保留", ls(w, "myCourses", []).length === 2);
    ok("H1 取消后校区不变", ls(w, "campus", "") === "UCI");
    ok("H1 取消后下拉回弹", sel.value === "UCI");
    dom.window.close();
  }

  /* ---------- M3 + H3 + L5: plan 页 ---------- */
  console.log("== M3/H3/L5 plan ==");
  {
    const dom = makePage("plan.html", { lang: "zh-CN", ls: { campus: "UCI",
      myCourses: [
        { code: "MATH 2A", u: "4", pre: [], campus: "UCI" },
        { code: "MATH 2B", u: "4", pre: ["MATH 2A"], campus: "UCI" },
        { code: "MATH 2D", u: "4", pre: ["MATH 2B"], campus: "UCI" }],
      draft: [["MATH 2A"], ["MATH 2B", "MATH 2D"]] } });
    const w = dom.window;
    await waitFor(() => w.document.querySelectorAll("#myList .course-row").length === 3, 8000, "mine");
    await waitFor(() => w.document.querySelector("#out .dchip"), 5000, "draft rendered");
    const assess = w.document.getElementById("tAssess").textContent;
    ok("H3 口径声明在评估卡内", /只针对已选的 3 门课/.test(assess), assess.slice(0, 150));
    ok("H3 学位总量对照行", /180/.test(assess) && /%/.test(assess), assess.slice(0, 200));
    const btns = w.document.querySelectorAll("#myList button[data-i]");
    btns[1].click(); /* 移除 MATH 2B */
    const d = ls(w, "draft", []);
    const flat = d.reduce((a, q) => a.concat(q), []);
    ok("M3 删一门后草稿保留其余课", flat.includes("MATH 2A") && flat.includes("MATH 2D") && !flat.includes("MATH 2B"),
      JSON.stringify(flat));
    ok("M3 草稿箱仍渲染", !!w.document.querySelector("#out .dchip"));
    dom.window.close();
  }
  {
    const dom = makePage("plan.html", { lang: "zh-CN", ls: { campus: "UCI", myCourses: [] } });
    const w = dom.window;
    await waitFor(() => w.document.querySelectorAll("#maxU option").length === 3, 8000, "init done");
    w.document.getElementById("genBtn").click();
    ok("L5 空清单点生成不跳页", w.location.pathname.endsWith("/plan.html"), w.location.pathname);
    ok("L5 有原地提示", w.__alerts.some(a => /清单是空的/.test(a)), JSON.stringify(w.__alerts));
    dom.window.close();
  }

  /* ---------- K5: 轨迹页读草稿 + 排不下明示 ---------- */
  console.log("== K5 轨迹 ==");
  {
    const dom = makePage("trajectory.html", { lang: "zh-CN", ls: { campus: "UCI",
      myCourses: [
        { code: "MATH 2A", u: "4", pre: [], campus: "UCI" },
        { code: "MATH 2B", u: "4", pre: ["MATH 2A"], campus: "UCI" }],
      draft: [["MATH 2B"], ["MATH 2A"]] } }); /* 手工把 2B 挪到第一学期 */
    const w = dom.window;
    const out = await waitFor(() => {
      const o = w.document.getElementById("trajOut");
      return o && o.textContent.includes("MATH 2B") ? o : null;
    }, 8000, "traj rendered");
    ok("K5 轨迹按草稿顺序（2B 在 2A 前）", out.textContent.indexOf("MATH 2B") < out.textContent.indexOf("MATH 2A"));
    ok("K5 草稿来源声明", /课表草稿呈现/.test(out.textContent));
    dom.window.close();
  }
  {
    const man = load(path.join(WEB, "data/search/uci/manifest.json"));
    let codes = [];
    man.files.forEach(f => load(path.join(WEB, "data/search/uci", f)).forEach(c => codes.push(c)));
    const mine = codes.slice(0, 50).map(c => ({ code: c.code, u: c.u, pre: c.pre || [], campus: "UCI" }));
    const dom = makePage("trajectory.html", { lang: "zh-CN", ls: { campus: "UCI", myCourses: mine, maxUnits: 12 } });
    const w = dom.window;
    const out = await waitFor(() => {
      const o = w.document.getElementById("trajOut");
      return o && /排不下/.test(o.textContent) ? o : null;
    }, 12000, "notPlaced warn");
    const m = out.textContent.match(/以下 (\d+) 门课在 12 个学季内排不下/);
    ok("K5 排不下的课明示数量", !!m, out.textContent.slice(0, 200));
    const rendered = out.querySelectorAll(".trajrow").length;
    ok("K5 已排 + 未排 = 清单总数（无静默消失）", rendered + (+m[1]) === 50,
      rendered + " + " + m[1] + " vs 50");
    dom.window.close();
  }

  /* ---------- 专业页：H2 中文层 / K3 计数 / M5 披露 / M2 横幅 / M1 校验 ---------- */
  console.log("== 专业页 ==");
  {
    const dom = makePage("major.html", { lang: "zh-CN", ls: { campus: "UCSD", major: "ucsd-computer-science.json", justImported: 5 } });
    const w = dom.window;
    await waitFor(() => w.document.querySelectorAll("#reqList .card").length >= 5, 8000, "req cards");
    const firstTitle = w.document.querySelector("#reqList .card .section-title").textContent;
    ok("H2 要求名中文显示", /[一-鿿]/.test(firstTitle), firstTitle.slice(0, 80));
    const banner = w.document.getElementById("importBanner");
    ok("M2 导入横幅显示门数", banner.hidden === false && /5/.test(banner.textContent), banner.textContent);
    ok("M2 横幅一次性（标记已清）", ls(w, "justImported", null) === null);
    w.document.getElementById("addAllReqBtn").click();
    const alertMsg = w.__alerts[w.__alerts.length - 1] || "";
    ok("M5 一键加入披露多方案取第一组", /方案A/.test(alertMsg), alertMsg.slice(0, 120));
    const prog = [...w.document.querySelectorAll("[data-havecount]")].map(e => e.textContent);
    ok("K3 一键加入后进度不再是 0", prog.some(t => /已修\/已选 [1-9]/.test(t)), prog.slice(0, 4).join(" | "));
    dom.window.close();
  }
  {
    const dom = makePage("major.html", { ls: { campus: "UCSD", major: "uci-computer-science.json" } });
    const w = dom.window;
    await waitFor(() => w.document.getElementById("majorMismatch").hidden === false, 8000, "mismatch");
    ok("M1 专业与校区不符时明示拦截", true);
    dom.window.close();
  }

  /* ---------- K6: 转学页导入按钮文案随语言 ---------- */
  console.log("== K6 transfer 按钮 ==");
  {
    const dom = makePage("transfer.html", { lang: "en", ls: { campus: "UCI" } });
    const w = dom.window;
    const btn = await waitFor(() => {
      const b = w.document.getElementById("importBtn");
      return b && b.textContent === en.transfer.importGo ? b : null;
    }, 8000, "importBtn en");
    ok("K6 英文下导入按钮为英文", btn.textContent === en.transfer.importGo, btn.textContent);
    dom.window.close();
  }

  console.log(`\nRESULT: ${pass} pass, ${fail} fail`);
  server.close();
  process.exit(fail ? 1 : 0);
}

main().catch(e => { console.error("ERROR", e); server.close(); process.exit(1); });
