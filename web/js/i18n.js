/* UC SmartPick i18n engine — 4 locales, data-i18n attributes + t(key, vars) */
"use strict";
var I18N_LOCALES = {
  "zh-CN": "简体中文",
  "zh-TW": "繁體中文",
  "en": "English",
  "es": "Español"
};
(function () {
  var LANG_KEY = "ucsp_lang";
  var locale = null, dict = null, readyPromise = null;

  function resolveLocale() {
    try {
      var s = localStorage.getItem(LANG_KEY);
      if (s && I18N_LOCALES[s]) return s;
    } catch (e) {}
    var b = String(navigator.language || navigator.userLanguage || "en").toLowerCase();
    if (b === "zh-tw" || b.indexOf("zh-tw") === 0 || b === "zh-hk" || b.indexOf("zh-hk") === 0) return "zh-TW";
    if (b === "zh" || b.indexOf("zh") === 0) return "zh-CN";
    if (b === "es" || b.indexOf("es") === 0) return "es";
    return "en";
  }

  function lookup(key) {
    var parts = key.split("."), cur = dict, i;
    for (i = 0; i < parts.length; i++) {
      if (cur === null || typeof cur !== "object") return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }

  function t(key, vars) {
    var v = dict ? lookup(key) : undefined;
    if (v === undefined || v === null) return key;
    if (typeof v !== "string") return v; /* arrays / objects pass through */
    if (vars) {
      v = v.replace(/\{(\w+)\}/g, function (m, k) {
        return (vars[k] !== undefined && vars[k] !== null) ? vars[k] : m;
      });
    }
    return v;
  }

  function applyI18n(root) {
    root = root || document;
    var els = root.querySelectorAll("[data-i18n]"), i, v;
    for (i = 0; i < els.length; i++) {
      v = t(els[i].getAttribute("data-i18n"));
      if (typeof v === "string") els[i].textContent = v;
    }
    var phs = root.querySelectorAll("[data-i18n-ph]"), j, p;
    for (j = 0; j < phs.length; j++) {
      p = t(phs[j].getAttribute("data-i18n-ph"));
      if (typeof p === "string") phs[j].setAttribute("placeholder", p);
    }
  }

  function init() {
    if (readyPromise) return readyPromise;
    locale = resolveLocale();
    readyPromise = fetch("data/i18n/" + locale + ".json")
      .then(function (r) { if (!r.ok) throw new Error("i18n " + locale); return r.json(); })
      .catch(function () {
        locale = "zh-CN";
        return fetch("data/i18n/zh-CN.json").then(function (r) { return r.json(); });
      })
      .then(function (d) {
        dict = d;
        try { document.documentElement.lang = locale; } catch (e) {}
        applyI18n();
        return locale;
      });
    return readyPromise;
  }

  function initSwitcher(selId) {
    var sel = document.getElementById(selId);
    if (!sel) return;
    Object.keys(I18N_LOCALES).forEach(function (l) {
      var o = document.createElement("option");
      o.value = l;
      o.textContent = I18N_LOCALES[l];
      sel.appendChild(o);
    });
    sel.value = locale;
    sel.addEventListener("change", function () { setLocale(sel.value); });
  }

  function setLocale(l) {
    if (!I18N_LOCALES[l]) return;
    try { localStorage.setItem(LANG_KEY, l); } catch (e) {}
    location.reload();
  }

  window.I18N = {
    t: t,
    applyI18n: applyI18n,
    init: init,
    initSwitcher: initSwitcher,
    getLocale: function () { return locale; },
    setLocale: setLocale,
    LOCALES: I18N_LOCALES
  };
})();
