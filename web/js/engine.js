/* 选课智能引擎 v1（校内版 · UCSB 环境科学试点）
 * 输入：目标毕业年数 → 输出：按先修链排好的学期表 + 最小学分覆盖 + 关键课。
 * 数据口径（诚实标注，见输出 warnings）：
 *  - 先修逻辑不用目录快照的扁平 prerequisites_courses（它把 and/or 压平、还会丢备选项，
 *    如 GEOG 172 只剩 COMM 87），而是现场解析 prerequisites_raw 的 and/or 结构；
 *  - GE 双计映射引自环境研究系 B.S. GE 计划（2022-08 修订），2026-27 目录下以 GOLD 标注为准；
 *  - C 区（校外集中方向）无官方课程清单，用 4 个通用 4 学分块表示；
 *  - 夏季学期、UC Online、社区大学课不在 v1，属二期/三期。
 */
"use strict";
(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Engine = api;
})(typeof self !== "undefined" ? self : this, function () {

  /* ---------- 通用 ---------- */
  function normCode(code) {
    return String(code || "").trim().replace(/\b0+(\d)/g, "$1").replace(/\s+/g, " ");
  }
  function unitsNum(u) {
    var m = String(u == null ? "4" : u).match(/(\d+(?:\.\d+)?)/g);
    if (!m) return 4;
    return Math.max.apply(null, m.map(Number));
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>\"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- 系名 → 系代码（解析先修原文用） ---------- */
  var DEPT_MAP = {
    "environmental studies": "ENV S", "envs": "ENV S", "es": "ENV S",
    "mathematics": "MATH", "math": "MATH",
    "statistics and applied probability": "PSTAT", "statistics": "PSTAT", "pstat": "PSTAT",
    "economics": "ECON", "econ": "ECON",
    "chemistry": "CHEM", "chem": "CHEM",
    "physics": "PHYS", "phys": "PHYS",
    "molecular cellular developmental biology": "MCDB",
    "molecular, cellular, and developmental biology": "MCDB", "mcdb": "MCDB",
    "ecology evolution marine biology": "EEMB",
    "ecology, evolution & marine biology": "EEMB", "eemb": "EEMB",
    "geography": "GEOG", "geog": "GEOG",
    "earth science": "EARTH", "earth": "EARTH",
    "anthropology": "ANTH", "anth": "ANTH",
    "communication": "COMM", "comm": "COMM",
    "psychology": "PSY", "psych": "PSY", "psy": "PSY",
    "religious studies": "RG ST", "relig st": "RG ST", "religious": "RG ST",
    "philosophy": "PHIL", "phil": "PHIL",
    "political science": "POL S", "poli sci": "POL S", "pols": "POL S", "pol s": "POL S",
    "history": "HIST", "hist": "HIST",
    "feminist studies": "FEMST", "femst": "FEMST",
    "asian american studies": "AS AM", "as am": "AS AM",
    "black studies": "BL ST", "blst": "BL ST", "bl st": "BL ST",
    "chicano studies": "CH ST", "ch st": "CH ST",
    "global studies": "GLOBL", "global st": "GLOBL", "glob": "GLOBL", "global": "GLOBL",
    "sociology": "SOC", "soc": "SOC",
    "english": "ENGL", "engl": "ENGL",
    "writing": "WRIT", "writ": "WRIT",
    "art history": "ARTHI", "arthi": "ARTHI",
    "linguistics": "LING", "ling": "LING",
    "computer science": "CMPSC", "cmpsc": "CMPSC",
    "family studies": "FAMST", "famst": "FAMST"
  };
  /* 按名称长度降序排列，解析时先匹配长名，避免 Mathematics 被 Math 截断等 */
  var DEPT_NAMES = Object.keys(DEPT_MAP).sort(function (a, b) { return b.length - a.length; });

  /* 数字串 → 课程号列表：处理区间（2A-B → 2A,2B；1A-B-C → 1A,1B,1C；34LA-LB → 34LA,34LB）与通配（5AA-ZZ、105A-Z） */
  function expandNumberToken(tok) {
    tok = tok.replace(/\s+/g, "");
    if (tok.indexOf("-") < 0) return [tok];
    var parts = tok.split("-");
    var first = parts[0];
    var m = first.match(/^(\d+)([A-Z]*)$/);
    if (!m) return [tok];
    var last = parts[parts.length - 1];
    if (last === "Z" || last === "ZZ") return [{ wildcard: m[1] }];
    /* 以后缀末位字母为变量展开：2A-B → 2A,2B；34LA-LB → 34LA,34LB；1A-B-C → 1A,1B,1C */
    var pre = m[1] + m[2].slice(0, -1);
    var a = m[2].slice(-1).charCodeAt(0), b = last.slice(-1).charCodeAt(0);
    if (!m[2] || isNaN(a) || isNaN(b) || b < a) return [tok];
    var out = [];
    for (var c = a; c <= b; c++) out.push(pre + String.fromCharCode(c));
    return out;
  }

  /* 从一段先修原文中抽出“提及”，state.dept 在整段解析中持续继承（目录裸数字继承最近的系，
   * 如 "PSTAT 5A or 5LS"、"MATH 2A-B or 3A-B"）。系名匹配要求词边界，避免 es 误 match Studies 等。 */
  function extractMentions(seg, state) {
    state = state || { dept: null };
    var mentions = [], i = 0;
    while (i < seg.length) {
      var matched = null;
      for (var di = 0; di < DEPT_NAMES.length; di++) {
        var d = DEPT_NAMES[di];
        if (seg.slice(i, i + d.length).toLowerCase() === d) {
          var before = i === 0 || /[^A-Za-z]/.test(seg[i - 1]);
          var afterIdx = i + d.length;
          var after = afterIdx >= seg.length || /[^A-Za-z]/.test(seg[afterIdx]);
          if (before && after) { matched = d; break; }
        }
      }
      if (matched) { state.dept = DEPT_MAP[matched]; i += matched.length; continue; }
      var numMatch = seg.slice(i).match(/^\d+\s*[A-Z]*(?:\s*-\s*[A-Z]+(?:\s*-\s*[A-Z]+)*)?/);
      if (numMatch && state.dept) {
        expandNumberToken(numMatch[0]).forEach(function (x) {
          if (typeof x === "string") mentions.push({ code: normCode(state.dept + " " + x) });
          else mentions.push({ wildcard: state.dept, prefix: x.wildcard });
        });
        i += numMatch[0].length; continue;
      }
      i++;
    }
    return mentions;
  }

  /* 解析先修原文 → 逻辑树 { op: 'AND'|'OR', items: [...] }，叶子 { code } 或 { wildcard, prefix }。
   * 规则（覆盖目录常见写法）：
   *  - 分号切段；段首 and → 与前段 AND，段首 or → 与前段 OR，无连接词 → 视作 AND；
   *  - 段内先按 ' and ' 切（AND），每块含 ' or ' 则整块为 OR（逗号与 or 均切），否则逗号切为 AND；
   *  - 无法解析（无课程提及）→ 返回 null（无课程先修约束，如仅“高年级站位/教师同意”）。 */
  function parsePrereq(raw) {
    if (!raw) return { fallback: true };
    var t = " " + raw + " ";
    /* 去掉成绩、同期、考试类说明（考试替代路径不计入课程先修） */
    t = t.replace(/with a (minimum )?grade of[^.;]*/gi, " ");
    t = t.replace(/\(may be taken concurrently\)/gi, " ");
    t = t.replace(/completion of all listed prerequisites[^.;]*/gi, " ");
    t = t.replace(/or (a )?score of[^.;]*/gi, " ");
    t = t.replace(/or (advanced placement|ap )[^.;]*/gi, " ");
    t = t.replace(/or instructor approval/gi, " ");
    t = t.replace(/or consent of instructor/gi, " ");
    t = t.replace(/upper-division standing/gi, " ");
    t = t.replace(/not open to freshmen/gi, " ");
    t = t.replace(/either/gi, " ");
    /* 保护含 and 的系名全称，避免被 and 切分逻辑切碎 */
    t = t.replace(/statistics and applied probability/gi, "PSTAT");
    t = t.replace(/molecular, cellular, and developmental biology/gi, "MCDB");
    t = t.replace(/ecology, evolution & marine biology/gi, "EEMB");
    var state = { dept: null };
    var segments = t.split(";").map(function (s) { return s.trim(); }).filter(Boolean);
    if (!segments.length) return null;
    var tree = null;
    segments.forEach(function (seg, si) {
      var joinOp = "AND";
      if (/^or\b/i.test(seg)) { joinOp = "OR"; seg = seg.replace(/^or\b/i, "").trim(); }
      else if (/^and\b/i.test(seg)) { joinOp = "AND"; seg = seg.replace(/^and\b/i, "").trim(); }
      else if (si > 0) joinOp = "AND";
      var andParts = seg.split(/\band\b/i).map(function (s) { return s.trim(); }).filter(Boolean);
      var segNodes = [];
      andParts.forEach(function (part) {
        var mentions;
        if (/\bor\b/i.test(part)) {
          mentions = [];
          part.split(/\bor\b|,/i).map(function (s) { return s.trim(); }).filter(Boolean).forEach(function (piece) {
            mentions = mentions.concat(extractMentions(piece, state));
          });
          if (mentions.length === 1) segNodes.push(mentions[0]);
          else if (mentions.length > 1) segNodes.push({ op: "OR", items: mentions });
        } else {
          mentions = [];
          part.split(",").map(function (s) { return s.trim(); }).filter(Boolean).forEach(function (piece) {
            mentions = mentions.concat(extractMentions(piece, state));
          });
          if (mentions.length === 1) segNodes.push(mentions[0]);
          else if (mentions.length > 1) segNodes.push({ op: "AND", items: mentions });
        }
      });
      var segTree = segNodes.length === 1 ? segNodes[0] : (segNodes.length ? { op: "AND", items: segNodes } : null);
      if (!segTree) return;
      if (!tree) tree = segTree;
      else if (joinOp === "AND") tree = { op: "AND", items: [tree, segTree] };
      else tree = { op: "OR", items: [tree, segTree] };
    });
    return tree || null;
  }

  /* 逻辑树求值：set 为已修/已选课程代码集合（归一化后） */
  function treeSatisfied(node, set) {
    if (!node) return true;
    if (node.code) return set.has(normCode(node.code));
    if (node.wildcard !== undefined) {
      var hit = false;
      set.forEach(function (c) {
        var m = c.match(/^(.+?)\s+(\d+)([A-Z]*)$/);
        if (m && (!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0)) hit = true;
      });
      return hit;
    }
    if (node.op === "AND") return node.items.every(function (x) { return treeSatisfied(x, set); });
    return node.items.some(function (x) { return treeSatisfied(x, set); });
  }
  /* 树中所有叶子代码（用于缺口提示） */
  function treeLeafCodes(node, out) {
    out = out || [];
    if (!node) return out;
    if (node.code) out.push(normCode(node.code));
    else if (node.items) node.items.forEach(function (x) { treeLeafCodes(x, out); });
    return out;
  }
  /* 最早学期：AND 取子项最大 +1；OR 取计划内/已修备选项的最小 +1；无计划内备选项 → 未满足（返回 -1） */
  function treeEarliest(node, earliestOf, inPlan) {
    if (!node) return -1;
    if (node.code) {
      var c = normCode(node.code);
      if (inPlan.has(c)) return earliestOf[c];
      return -1;
    }
    if (node.wildcard !== undefined) {
      var best = -1;
      inPlan.forEach(function (c) {
        var m = c.match(/^(.+?)\s+(\d+)([A-Z]*)$/);
        if (m && (!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0)) {
          if (best < 0 || earliestOf[c] < best) best = earliestOf[c];
        }
      });
      return best;
    }
    if (node.op === "AND") {
      var mx = -1, any = false;
      node.items.forEach(function (x) {
        var e = treeEarliest(x, earliestOf, inPlan);
        if (e >= 0) { any = true; if (e > mx) mx = e; }
      });
      return any ? mx : -1;
    }
    var mn = -1;
    node.items.forEach(function (x) {
      var e = treeEarliest(x, earliestOf, inPlan);
      if (e >= 0 && (mn < 0 || e < mn)) mn = e;
    });
    return mn;
  }

  /* ---------- GE 双计映射（环境研究系 B.S. GE 计划 2022-08 修订；2026-27 目录下以 GOLD 标注为准） ---------- */
  var GE_MARK = {
    writing: ["ENV S 1", "ENV S 2", "ENV S 3", "HIST 5", "HIST 7", "FEMST 50", "POL S 12", "RG ST 14"],
    nwc: ["ANTH 2", "GLOBL 1", "ENV S 130A", "ENV S 130B"],
    eth: ["RG ST 14", "ENV S 189"],
    ahi: ["POL S 12", "RG ST 14", "ENV S 173"],
    areaC: ["ENV S 2", "CHEM 1A", "MATH 2A", "MATH 3A", "EEMB 3", "MCDB 1A", "GEOG 3", "GEOG 4",
            "EARTH 2", "EARTH 4", "EARTH 20", "ENV S 115", "MATH 2B", "MATH 3B",
            "PSTAT 5A", "PSTAT 5LS", "PHYS 6A", "PHYS 6B", "PHYS 6C"],
    areaD: ["ENV S 1", "ECON 1", "ECON 2", "ECON 9", "ANTH 2", "BL ST 4", "ENV S 130A", "ENV S 130B",
            "ENV S 132", "GEOG 5", "HIST 5", "HIST 7", "FEMST 50", "POL S 12", "PSY 1", "RG ST 14", "SOC 1"],
    areaE: ["ENV S 3", "PHIL 4", "RG ST 1", "GLOBL 1"]
  };
  /* 同课异码（永久号取代临时号 / 交叉开设）：选项组内视作同一门课，优先取永久号。
   * 注意：键须为排序后的拼接（equivKey 会排序）。标题相同的序列课（如 MATH 2A/2B）
   * 不是同课异码，不得用标题判断——只认本表。 */
  var KNOWN_EQUIV = {
    "ENV S 126|ENV S 193DS": "ENV S 126",
    "ENGL 37|RG ST 37": "ENGL 37"
  };
  function equivKey(codes) {
    return codes.map(normCode).sort().join("|");
  }

  /* 选项组归一化：单门 → 取 1 门；同课异码组 → 取 1 门（优先永久号）；其余（序列）→ 全修。 */
  function normalizeGroup(group) {
    var codes = group.map(normCode);
    if (codes.length === 1) return { take: "one", courses: codes };
    var key = equivKey(codes);
    if (KNOWN_EQUIV[key]) return { take: "one", courses: [KNOWN_EQUIV[key]], alt: codes };
    return { take: "all", courses: codes };
  }

  /* ---------- 排课引擎 ---------- */
  function buildPlan(input, data) {
    var warnings = [];
    var years = input.years || 3;
    var cap = input.maxUnits || 20;
    var startTerm = input.startTerm || 0; /* 0 秋 1 冬 2 春 */
    var nTerms = years * 3;
    var have = new Set((input.have || []).map(normCode));
    var major = data.major, catalog = data.catalog;
    var units = function (c) { return unitsNum((catalog[normCode(c)] || {}).units); };
    var title = function (c) { return (catalog[normCode(c)] || {}).title || ""; };

    /* 先修树：raw 解析为主；raw 为空时退回扁平列表作 OR；raw 无课程提及 → 无约束 */
    var treeOf = {};
    var fallbackCount = 0;
    Object.keys(catalog).forEach(function (code) {
      var raw = catalog[code].prerequisites_raw || "";
      var t = parsePrereq(raw);
      if (t && t.fallback) {
        fallbackCount++;
        var flat = (catalog[code].prerequisites_courses || []).map(normCode);
        treeOf[code] = flat.length ? { op: "OR", items: flat.map(function (c) { return { code: c }; }) } : null;
      } else treeOf[code] = t;
    });

    /* ---- 选择阶段：每条要求选一组（或全修），目标 = 总学分最小（含 GE 新增课） ---- */
    var selected = {}; /* code -> { via: reqId }，一课只计一个专业方向 */
    var occupied = new Set(); /* 已占用（含同课异码的另一码） */
    var EQUIV_PARTNER = { "ENGL 37": "RG ST 37", "RG ST 37": "ENGL 37", "ENV S 193DS": "ENV S 126", "ENV S 126": "ENV S 193DS" };
    function markOccupied(code, via) {
      selected[normCode(code)] = { via: via };
      occupied.add(normCode(code));
      var p = EQUIV_PARTNER[normCode(code)];
      if (p) occupied.add(normCode(p));
    }
    var choice = {}; /* reqId -> 选中的课程列表 */
    function groupCost(courses) {
      return courses.reduce(function (s, c) { return s + (have.has(normCode(c)) ? 0 : units(c)); }, 0);
    }
    /* 要求按顺序处理：先修（prereq）→ 必修（required）→ 选修池（elective，B-1/C 另算） */
    var ordered = major.requirements.slice().sort(function (a, b) {
      var rank = { prereq: 0, required: 1, elective: 2 };
      return (rank[a.type] || 9) - (rank[b.type] || 9);
    });
    ordered.forEach(function (req) {
      if (req.type === "elective") return; /* B-1/C 随后处理 */
      var groups;
      if (req.options && req.options.length) {
        groups = req.options.map(function (g) { return normalizeGroup(g); });
      } else {
        groups = [{ take: "all", courses: req.courses.map(normCode) }];
      }
      var best = null, bestScore = Infinity;
      groups.forEach(function (g) {
        var take = g.take === "one" ? [pickOne(g)] : g.courses.slice();
        /* 已被其他要求占用的课不得复用（跨方向不双计）；但 have 课可复用（已修） */
        var usable = take.filter(function (c) { return !occupied.has(normCode(c)) || have.has(normCode(c)); });
        if (g.take === "one" && usable.length === 0) return;
        if (g.take === "all" && usable.length !== take.length) return;
        var score = groupCost(usable);
        if (score < bestScore) { bestScore = score; best = usable; }
      });
      if (!best) { warnings.push(req.id + "：无可用选项（课程已被其他要求占用），该要求未排入"); return; }
      choice[req.id] = best;
      best.forEach(function (c) { if (!have.has(normCode(c))) markOccupied(c, req.id); });
    });
    function pickOne(g) {
      /* 组内取 1 门：优先未被占用、学分最小；已被占用的 have 课也可 */
      var cands = g.courses.filter(function (c) { return !occupied.has(normCode(c)) || have.has(normCode(c)); });
      if (!cands.length) cands = g.courses;
      cands.sort(function (a, b) { return units(a) - units(b); });
      return normCode(cands[0]);
    }
    /* B-1：从池中取最便宜的 32 学分，排除 A 区已用课与已选课 */
    var b1 = major.requirements.filter(function (r) { return r.id === "b-1"; })[0];
    var cReq = major.requirements.filter(function (r) { return r.id === "c-outside-concentration"; })[0];
    if (b1) {
      var pool = [];
      (b1.courses || []).forEach(function (c) {
        var nc = normCode(c);
        if (!occupied.has(nc) || have.has(nc)) pool.push(nc);
      });
      /* 193DS/126 同课异码：池中两者只留 126 */
      if (pool.indexOf("ENV S 126") >= 0) pool = pool.filter(function (c) { return c !== "ENV S 193DS"; });
      pool.sort(function (a, b) { return units(a) - units(b); });
      var acc = 0, picked = [];
      pool.forEach(function (c) {
        if (acc >= 32) return;
        if (units(c) <= 0) return; /* 目录记 0 学分的课不推进 32 学分目标，不选 */
        picked.push(c); acc += units(c);
      });
      choice["b-1"] = picked;
      picked.forEach(function (c) { if (!have.has(c)) markOccupied(c, "b-1"); });
    }
    /* C 区：4 个通用 4 学分块 */
    var cBlocks = [];
    if (cReq) {
      for (var bi = 1; bi <= 4; bi++) cBlocks.push("C 区方向课 " + bi);
      choice["c-outside-concentration"] = cBlocks.slice();
    }

    /* ---- GE 覆盖评估（纯函数：输入已选集合，输出覆盖与新增课；供优化循环复用） ---- */
    var areaNeed = { areaC: 3, areaD: 2, areaE: 2 };
    function evaluateGe(baseSet) {
      var planSet = new Set(baseSet);
      function hasMarker(list) { return list.some(function (c) { return planSet.has(normCode(c)); }); }
      function countMarkers(list) {
        var n = 0;
        list.forEach(function (c) { if (planSet.has(normCode(c))) n++; });
        return n;
      }
      var areaCovered = { areaC: [], areaD: [], areaE: [] };
      var usedForArea = new Set();
      ["areaC", "areaD", "areaE"].forEach(function (area) {
        GE_MARK[area].forEach(function (c) {
          var nc = normCode(c);
          if (planSet.has(nc) && !usedForArea.has(nc) && areaCovered[area].length < areaNeed[area]) {
            areaCovered[area].push(nc); usedForArea.add(nc);
          }
        });
      });
      var writingCovered = 2 + countMarkers(GE_MARK.writing); /* A1+A2 两门写作课计入 Writing */
      var nwcCovered = hasMarker(GE_MARK.nwc);
      var ethCovered = hasMarker(GE_MARK.eth);
      var ahiCovered = hasMarker(GE_MARK.ahi);
      var geNew = [];
      function addGeNew(code, why) {
        var nc = normCode(code);
        if (!planSet.has(nc)) { geNew.push({ code: nc, why: why }); planSet.add(nc); }
      }
      addGeNew("WRIT 2", "Area A1");
      addGeNew("WRIT 107EP", "Area A2（环境专业写作）");
      addGeNew("ENV S 136O", "Area F 艺术");
      addGeNew("ENV S 160", "Area G 文学");
      ["areaC", "areaD", "areaE"].forEach(function (area) {
        var gap = areaNeed[area] - areaCovered[area].length;
        for (var gi = 0; gi < gap; gi++) geNew.push({ code: "GE " + area + " 选修 " + (gi + 1), why: "Area " + area.slice(-1) + " 缺口", generic: true });
      });
      for (var wi = writingCovered; wi < 6; wi++) geNew.push({ code: "GE 写作课 " + (wi + 1), why: "Writing 要求缺口", generic: true });
      if (!nwcCovered) addGeNew("ENV S 130A", "World Cultures");
      if (!ethCovered) addGeNew("ENV S 189", "Ethnicity");
      if (!ahiCovered) addGeNew("ENV S 173", "American History and Institutions");
      if (input.langAtUCSB) {
        for (var li = 1; li <= 3; li++) geNew.push({ code: "外语 level " + li, why: "Area B（UCSB 修课途径）", generic: true, units: 5 });
      }
      var geUnits = 0;
      geNew.forEach(function (g) {
        g.units = g.generic ? (g.units || 4) : units(g.code);
        geUnits += g.units;
      });
      return { areaCovered: areaCovered, writingCovered: writingCovered, nwcCovered: nwcCovered,
               ethCovered: ethCovered, ahiCovered: ahiCovered, geNew: geNew, geUnits: geUnits };
    }
    function currentPlanSet() {
      var s = new Set(Object.keys(selected));
      have.forEach(function (c) { s.add(c); });
      return s;
    }
    function totalUnitsFor() {
      var majorUnits = 0;
      Object.keys(selected).forEach(function (c) { majorUnits += units(c); });
      if (cReq) majorUnits += 16; /* C 区 4 块 */
      return majorUnits + evaluateGe(currentPlanSet()).geUnits;
    }
    /* ---- GE 感知优化：取“专业+GE新增”总学分最小者。
     * 单组轮换会陷入局部最优（如专题预备两门课需联动换组），故单组 pass 后再做双组联动 pass。 ---- */
    function snapshotState() {
      return { selected: Object.assign({}, selected), occupied: new Set(occupied) };
    }
    function restoreState(snap, reqIds) {
      Object.keys(selected).forEach(function (k) { delete selected[k]; });
      Object.assign(selected, snap.selected);
      occupied = snap.occupied;
      reqIds.forEach(function (id) { choice[id] = snap.choices[id]; });
    }
    function releaseReq(reqId) {
      (choice[reqId] || []).forEach(function (c) {
        var nc = normCode(c);
        if (have.has(nc)) return;
        delete selected[nc];
        occupied.delete(nc);
        var p = EQUIV_PARTNER[nc];
        if (p) occupied.delete(normCode(p));
      });
    }
    function applyGroup(req, g) {
      var take = g.take === "one" ? [pickOne(g)] : g.courses.slice();
      var usable = take.filter(function (c) { return !occupied.has(normCode(c)) || have.has(normCode(c)); });
      if (g.take === "one" ? usable.length === 0 : usable.length !== take.length) return null;
      take.forEach(function (c) { if (!have.has(normCode(c))) markOccupied(c, req.id); });
      choice[req.id] = take;
      return take;
    }
    var bestTotal = totalUnitsFor();
    var optReqs = ordered.filter(function (r) { return r.type !== "elective" && r.options && r.options.length; });
    for (var pass = 0; pass < 2; pass++) {
      var improved = false;
      optReqs.forEach(function (req) {
        var current = choice[req.id] || [];
        var curKey = current.map(normCode).sort().join("|");
        req.options.map(function (g) { return normalizeGroup(g); }).forEach(function (g) {
          var snap = snapshotState(); snap.choices = {}; snap.choices[req.id] = choice[req.id];
          releaseReq(req.id);
          var take = applyGroup(req, g);
          var takeKey = take ? take.map(normCode).sort().join("|") : "";
          if (!take || takeKey === curKey) { restoreState(snap, [req.id]); return; }
          var total = totalUnitsFor();
          if (total < bestTotal) { bestTotal = total; improved = true; current = take; curKey = takeKey; }
          else restoreState(snap, [req.id]);
        });
      });
      if (!improved) break;
    }
    /* 双组联动 pass：两条要求同时换组（组合数过大时跳过） */
    for (var i1 = 0; i1 < optReqs.length; i1++) {
      for (var i2 = i1 + 1; i2 < optReqs.length; i2++) {
        var r1 = optReqs[i1], r2 = optReqs[i2];
        var g1s = r1.options.map(function (g) { return normalizeGroup(g); });
        var g2s = r2.options.map(function (g) { return normalizeGroup(g); });
        if (g1s.length * g2s.length > 400) continue;
        var snap = snapshotState();
        snap.choices = {}; snap.choices[r1.id] = choice[r1.id]; snap.choices[r2.id] = choice[r2.id];
        var bestPair = null;
        g1s.forEach(function (g1) {
          g2s.forEach(function (g2) {
            var s2 = snapshotState(); s2.choices = {}; s2.choices[r1.id] = choice[r1.id]; s2.choices[r2.id] = choice[r2.id];
            releaseReq(r1.id); releaseReq(r2.id);
            var t1 = applyGroup(r1, g1), t2 = applyGroup(r2, g2);
            if (!t1 || !t2) { restoreState(s2, [r1.id, r2.id]); return; }
            var total = totalUnitsFor();
            if (total < bestTotal && (!bestPair || total < bestPair.total)) bestPair = { total: total, t1: t1, t2: t2 };
            restoreState(s2, [r1.id, r2.id]);
          });
        });
        if (bestPair) {
          releaseReq(r1.id); releaseReq(r2.id);
          bestPair.t1.forEach(function (c) { if (!have.has(normCode(c))) markOccupied(c, r1.id); });
          bestPair.t2.forEach(function (c) { if (!have.has(normCode(c))) markOccupied(c, r2.id); });
          choice[r1.id] = bestPair.t1; choice[r2.id] = bestPair.t2;
          bestTotal = bestPair.total;
        } else restoreState(snap, [r1.id, r2.id]);
      }
    }
    /* 最终 GE 评估 */
    var planSet = currentPlanSet();
    var ev = evaluateGe(planSet);
    var areaCovered = ev.areaCovered, writingCovered = ev.writingCovered,
        nwcCovered = ev.nwcCovered, ethCovered = ev.ethCovered, ahiCovered = ev.ahiCovered;
    var geNew = ev.geNew;
    /* GE 新增课的先修树（查目录；通用块无先修） */
    geNew.forEach(function (g) {
      if (g.generic) { g.tree = null; return; }
      var cat = catalog[normCode(g.code)];
      if (!cat) { warnings.push("GE 新增课 " + g.code + " 不在 2026-27 目录中，改按通用块处理"); g.generic = true; g.units = 4; g.tree = null; return; }
      var t = parsePrereq(cat.prerequisites_raw || "");
      g.tree = (t && t.fallback)
        ? ((cat.prerequisites_courses || []).length ? { op: "OR", items: cat.prerequisites_courses.map(function (c) { return { code: normCode(c) }; }) } : null)
        : t;
    });

    /* ---- 排学期：关键路径优先的列表调度 ---- */
    var nodes = []; /* { code, units, tree, generic, why } */
    Object.keys(selected).forEach(function (c) {
      if (have.has(c)) return;
      nodes.push({ code: c, units: units(c), tree: treeOf[c] || null, generic: false });
    });
    geNew.forEach(function (g) {
      if (have.has(normCode(g.code))) return;
      nodes.push({ code: g.code, units: g.units, tree: g.tree || null, generic: !!g.generic, why: g.why });
    });
    cBlocks.forEach(function (b) {
      nodes.push({ code: b, units: 4, tree: null, generic: true, why: "Area C 校外集中方向" });
    });
    var nodeByCode = {};
    nodes.forEach(function (n) { nodeByCode[normCode(n.code)] = n; });
    var inPlan = new Set(nodes.map(function (n) { return normCode(n.code); }));
    have.forEach(function (c) { inPlan.add(c); });

    /* 最早学期（拓扑最长路；未满足先修 → 警告并按已满足处理） */
    var earliest = {}, unmetWarnings = [];
    var nodes2 = nodes.slice();
    nodes2.forEach(function (n) { earliest[normCode(n.code)] = 0; });
    have.forEach(function (c) { earliest[normCode(c)] = -1; });
    var changed = true, iter = 0;
    while (changed && iter++ < 50) {
      changed = false;
      nodes.forEach(function (n) {
        if (!n.tree) return;
        var et = treeEarliest(n.tree, earliest, inPlan);
        if (et >= 0 && et + 1 > earliest[normCode(n.code)]) {
          earliest[normCode(n.code)] = et + 1; changed = true;
        }
      });
    }
    /* 未满足先修警告：AND 缺失的必修叶、OR 无计划内备选项的整组 */
    function treeMissingLeaves(node) {
      if (!node) return [];
      if (node.code) return inPlan.has(normCode(node.code)) ? [] : [normCode(node.code)];
      if (node.wildcard !== undefined) {
        var hit = false;
        inPlan.forEach(function (c) {
          var m = c.match(/^(.+?)\s+(\d+)([A-Z]*)$/);
          if (m && (!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0)) hit = true;
        });
        return hit ? [] : [(node.wildcard || "") + " " + (node.prefix || "") + "*"];
      }
      if (node.op === "AND") {
        var out = [];
        node.items.forEach(function (x) { out = out.concat(treeMissingLeaves(x)); });
        return out;
      }
      var anyClean = node.items.some(function (x) { return treeMissingLeaves(x).length === 0; });
      if (anyClean) return [];
      var all = [];
      node.items.forEach(function (x) { all = all.concat(treeMissingLeaves(x)); });
      return all;
    }
    nodes.forEach(function (n) {
      if (!n.tree) return;
      var missing = treeMissingLeaves(n.tree);
      if (missing.length) unmetWarnings.push(n.code + " 的先修 " + missing.slice(0, 4).join("、") + " 不在计划内（假设已满足或需另修）");
    });
    unmetWarnings.forEach(function (w) { warnings.push(w); });

    /* 关键度：下游最长链 + 直连解锁数 */
    var downstream = {};
    function downstreamOf(code, seen) {
      var nc = normCode(code);
      if (downstream[nc] !== undefined) return downstream[nc];
      if (seen && seen.has(nc)) return 0;
      var s2 = new Set(seen || []); s2.add(nc);
      var best = 0;
      nodes.forEach(function (n) {
        if (!n.tree) return;
        var leaves = treeLeafCodes(n.tree, []);
        if (leaves.indexOf(nc) >= 0) {
          var d = 1 + downstreamOf(n.code, s2);
          if (d > best) best = d;
        }
      });
      downstream[nc] = best;
      return best;
    }
    var fanout = {};
    nodes.forEach(function (n) {
      if (!n.tree) return;
      treeLeafCodes(n.tree, []).forEach(function (l) { fanout[l] = (fanout[l] || 0) + 1; });
    });
    nodes.forEach(function (n) {
      n.criticality = downstreamOf(n.code);
      n.fanout = fanout[normCode(n.code)] || 0;
    });

    /* 逐学期调度 */
    var terms = [];
    for (var ti = 0; ti < nTerms; ti++) terms.push({ courses: [], units: 0 });
    var placed = {};
    var remaining = nodes.slice();
    for (var t = 0; t < nTerms; t++) {
      var ready = remaining.filter(function (n) {
        if (earliest[normCode(n.code)] > t) return false;
        /* 先修须在更早学期（同学期不算满足；并发先修 v1 从严）；计划外先修按已满足处理并警告 */
        if (!n.tree) return true;
        return treeReadyStatus(n.tree, placed, t, have) !== "PENDING";
      });
      ready.sort(function (a, b) {
        if (b.criticality !== a.criticality) return b.criticality - a.criticality;
        if (b.fanout !== a.fanout) return b.fanout - a.fanout;
        return b.units - a.units;
      });
      ready.forEach(function (n) {
        if (terms[t].units + n.units <= cap) {
          terms[t].courses.push(n);
          terms[t].units += n.units;
          placed[normCode(n.code)] = t;
        }
      });
      remaining = remaining.filter(function (n) { return placed[normCode(n.code)] === undefined; });
      if (!remaining.length) break;
    }
    /* 三值先修判定：SAT（已满足）/ PENDING（计划内先修尚未排入更早学期）/ EXTERNAL（计划外，假设已满足并警告） */
    function treeReadyStatus(node, placedMap, term, haveSet) {
      if (!node) return "SAT";
      if (node.code) {
        var c = normCode(node.code);
        if (haveSet.has(c)) return "SAT";
        if (placedMap[c] !== undefined && placedMap[c] < term) return "SAT";
        if (inPlan.has(c)) return "PENDING";
        return "EXTERNAL";
      }
      if (node.wildcard !== undefined) {
        var sat = false, pend = false;
        var check = function (c, placedTerm) {
          var m = c.match(/^(.+?)\s+(\d+)([A-Z]*)$/);
          if (!m) return;
          if ((!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0)) {
            if (placedTerm === true || placedTerm < term) sat = true;
            else if (inPlan.has(c)) pend = true;
          }
        };
        Object.keys(placedMap).forEach(function (c) { check(c, placedMap[c]); });
        haveSet.forEach(function (c) { check(c, true); });
        if (sat) return "SAT";
        var anyInPlan = false;
        inPlan.forEach(function (c) {
          var m = c.match(/^(.+?)\s+(\d+)([A-Z]*)$/);
          if (m && (!node.wildcard || m[1] === node.wildcard) && (!node.prefix || m[2].indexOf(node.prefix) === 0)) anyInPlan = true;
        });
        if (pend || anyInPlan) return "PENDING";
        return "EXTERNAL";
      }
      if (node.op === "AND") {
        var stats = node.items.map(function (x) { return treeReadyStatus(x, placedMap, term, haveSet); });
        if (stats.indexOf("PENDING") >= 0) return "PENDING";
        return "SAT";
      }
      var statsOr = node.items.map(function (x) { return treeReadyStatus(x, placedMap, term, haveSet); });
      if (statsOr.indexOf("SAT") >= 0) return "SAT";
      if (statsOr.indexOf("PENDING") >= 0) return "PENDING";
      return "EXTERNAL";
    }

    /* 修复 pass：学期容量碎片导致的小课滞留——把区间内无后续依赖的课往后挪，腾出位置 */
    for (var rep = 0; rep < 10 && remaining.length; rep++) {
      var progress = false;
      var still = [];
      remaining.forEach(function (u) {
        var placedNow = false;
        var uCode = normCode(u.code);
        for (var tt = Math.max(0, earliest[uCode]); tt < nTerms && !placedNow; tt++) {
          if (treeReadyStatus(u.tree, placed, tt, have) === "PENDING") continue;
          if (terms[tt].units + u.units <= cap) {
            terms[tt].courses.push(u); terms[tt].units += u.units; placed[uCode] = tt; placedNow = true; progress = true;
          } else {
            var cands = terms[tt].courses.slice().sort(function (a, b) { return b.units - a.units; });
            for (var ci = 0; ci < cands.length && !placedNow; ci++) {
              var v = cands[ci];
              var vCode = normCode(v.code);
              if (terms[tt].units - v.units + u.units > cap) continue;
              for (var t2 = tt + 1; t2 < nTerms && !placedNow; t2++) {
                if (terms[t2].units + v.units > cap) continue;
                var blocked = false;
                Object.keys(placed).forEach(function (wCode) {
                  var wt = placed[wCode];
                  if (wt <= tt || wt > t2) return;
                  var wNode = nodeByCode[wCode];
                  if (wNode && wNode.tree && treeLeafCodes(wNode.tree, []).indexOf(vCode) >= 0) blocked = true;
                });
                if (blocked) continue;
                terms[tt].courses = terms[tt].courses.filter(function (x) { return normCode(x.code) !== vCode; });
                terms[tt].units -= v.units;
                terms[t2].courses.push(v); terms[t2].units += v.units; placed[vCode] = t2;
                terms[tt].courses.push(u); terms[tt].units += u.units; placed[uCode] = tt;
                placedNow = true; progress = true;
              }
            }
          }
        }
        if (!placedNow) still.push(u);
      });
      remaining = still;
      if (!progress) break;
    }

    var unscheduled = remaining.map(function (n) { return n.code; });
    var totalUnits = terms.reduce(function (s, t) { return s + t.units; }, 0);
    var unscheduledUnits = remaining.reduce(function (s, n) { return s + n.units; }, 0);
    var criticalLen = 0;
    nodes.forEach(function (n) { if (earliest[normCode(n.code)] + 1 > criticalLen) criticalLen = earliest[normCode(n.code)] + 1; });
    var minTermsByLoad = Math.ceil((totalUnits + unscheduledUnits) / cap);
    var feasible = unscheduled.length === 0;
    var termNames = ["秋季", "冬季", "春季"];
    /* 去掉尾部空学期 */
    var lastNonEmpty = -1;
    terms.forEach(function (t, i) { if (t.courses.length) lastNonEmpty = i; });
    var outTerms = terms.slice(0, lastNonEmpty + 1);
    var termLabels = outTerms.map(function (_, i) {
      var year = Math.floor(i / 3) + 1;
      var q = termNames[(startTerm + i) % 3];
      return "第" + year + "年" + q;
    });
    /* 关键课：slack 为 0（拖期即拖毕业）或 fanout ≥ 6 */
    var keyCourses = nodes.filter(function (n) {
      var slack = (nTerms - 1 - (n.criticality)) - (placed[normCode(n.code)] === undefined ? earliest[normCode(n.code)] : placed[normCode(n.code)]);
      n.slack = slack;
      return placed[normCode(n.code)] !== undefined && (slack <= 0 || n.fanout >= 6);
    }).map(function (n) {
      return { code: n.code, fanout: n.fanout, criticality: n.criticality, slack: n.slack, term: placed[normCode(n.code)] };
    }).sort(function (a, b) { return b.fanout - a.fanout; });

    /* 覆盖清单 */
    var coverage = { major: [], ge: [] };
    ordered.forEach(function (req) {
      if (req.type === "elective") return;
      coverage.major.push({ id: req.id, name: req.name_zh || req.name, courses: choice[req.id] || [] });
    });
    if (b1) coverage.major.push({ id: "b-1", name: "B-1 专业选修（32 学分）", courses: choice["b-1"] || [] });
    if (cReq) coverage.major.push({ id: "c-outside-concentration", name: "C. 校外集中方向（16 学分）", courses: cBlocks });
    coverage.ge.push({ id: "areaA", name: "Area A 英语阅读与写作", courses: ["WRIT 2", "WRIT 107EP"] });
    coverage.ge.push({ id: "areaB", name: "Area B 外语", courses: input.langAtUCSB ? ["外语 level 1", "外语 level 2", "外语 level 3"] : ["（高中/考试途径，0 学分）"] });
    ["areaC", "areaD", "areaE"].forEach(function (area, ai) {
      var gapBlocks = geNew.filter(function (g) { return g.generic && g.why === "Area " + area.slice(-1) + " 缺口"; }).map(function (g) { return g.code; });
      var shown = areaCovered[area].concat(gapBlocks);
      coverage.ge.push({ id: area, name: "Area " + "CDE"[ai], courses: shown.length ? shown : ["（缺口走 GE 选修）"] });
    });
    coverage.ge.push({ id: "areaF", name: "Area F 艺术", courses: ["ENV S 136O"] });
    coverage.ge.push({ id: "areaG", name: "Area G 文学", courses: ["ENV S 160"] });
    coverage.ge.push({ id: "writing", name: "Writing 6 门", courses: ["WRIT 2", "WRIT 107EP"].concat(GE_MARK.writing.filter(function (c) { return planSet.has(normCode(c)); })) });
    coverage.ge.push({ id: "nwc", name: "World Cultures", courses: nwcCovered ? GE_MARK.nwc.filter(function (c) { return planSet.has(normCode(c)); }) : ["ENV S 130A"] });
    coverage.ge.push({ id: "eth", name: "Ethnicity", courses: ethCovered ? GE_MARK.eth.filter(function (c) { return planSet.has(normCode(c)); }) : ["ENV S 189"] });
    coverage.ge.push({ id: "qnt", name: "Quantitative Relationships", courses: ["（任一专业预备课即满足）"] });
    coverage.ge.push({ id: "ahi", name: "American History and Institutions", courses: ahiCovered ? GE_MARK.ahi.filter(function (c) { return planSet.has(normCode(c)); }) : ["ENV S 173"] });

    if (fallbackCount) warnings.push("先修原文为空的课程 " + fallbackCount + " 门，暂按目录快照扁平列表（任一满足）处理");
    warnings.push("先修逻辑按目录原文 and/or 解析；“可同期修读”在 v1 中从严按先修学期处理，请以 GOLD 为准复核");
    warnings.push("GE 双计映射引自环境研究系 B.S. GE 计划（2022-08 修订），2026-27 目录下以 GOLD 标注为准");
    if (input.langAtUCSB) warnings.push("外语走 UCSB 修课途径：学位总学分要求为 184 学分（已计入 3 门外语块）");
    var b2choice = choice["b-2"] || [];
    if (b2choice.some(function (c) { return units(c) <= 0; })) warnings.push("B-2（192/194/199/199RA）为实习/独立研究，目录学分记 0，实际学分以 GOLD 为准");

    return {
      feasible: feasible,
      years: years, cap: cap, nTerms: nTerms,
      terms: outTerms.map(function (t, i) {
        return { label: termLabels[i], units: t.units, courses: t.courses.map(function (n) { return { code: n.code, units: n.units, generic: !!n.generic, key: keyCourses.some(function (k) { return normCode(k.code) === normCode(n.code); }) }; }) };
      }),
      unscheduled: unscheduled,
      totalUnits: totalUnits,
      criticalPathTerms: criticalLen,
      minTermsByLoad: minTermsByLoad,
      neededTerms: Math.max(criticalLen, minTermsByLoad),
      extraTerms: Math.max(0, Math.max(criticalLen, minTermsByLoad) - nTerms),
      suggestedYears: Math.ceil(Math.max(criticalLen, minTermsByLoad) / 3),
      keyCourses: keyCourses,
      coverage: coverage,
      warnings: warnings
    };
  }

  return {
    normCode: normCode, unitsNum: unitsNum, esc: esc,
    parsePrereq: parsePrereq, treeSatisfied: treeSatisfied,
    treeLeafCodes: treeLeafCodes, treeEarliest: treeEarliest,
    buildPlan: buildPlan, GE_MARK: GE_MARK
  };
});
