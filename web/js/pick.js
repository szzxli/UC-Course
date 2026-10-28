/* 选课智能引擎 v1（下学期选什么 · UCSB 环境科学试点）
 * 输入：专业要求 + 课程先修数据 + 已修集合 → 输出：本学期可修推荐（按关键程度排序）+ 还差先修。
 * 口径（与 graduation 引擎一致，诚实标注）：
 *  - 先修按目录原文 and/or 解析（复用 Engine.parsePrereq）；原文为空时按快照扁平列表任一满足处理；
 *  - 关键课 = 在最长先修链上，或扇出（间接解锁门数）≥ 6（与引擎同一阈值）；
 *  - 最短路径 = 优先排最长链上的课，拖后即拖毕业；排序：链长 → 扇出 → 课号；
 *  - 等效：只认显式同课异码表（与引擎一致的两组）+ 要求内的备选路径组；UCSB 的 CC 对标数据待建，不编；
 *  - 热门课/候选人数：现有数据无选课人数与候补数，v1 不做此项；
 *  - 范围：必修路径（prereq + required）；选修池（B-1/C）只给提示，不进排名。
 */
"use strict";
(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Pick = api;
})(typeof self !== "undefined" ? self : this, function () {
  var Engine = null;
  try {
    if (typeof module !== "undefined" && module.exports) Engine = require("./engine.js");
    else if (typeof self !== "undefined" && self.Engine) Engine = self.Engine;
  } catch (e) { Engine = null; }
  if (!Engine) throw new Error("Pick requires Engine");

  var normCode = Engine.normCode;
  var unitsNum = Engine.unitsNum;

  /* 与引擎一致的同课异码（永久号优先） */
  var KNOWN_EQUIV = {
    "ENV S 126|ENV S 193DS": "ENV S 126",
    "ENGL 37|RG ST 37": "ENGL 37"
  };
  var EQUIV_PARTNER = {
    "ENV S 193DS": "ENV S 126", "ENV S 126": "ENV S 193DS",
    "ENGL 37": "RG ST 37", "RG ST 37": "ENGL 37"
  };

  function equivKey(codes) {
    return codes.map(normCode).sort().join("|");
  }
  function normalizeGroup(group) {
    var codes = group.map(normCode);
    if (codes.length === 1) return { take: "one", courses: codes };
    var key = equivKey(codes);
    if (KNOWN_EQUIV[key]) return { take: "one", courses: [normCode(KNOWN_EQUIV[key])], alt: codes };
    return { take: "all", courses: codes };
  }
  function groupSatisfied(g, haveSet) {
    if (g.take === "one") return g.courses.some(function (c) { return haveSet.has(normCode(c)); });
    return g.courses.every(function (c) { return haveSet.has(normCode(c)); });
  }
  function groupStarted(g, haveSet) {
    return g.courses.some(function (c) { return haveSet.has(normCode(c)); });
  }

  /* 要求 → 待修课程：返回 { needed: Map(code -> {reqIds, reqNames, altGroups}), electiveInfo } */
  function neededFromRequirements(requirements, haveSet) {
    var needed = {};
    var electiveInfo = { b1: null, c: null };
    requirements.forEach(function (req) {
      if (req.type === "elective") {
        if (req.id === "b-1") electiveInfo.b1 = req;
        if (req.id === "c-outside-concentration") electiveInfo.c = req;
        return;
      }
      var groups = (req.options && req.options.length)
        ? req.options.map(normalizeGroup)
        : [{ take: "all", courses: (req.courses || []).map(normCode) }];
      if (groups.some(function (g) { return groupSatisfied(g, haveSet); })) return;
      var started = groups.filter(function (g) { return groupStarted(g, haveSet); });
      var active = started.length ? started : groups;
      active.forEach(function (g) {
        g.courses.forEach(function (c) {
          var nc = normCode(c);
          if (haveSet.has(nc)) return;
          if (!needed[nc]) needed[nc] = { code: nc, reqIds: [], reqNames: [], altGroups: [] };
          if (needed[nc].reqIds.indexOf(req.id) < 0) {
            needed[nc].reqIds.push(req.id);
            needed[nc].reqNames.push(req);
          }
          if (groups.length > 1) {
            var others = groups.filter(function (h) { return h !== g; }).map(function (h) { return h.courses; });
            if (others.length && needed[nc].altGroups.length === 0) needed[nc].altGroups = others;
          }
        });
      });
    });
    return { needed: needed, electiveInfo: electiveInfo };
  }

  function treeHasOr(node) {
    if (!node) return false;
    if (node.op === "OR") return true;
    if (node.items) return node.items.some(treeHasOr);
    return false;
  }

  function compute(input) {
    var requirements = input.requirements || [];
    var catalog = input.catalog || {};
    var haveRaw = input.have || [];
    var plannedRaw = input.planned || [];

    var haveSet = new Set();
    haveRaw.forEach(function (c) {
      var nc = normCode(c);
      haveSet.add(nc);
      if (EQUIV_PARTNER[nc]) haveSet.add(normCode(EQUIV_PARTNER[nc]));
    });
    var plannedSet = new Set(plannedRaw.map(normCode));

    var nr = neededFromRequirements(requirements, haveSet);
    var needed = nr.needed;
    var neededCodes = Object.keys(needed);

    /* 先修树与叶子（原文为空 → 扁平列表任一满足，与引擎回退口径一致） */
    var trees = {};
    var leaves = {};
    neededCodes.forEach(function (code) {
      var cat = catalog[code] || {};
      var tree = Engine.parsePrereq(cat.prerequisites_raw || "");
      if (tree && tree.fallback) tree = null; /* 原文为空：parsePrereq 回 {fallback:true}，须走扁平回退 */
      if (!tree && (cat.prerequisites_courses || []).length) {
        var flat = cat.prerequisites_courses.map(normCode);
        tree = flat.length === 1 ? { code: flat[0] } : { op: "OR", items: flat.map(function (c) { return { code: c }; }) };
      }
      trees[code] = tree || null;
      leaves[code] = tree ? Engine.treeLeafCodes(tree, []) : [];
    });

    var neededSet = new Set(neededCodes);
    var neededPrereqs = {};
    neededCodes.forEach(function (code) {
      neededPrereqs[code] = leaves[code].filter(function (l) { return neededSet.has(normCode(l)); });
    });
    /* 反向边：直接解锁 */
    var dependents = {};
    neededCodes.forEach(function (code) { dependents[code] = []; });
    neededCodes.forEach(function (code) {
      neededPrereqs[code].forEach(function (p) {
        var np = normCode(p);
        if (dependents[np] && dependents[np].indexOf(code) < 0) dependents[np].push(code);
      });
    });
    /* 链长与扇出（传递闭包，防环） */
    var chainMemo = {};
    var fanMemo = {};
    function chainLen(code, seen) {
      if (chainMemo[code] !== undefined) return chainMemo[code];
      if (seen[code]) return 1;
      seen[code] = true;
      var best = 1;
      dependents[code].forEach(function (d) {
        best = Math.max(best, 1 + chainLen(d, seen));
      });
      delete seen[code];
      chainMemo[code] = best;
      return best;
    }
    function fanout(code, seen) {
      if (fanMemo[code] !== undefined) return fanMemo[code];
      if (seen[code]) return [];
      seen[code] = true;
      var out = {};
      dependents[code].forEach(function (d) {
        out[d] = true;
        fanout(d, seen).forEach(function (x) { out[x] = true; });
      });
      delete seen[code];
      var list = Object.keys(out);
      fanMemo[code] = list;
      return list;
    }
    var maxChain = 0;
    neededCodes.forEach(function (code) { maxChain = Math.max(maxChain, chainLen(code, {})); });

    var recommended = [];
    var blocked = [];
    neededCodes.forEach(function (code) {
      var cat = catalog[code] || {};
      var item = {
        code: code,
        title: cat.title || "",
        units: unitsNum(cat.units),
        reqIds: needed[code].reqIds,
        reqNames: needed[code].reqNames,
        altGroups: needed[code].altGroups,
        chainLen: chainLen(code, {}),
        fanout: fanout(code, {}).length,
        directUnlocks: dependents[code].slice(),
        equivPartner: EQUIV_PARTNER[code] || null,
        planned: plannedSet.has(code)
      };
      item.key = item.chainLen >= maxChain || item.fanout >= 6;
      if (item.planned) return;
      if (Engine.treeSatisfied(trees[code], haveSet)) recommended.push(item);
      else {
        item.missing = leaves[code].filter(function (l) { return !haveSet.has(normCode(l)); });
        item.hasOr = treeHasOr(trees[code]);
        blocked.push(item);
      }
    });
    function byRank(a, b) {
      if (b.chainLen !== a.chainLen) return b.chainLen - a.chainLen;
      if (b.fanout !== a.fanout) return b.fanout - a.fanout;
      return a.code < b.code ? -1 : (a.code > b.code ? 1 : 0);
    }
    recommended.sort(byRank);
    blocked.sort(byRank);

    /* B-1 选修提示：池中学分缺口（32 学分目标，与引擎一致） */
    var b1Info = null;
    if (nr.electiveInfo.b1) {
      var pool = (nr.electiveInfo.b1.courses || []).map(normCode);
      var poolSet = {};
      pool.forEach(function (c) { poolSet[c] = true; });
      if (poolSet["ENV S 126"]) delete poolSet["ENV S 193DS"];
      var haveUnits = 0;
      Object.keys(poolSet).forEach(function (c) {
        if (haveSet.has(c)) haveUnits += unitsNum((catalog[c] || {}).units);
      });
      b1Info = { poolSize: Object.keys(poolSet).length, haveUnits: haveUnits, remaining: Math.max(0, 32 - haveUnits) };
    }

    return {
      recommended: recommended,
      blocked: blocked,
      b1: b1Info,
      hasC: !!nr.electiveInfo.c,
      stats: { needed: neededCodes.length, recommended: recommended.length, blocked: blocked.length, maxChain: maxChain }
    };
  }

  return { compute: compute, KNOWN_EQUIV: KNOWN_EQUIV, EQUIV_PARTNER: EQUIV_PARTNER };
});
