/* UC SmartPick 智能客服：本地 FAQ 关键词匹配，零后端 */
"use strict";
(function () {
  var FAQ = null, OPEN = false;
  function cur() { try { return (localStorage.getItem("ucsp_lang") || "zh-CN"); } catch (e) { return "zh-CN"; } }
  function t(k) { return (window.I18N ? I18N.t(k) : k); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function entries() {
    if (!FAQ) return [];
    var l = cur();
    return FAQ[l] || FAQ["en"] || [];
  }
  function answer(q) {
    var list = entries(), ql = q.toLowerCase(), best = null, bestScore = 0;
    list.forEach(function (e) {
      var score = 0;
      (e.kws || []).forEach(function (k) { if (ql.indexOf(String(k).toLowerCase()) >= 0) score += 2; });
      var qt = (e.q || "").toLowerCase();
      ql.split(/\s+/).forEach(function (w) { if (w.length > 1 && qt.indexOf(w) >= 0) score += 1; });
      if (score > bestScore) { bestScore = score; best = e; }
    });
    return bestScore > 0 ? best.a : null;
  }
  function build() {
    if (document.getElementById("ucspChatBtn")) return;
    var btn = document.createElement("button");
    btn.id = "ucspChatBtn";
    btn.className = "chatbtn";
    btn.textContent = "💬";
    btn.setAttribute("aria-label", "help");
    var panel = document.createElement("div");
    panel.id = "ucspChatPanel";
    panel.className = "chatpanel";
    panel.hidden = true;
    panel.innerHTML = '<div class="chathead"><b>' + esc(t("chat.title")) + '</b>' +
      '<button class="chatx" aria-label="close">✕</button></div>' +
      '<div class="chatbody"></div>' +
      '<div class="chatinput"><input maxlength="200"><button>➤</button></div>';
    document.body.appendChild(btn);
    document.body.appendChild(panel);
    var body = panel.querySelector(".chatbody"), input = panel.querySelector("input");
    function say(who, text) {
      var d = document.createElement("div");
      d.className = "chatmsg " + who;
      d.textContent = text;
      body.appendChild(d);
      body.scrollTop = body.scrollHeight;
    }
    function refreshUI() {
      panel.querySelector(".chathead b").textContent = t("chat.title");
      input.placeholder = t("chat.placeholder");
      if (!body.children.length) say("bot", t("chat.hello"));
    }
    function ask() {
      var q = input.value.trim();
      if (!q) return;
      say("me", q);
      input.value = "";
      var a = answer(q);
      say("bot", a || t("chat.fallback"));
    }
    btn.addEventListener("click", function () {
      OPEN = !OPEN;
      panel.hidden = !OPEN;
      if (OPEN) { refreshUI(); input.focus(); }
    });
    panel.querySelector(".chatx").addEventListener("click", function () { OPEN = false; panel.hidden = true; });
    panel.querySelector(".chatinput button").addEventListener("click", ask);
    input.addEventListener("keydown", function (e) { if (e.key === "Enter") ask(); });
    fetch("data/faq.json").then(function (r) { return r.json(); }).then(function (j) { FAQ = j; }).catch(function () {});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
