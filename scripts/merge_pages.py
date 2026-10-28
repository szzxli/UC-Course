#!/usr/bin/env python3
"""四页整合装配：把旧单页拼成 requirements/courses/plan 三个合并页。
策略：每段原页内联脚本整体包进 IIFE（消除函数/变量冲突），只改元素 id 冲突处与跨页链接。
原页文件不动；输出写到 web/requirements.html、web/courses.html、web/plan.html（后两者覆盖原文件）。
用法：python3 scripts/merge_pages.py [requirements|courses|plan]（不带参数则全量；注意 courses/plan 的输入即输出，全量重跑会损坏已合并页，仅在原页状态下全量跑）。
"""
import re, sys
ONLY = set(sys.argv[1:])

WEB = "/home/hatch/workspace/uc-course/web"

def read(name):
    with open(f"{WEB}/{name}", encoding="utf-8") as f:
        return f.read()

def extract_div_body(html, start_marker):
    """从 start_marker 处的 <div ...> 起，按 div 深度取到配对闭合，返回 inner（不含外层标签）。"""
    i = html.index(start_marker)
    gt = html.index(">", i) + 1
    depth = 1
    j = gt
    tag_re = re.compile(r"</?div\b[^>]*>", re.I)
    while depth > 0:
        m = tag_re.search(html, j)
        if not m:
            raise ValueError("unbalanced div at " + start_marker)
        depth += -1 if m.group(0).startswith("</") else 1
        j = m.end()
        if depth == 0:
            return html[gt:m.start()]
    raise ValueError("unreachable")

def body_region(html):
    """<body> 到第一个 <script（含 src）之间的区域（不含脚本字符串干扰）。"""
    b = html.index("<body>") + len("<body>")
    s = html.index("<script", b)
    return html[b:s]

def page_inner(html):
    region = body_region(html)
    return extract_div_body(region, '<div class="page">')

def block_after_page(html, marker):
    """取 .page 之后、<nav 之前的指定 id 块（如 major 的 selBar/eqPop）。"""
    region = body_region(html)
    i = region.index(marker)
    gt = region.index(">", i) + 1
    depth = 1
    j = gt
    tag_re = re.compile(r"</?div\b[^>]*>", re.I)
    while depth > 0:
        m = tag_re.search(region, j)
        depth += -1 if m.group(0).startswith("</") else 1
        j = m.end()
    return region[i:j]

def inline_script(html):
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    if not m:
        raise ValueError("no inline script")
    return m.group(1)

def iife(script):
    script = re.sub(r'\n\s*I18N\.initSwitcher\("langSel"\);\n', "\n", script)
    script = re.sub(r'\n\s*navActive\("[^"]+"\);\n', "\n", script)
    return "(function(){\n" + script + "\n})();"

TABBAR = """<nav class="tabbar">
  <a href="index.html" data-page="index"><span class="ico">🏠</span><span data-i18n="nav.home">首页</span></a>
  <a href="courses.html" data-page="courses"><span class="ico">🔍</span><span data-i18n="nav.courses">选课</span></a>
  <a href="requirements.html" data-page="requirements"><span class="ico">🎓</span><span data-i18n="nav.requirements">毕业要求</span></a>
  <a href="plan.html" data-page="plan"><span class="ico">🗓️</span><span data-i18n="nav.plan">排课</span></a>
</nav>"""

def seg_script(segs, page_key, extra=""):
    btns = "\n".join(
        f'    <button data-seg="{s}" data-i18n="{k}">{fb}</button>'
        for s, k, fb in segs
    )
    seg_ids = "[" + ", ".join(f'"{s}"' for s, _, _ in segs) + "]"
    return f"""<div class="seg">
{btns}
  </div>""", f"""<script>
(function(){{
  var SEGS = {seg_ids};
  function show(id){{
    SEGS.forEach(function(s){{ document.getElementById("sec-"+s).hidden = (s !== id); }});
    document.querySelectorAll("[data-seg]").forEach(function(b){{ b.classList.toggle("on", b.dataset.seg === id); }});
  }}
  function fromHash(){{
    var h = (location.hash || "").replace("#", "").split("?")[0];
    return SEGS.indexOf(h) >= 0 ? h : SEGS[0];
  }}
  document.querySelectorAll("[data-seg]").forEach(function(b){{
    b.addEventListener("click", function(){{
      history.replaceState(null, "", "#" + b.dataset.seg);
      show(b.dataset.seg);
    }});
  }});
  window.addEventListener("hashchange", function(){{ show(fromHash()); }});
  {extra}
  I18N.init().then(function(){{
    I18N.initSwitcher("langSel");
    navActive("{page_key}");
    show(fromHash());
  }});
}})();
</script>"""

def assemble(title_key, title_fb, brand_key, brand_fb, scripts, sections_html, seg_html, page_script):
    script_tags = "\n".join(f'<script src="{s}"></script>' for s in scripts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title data-i18n="{title_key}">{title_fb}</title>
<link rel="stylesheet" href="css/app.css">
<meta name="theme-color" content="#132625">
</head>
<body>
<div class="topbar"><div class="topbar-in">
  <div class="brand" data-i18n="{brand_key}">{brand_fb}</div>
  <div><select id="langSel" class="langsel" aria-label="language"></select></div>
</div></div>
<div class="page">
{seg_html}
{sections_html}
</div>
{TABBAR}
{script_tags}
{page_script}
</body>
</html>
"""

def write(name, content):
    with open(f"{WEB}/{name}", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote {name} ({len(content)} chars)")

# ---------------- 毕业要求页 ----------------
if not ONLY or "requirements" in ONLY:
  major_html = read("major.html")
  ge_html = read("ge.html")
  major_inner = page_inner(major_html)
  major_inner = major_inner.replace('href="engine.html"', 'href="plan.html#engine"')
  major_inner = major_inner.replace('href="pick.html"', 'href="courses.html#pick"')
  major_inner = major_inner.replace(
      '<a class="btn ghost" href="ge.html" data-i18n="major.goGe">',
      '<a class="btn ghost" href="#" id="goGeBtn" data-i18n="major.goGe">')
  major_inner = '<p class="hint" id="majorSub"></p>\n' + major_inner.replace(
      '<div class="sub" id="majorSub"></div>', '')
  # major 原 topbar 的 sub 已随 topbar 丢弃；上面在段首补一个 majorSub 占位（脚本只写 textContent）
  selbar = block_after_page(major_html, '<div id="selBar"')
  eqpop = block_after_page(major_html, '<div id="eqPop"')
  major_sec = major_inner + "\n" + selbar + "\n" + eqpop
  major_script = iife(inline_script(major_html))

  ge_inner = page_inner(ge_html)
  ge_inner = ge_inner.replace('id="srcNote"', 'id="geSrcNote"')
  ge_inner = ge_inner.replace('href="engine.html"', 'href="plan.html#engine"')
  ge_inner = '<p class="hint" id="geSub"></p>\n' + ge_inner
  ge_script = iife(inline_script(ge_html).replace('getElementById("srcNote")', 'getElementById("geSrcNote")'))

  seg_html, page_script = seg_script(
      [("major", "req.segMajor", "专业要求"), ("ge", "req.segGe", "通识要求")],
      "requirements",
      extra="""document.getElementById("goGeBtn").addEventListener("click", function(e){
      e.preventDefault();
      history.replaceState(null, "", "#ge");
      show("ge");
    });""")
  sections = f'<section id="sec-major">\n{major_sec}\n</section>\n<section id="sec-ge" hidden>\n{ge_inner}\n</section>'
  write("requirements.html", assemble(
      "title.requirements", "毕业要求 · UC 智选", "brand.requirements", "🎓 毕业要求",
      ["js/app.js", "js/i18n.js", "js/chat.js", "js/major.js"],
      sections, seg_html,
      f"<script>\n{major_script}\n</script>\n<script>\n{ge_script}\n</script>\n{page_script}"))

# ---------------- 选课页 ----------------
if not ONLY or "courses" in ONLY:
  courses_html = read("courses.html")
  pick_html = read("pick.html")
  courses_inner = page_inner(courses_html)
  courses_inner = '<p class="hint" id="campusSub"></p>\n' + courses_inner
  courses_script = iife(inline_script(courses_html))
  main = pick_html[pick_html.index("<main>") + len("<main>"):pick_html.index("</main>")]
  pick_inner = main
  pick_inner = pick_inner.replace('id="addBtn"', 'id="pickAddBtn"')
  pick_inner = pick_inner.replace('id="goPlanBtn"', 'id="pickGoPlanBtn"')
  pick_script_src = inline_script(pick_html)
  pick_script_src = pick_script_src.replace('getElementById("addBtn")', 'getElementById("pickAddBtn")')
  pick_script_src = pick_script_src.replace('getElementById("goPlanBtn")', 'getElementById("pickGoPlanBtn")')
  # 非试点不再用真实已修套 ES 要求：与 pilotNote 文案一致，统一按示例算
  pick_script_src = pick_script_src.replace(
      'var have = DEMO ? [] : getHave();',
      'var have = (DEMO || !PERSONAL) ? [] : getHave();')
  pick_script_src = pick_script_src.replace(
      'var planned0 = DEMO ? [] : Sget("myCourses", []).map(function (x) { return x.code; });',
      'var planned0 = (DEMO || !PERSONAL) ? [] : Sget("myCourses", []).map(function (x) { return x.code; });')
  pick_script_src = pick_script_src.replace(
      'if (DEMO) document.getElementById("pickAddBtn").disabled = true;',
      'if (DEMO || !PERSONAL) document.getElementById("pickAddBtn").disabled = true;')
  pick_script_src = pick_script_src.replace(
      'if (DEMO || !RESULT) return;',
      'if (DEMO || !PERSONAL || !RESULT) return;')
  pick_script = iife(pick_script_src)
  seg_html, page_script = seg_script(
      [("search", "courses.segSearch", "查课"), ("pick", "courses.segPick", "智能选课")],
      "courses")
  sections = f'<section id="sec-search">\n{courses_inner}\n</section>\n<section id="sec-pick" hidden>\n{pick_inner}\n</section>'
  write("courses.html", assemble(
      "title.courses", "选课 · UC 智选", "brand.courses", "🔍 选课",
      ["js/app.js", "js/i18n.js", "js/chat.js", "js/major.js", "js/engine.js", "js/pick.js"],
      sections, seg_html,
      f"<script>\n{courses_script}\n</script>\n<script>\n{pick_script}\n</script>\n{page_script}"))

# ---------------- 排课页 ----------------
if not ONLY or "plan" in ONLY:
  plan_html = read("plan.html")
  traj_html = read("trajectory.html")
  engine_html = read("engine.html")
  plan_inner = page_inner(plan_html)
  plan_inner = plan_inner.replace('href="major.html"', 'href="requirements.html#major"')
  plan_script = iife(inline_script(plan_html))
  traj_inner = page_inner(traj_html)
  traj_inner = traj_inner.replace('href="major.html"', 'href="requirements.html#major"')
  traj_script = iife(inline_script(traj_html))
  engine_inner = page_inner(engine_html)
  engine_inner = engine_inner.replace('id="statusLine"', 'id="engStatusLine"')
  engine_inner = '<p class="hint" id="engSub"></p>\n' + engine_inner
  engine_script = iife(inline_script(engine_html).replace('getElementById("statusLine")', 'getElementById("engStatusLine")'))
  seg_html, page_script = seg_script(
      [("plan", "plan.segPlan", "排课表"), ("traj", "plan.segTraj", "进度"), ("engine", "plan.segEngine", "智能排课")],
      "plan")
  sections = (f'<section id="sec-plan">\n{plan_inner}\n</section>\n'
              f'<section id="sec-traj" hidden>\n{traj_inner}\n</section>\n'
              f'<section id="sec-engine" hidden>\n{engine_inner}\n</section>')
  write("plan.html", assemble(
      "title.plan", "排课 · UC 智选", "brand.plan", "🗓️ 排课",
      ["js/app.js", "js/i18n.js", "js/chat.js", "js/planner.js", "js/major.js", "js/engine.js"],
      sections, seg_html,
      f"<script>\n{plan_script}\n</script>\n<script>\n{traj_script}\n</script>\n<script>\n{engine_script}\n</script>\n{page_script}"))
  print("done")
print("done")
