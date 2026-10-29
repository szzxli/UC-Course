#!/usr/bin/env python3
# UCSD 七学院通识文件建造器（第二批）
# 数据来源：各学院官网 GE 页 + UCSD catalog（2026-10-28 核对），见各文件 sources。
# 口径：① 固定序列/有界清单全量录入；② 按学期动态清单（Muir 序列、Sixth breadth、Seventh alternatives、
# Warren formal skills、Marshall breadth、ERC 区域课单）只写规则 + 链接，不编造课号；
# ③ 规则型要求（达标、论文、转学衔接）用 count=null + note，不编课程。
# 输出 data/ge/ucsd-*.json 与 web/data/ge/ucsd-*.json 两份一致；另做 name_zh 齐全与快照覆盖检查。
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def R(id, name, name_zh, count, courses, note, note_zh):
    return {"id": id, "name": name, "name_zh": name_zh, "count": count,
            "courses": courses, "note": note, "note_zh": note_zh}

def F(campus_file, title, title_zh, school, source_url, sources, source_note, sections):
    return {"campus": "UCSD", "title": title, "title_zh": title_zh, "degree": "",
            "school": school, "source_url": source_url, "sources": sources,
            "source_note": source_note, "checked": "2026-10-28",
            "sections": [{"id": s[0], "title": s[1], "title_zh": s[2],
                          "requirements": s[3]} for s in sections]}

COLLEGES = {}

# ---------------- Revelle ----------------
REV_BIO = ["BILD 1", "BILD 2", "BILD 3", "BILD 5", "BILD 7", "BILD 10", "BILD 12",
           "COGS 17", "BILD X13", "BILD 18", "BILD 20", "BILD 22", "BILD 26", "BILD 28",
           "BILD 30", "BILD 32", "BILD 36", "BILD 38", "BILD 42", "BILD 44", "BILD 46",
           "BILD 51", "BILD 60", "BILD 61"]
REV_CHEM = ["CHEM 4", "CHEM 6A", "CHEM 6B", "CHEM 6C", "CHEM 6AH", "CHEM 6BH",
            "CHEM 6CH", "CHEM 11"]
REV_PHYS = ["ASTR 1", "ASTR 2", "ASTR 3", "ASTR 4", "ASTR 20A", "ASTR 20B",
            "PHYS 8", "PHYS 10", "PHYS 11", "PHYS 12",
            "PHYS 1A", "PHYS 1B", "PHYS 1C", "PHYS 2A", "PHYS 2B", "PHYS 2C", "PHYS 2D",
            "PHYS 4A", "PHYS 4B", "PHYS 4C", "PHYS 4D", "PHYS 4E"]
REV_ADD = ["ESYS 10", "SIO 1", "SIO 3", "SIO 10", "SIO 12", "SIO 15", "SIO 16",
           "SIO 20", "SIO 25", "SIO 30", "SIO 35", "SIO 40", "SIO 45", "SIO 46GS",
           "SIO 50", "SIO 60", "SIO 121GS", "PHIL 12", "ASTR 15"]
REV_SOC_COGS = ["COGS 1", "COGS 9", "COGS 10", "COGS 11", "COGS 12", "COGS 13",
                "COGS 14A", "COGS 15", "COGS 20", "COGS 100", "COGS 101A", "COGS 101B",
                "COGS 101C", "COGS 102A", "COGS 102B", "COGS 102C", "COGS 108",
                "COGS 110", "COGS 115", "COGS 120", "COGS 143", "COGS 151",
                "COGS 152", "COGS 153", "COGS 154", "COGS 155", "COGS 156",
                "COGS 157", "COGS 164", "COGS 169", "COGS 171", "COGS 172",
                "COGS 174", "COGS 175", "COGS 176", "COGS 178", "COGS 179",
                "COGS 184", "COGS 188"]
REV_SOC_RESTRICTED = ["AAS 10", "AAS 11", "AAS 14", "AAS 15", "COMM 10", "COMM 20",
                      "COMM 30", "COMM 80", "ENG 30", "GSS 20", "GSS 22", "GSS 27",
                      "LATI 10", "LATI 50", "PHIL 51", "PHIL 148",
                      "HILD 7A", "HILD 7B", "HILD 7C"]
COLLEGES["revelle"] = F(
    "revelle", "Revelle College General Education", "Revelle 学院通识",
    "Revelle College", "https://revelle.ucsd.edu/academics/general-education/index.html",
    [{"label": "Revelle GE index", "url": "https://revelle.ucsd.edu/academics/general-education/index.html"},
     {"label": "Natural Science", "url": "https://revelle.ucsd.edu/academics/general-education/nat-science.html"},
     {"label": "Social Science", "url": "https://revelle.ucsd.edu/academics/general-education/soc-science.html"}],
    "Revelle 学院官网 GE 页（2026-10-28 核对）；转学规则见学院 Fall 2026 转学要求页。",
    [("humanities", "Humanities", "人文", [
        R("hum", "Humanities sequence", "人文序列", 5,
          ["HUM 1", "HUM 2", "HUM 3", "HUM 4", "HUM 5"],
          "Five-course sequence HUM 1 (winter) -> HUM 2 (spring) -> HUM 3 (fall/summer) -> HUM 4 (winter/summer) -> HUM 5 (spring/summer). Letter grade.",
          "人文 5 门序列：HUM 1（冬）→ HUM 2（春）→ HUM 3（秋/夏）→ HUM 4（冬/夏）→ HUM 5（春/夏），须 letter grade。")]),
     ("math", "Mathematics", "数学", [
        R("math", "Mathematics", "数学", 3,
          ["MATH 10A", "MATH 20A", "MATH 10B", "MATH 20B", "MATH 10C", "MATH 20C",
           "MATH 11", "MATH 18", "MATH 31AH", "DSC 10", "PHIL 10", "PSYC 60"],
          "1 quarter of calculus (MATH 10A/20A) plus 2 courses from MATH 10B/20B, 10C/20C, 11, 18/31AH, DSC 10, PHIL 10, PSYC 60. Letter grade.",
          "微积分 1 门（MATH 10A/20A）+ 再 2 门（MATH 10B/20B、10C/20C、11、18/31AH、DSC 10、PHIL 10、PSYC 60），须 letter grade。")]),
     ("natsci", "Natural Science", "自然科学", [
        R("natsci", "Natural Science", "自然科学", 5,
          REV_BIO + REV_CHEM + REV_PHYS + REV_ADD,
          "5 courses: 1 Biology + 1 Chemistry + 1 Physics + 2 additional from the approved list. Labs are not required for GE (major may require them). Science/engineering/math majors advised letter grade; arts/humanities/social science majors may take P/NP.",
          "自然科学 5 门：生物 1 门 + 化学 1 门 + 物理 1 门 + 另 2 门（批准清单内）。GE 不要求实验课（专业可能要求）。理工科专业建议 letter grade，文社科专业可 P/NP。")]),
     ("social", "Social Science", "社会科学", [
        R("social", "Social Science", "社会科学", 2,
          REV_SOC_COGS + REV_SOC_RESTRICTED,
          "2 courses (4 units each, upper or lower division) from approved social science departments. Letter grade. Department restrictions: AAS 10/11/14/15 only; COMM 10/20/30/80 only; COGS only the listed courses; Economics lower division only; ENG 30 only; GSS 20/22/27 only; LATI 10/50 only; Linguistics excluding language courses; PHIL 51/148 only; POLI 10-179; HILD 7A/7B/7C only. Other approved departments (any course unless restricted): Anthropology, Critical Gender Studies, Education Studies, Ethnic Studies, Human Developmental Science, International Studies, Psychology, Sociology, Urban Studies and Planning. Special Studies courses do not count; upper-division major courses may not overlap GE. Remote (R) versions accepted.",
          "社会科学 2 门（每门 4 学分，高/低年级均可），须 letter grade。批准系所 + 限课：AAS 仅 10/11/14/15；COMM 仅 10/20/30/80；COGS 仅下表课程；经济仅低年级；ENG 仅 30；GSS 仅 20/22/27；LATI 仅 10/50；语言学不含语言课；PHIL 仅 51/148；POLI 10–179；HILD 仅 7A/7B/7C。其余批准系（人类学、批判性别研究、教育研究、族裔研究、人类发展科学、国际研究、心理、社会学、城市研究与规划）不限课程。Special Studies 不计；高年级专业课不得与 GE 重叠；R 远程版亦可。")]),
     ("arts", "Fine Arts", "美术", [
        R("arts", "Fine Arts", "美术", 1, [],
          "1 course (2-4 units) from Music, Theatre, Dance, or Visual Arts. May be P/NP unless the major requires a letter grade.",
          "美术 1 门（2–4 学分），音乐/戏剧/舞蹈/视觉艺术中选；除非专业要求 letter grade，否则可 P/NP。")]),
     ("language", "Language", "外语", [
        R("language", "Language proficiency", "外语达标", None, [],
          "Proficiency in a language other than English, demonstrated by exam or completion of a fourth-quarter intermediate course (0-4 courses depending on placement). May be P/NP unless the major requires a letter grade.",
          "非英语外语达标：考试通过，或修到第四学期中级水平（按 placement 从 0 到 4 门不等）；除非专业要求 letter grade，否则可 P/NP。")]),
     ("transfer", "Transfer Students", "转学生衔接", [
        R("transfer-hum100", "HUM 100 for transfers", "转学生 HUM 100", 1, ["HUM 100"],
          "All transfer students admitted Fall 2024 and later must take HUM 100 within their first year. Students with IGETC/Cal-GETC: HUM 1-5 waived, but full Mathematics and Natural Science requirements still required. UC Reciprocity satisfies lower-division GE; required upper-division GE is HUM 100. Transfer students admitted Fall 2026 and after: Natural Science is 3 courses (2 from different Biology/Chemistry/Physics disciplines + 1 additional).",
          "2024 秋及以后入学的转学生须在第一年内修 HUM 100。IGETC/Cal-GETC 免 HUM 1–5，但数学与自然科学须全修；UC Reciprocity 满足低年级 GE，高年级 GE 为 HUM 100。2026 秋及以后入学的转学生自然科学为 3 门（生物/化学/物理中两个不同学科 2 门 + 另 1 门）。")])])

# ---------------- Muir ----------------
COLLEGES["muir"] = F(
    "muir", "John Muir College General Education", "Muir 学院通识",
    "John Muir College", "https://muir.ucsd.edu/academics/degree_reqs.html",
    [{"label": "Muir degree requirements", "url": "https://muir.ucsd.edu/academics/degree_reqs.html"},
     {"label": "UCSD catalog: Muir", "url": "https://catalog.ucsd.edu/undergraduate/colleges/john-muir-college/index.html"}],
    "Muir 学院官网学位要求页 + UCSD catalog（2026-10-28 核对）；批准序列按学期公布，只写规则 + 链接。",
    [("writing", "Writing", "写作", [
        R("mcwp", "Muir College Writing Program", "Muir 写作", 2, ["MCWP 40", "MCWP 50"],
          "MCWP 40 + MCWP 50, letter grade, within the first two years. MCWP 41 (if assigned) does not satisfy the first part.",
          "MCWP 40 + MCWP 50，须 letter grade，两年内完成；如被要求先修 MCWP 41，该课不算第一部分。"),
        R("mcwp-transfer", "Writing for transfer students", "转学生写作", 1, ["MCWP 125"],
          "CalGETC/UC IGETC-certified transfer students take MCWP 125 instead of MCWP 40/50. Letter grade.",
          "CalGETC/UC IGETC 认证转学生修 MCWP 125 代替 MCWP 40/50，须 letter grade。")]),
     ("sequences", "General Education Sequences", "通识序列", [
        R("seq-i", "Category I: Social Sciences", "第一类：社会科学", 3, [],
          "One three-course sequence (three courses in the same department) in Social Sciences, chosen from the college-approved sequences published each quarter.",
          "社会科学方向 3 门序列（同一系 3 门），按学院每学期公布的批准序列选。"),
        R("seq-ii", "Category II: Mathematics or Natural Sciences", "第二类：数学或自然科学", 3, [],
          "One three-course sequence in Mathematics (calculus) or Natural Sciences, chosen from the college-approved sequences published each quarter.",
          "数学（微积分）或自然科学方向 3 门序列，按学院每学期公布的批准序列选。"),
        R("seq-iii", "Category III: two sequences", "第三类：另两个序列", 6, [],
          "Two three-course sequences chosen from two of: Fine Arts, Humanities, Foreign Languages, from the college-approved sequences published each quarter.",
          "另两个 3 门序列，从美术、人文、外语三区中选两个区，按学院每学期公布的批准序列选。")]),
     ("transfer", "Transfer Students", "转学生衔接", [
        R("transfer", "IGETC / reciprocity", "IGETC / 互认", None, [],
          "Transfer students who completed IGETC before transfer may waive the GE sequences above (MCWP 125 still required). Students with breadth requirements completed at another UC campus may submit a letter of reciprocity. Up to three major courses may overlap GE.",
          "转学前完成 IGETC 者可免上述 GE 序列（仍须 MCWP 125）；在另一 UC 校区完成通识/广度要求者可交 reciprocity 信函免序列；最多 3 门专业课可与 GE 重叠。")])])

# ---------------- Marshall ----------------
MAR_BIO = ["ANTH 2", "COGS 17", "BILD 1", "BILD 2", "BILD 3", "BILD 7", "BILD 10",
           "BILD 12", "BILD 18", "BILD 20", "BILD 22", "BILD 26", "BILD 28", "BILD 30",
           "BILD 32", "BILD 36", "BILD 38", "BILD 42", "BILD 46", "BILD 61"]
MAR_CHEM = ["CHEM 4", "CHEM 6A", "CHEM 6B", "CHEM 6C", "CHEM 6AH", "CHEM 6BH",
            "CHEM 6CH", "CHEM 11", "CHEM 12", "CHEM 13"]
MAR_PHYS = ["ASTR 1", "ASTR 2", "ASTR 3", "ASTR 4", "ESYS 10",
            "PHYS 1A", "PHYS 1B", "PHYS 1C", "PHYS 2A", "PHYS 2B", "PHYS 2C",
            "PHYS 4A", "PHYS 4B", "PHYS 4C", "PHYS 8", "PHYS 10", "PHYS 11", "PHYS 12",
            "SIO 1", "SIO 10", "SIO 12", "SIO 15", "SIO 16", "SIO 20", "SIO 20R",
            "SIO 30", "SIO 35", "SIO 40", "SIO 45", "SIO 50"]
MAR_MATH = ["BIEB 100", "MATH 3C", "MATH 4C", "MATH 10A", "MATH 10B", "MATH 10C",
            "MATH 11", "MATH 20A", "MATH 20B", "MATH 20C", "MATH 180A", "MATH 181A"]
MAR_STATS = ["COGS 14A", "HDS 60", "POLI 30", "POLI 30D", "PSYC 60", "SOCI 60"]
MAR_PROG = ["BILD 62", "COGS 18", "CSE 5", "CSE 5R", "CSE 6R", "CSE 8A", "CSE 11",
            "CSS 1", "LIGN 17", "MAE 5", "PHIL 10", "PHIL 12"]
MAR_HUM = ["AAS 10", "AAS 10R", "AAS 11", "AAS 11R", "AAS 14", "AAS 15",
           "ETHN 1", "ETHN 1R", "ETHN 2", "ETHN 2R", "ETHN 3", "ETHN 3R",
           "ETHN 20", "ETHN 20R", "ETHN 30",
           "HILD 7A", "HILD 7B", "HILD 7C", "HILD 10", "HILD 11", "HILD 12", "HILD 14",
           "LATI 10", "LATI 50", "LTEN 27", "LTEN 28", "LTEN 29", "LTEN 31",
           "RELI 2", "GSS 20", "GSS 21", "GSS 22", "GSS 23", "GSS 24", "GSS 25",
           "GSS 26", "GSS 27"]
MAR_ARTS = ["MUS 4", "MUS 5", "MUS 6", "MUS 7", "MUS 8", "MUS 9", "MUS 10",
            "MUS 11", "MUS 12", "MUS 13", "MUS 14", "MUS 15", "MUS 16", "MUS 17",
            "MUS 18", "MUS 19", "MUS 20", "MUS 80",
            "TDGE 1", "TDGE 5", "TDGE 10", "TDGE 11", "TDGE 12",
            "TDHT 21", "TDHT 22", "TDHT 23",
            "VIS 1", "VIS 2", "VIS 3", "VIS 20", "VIS 21A", "VIS 21B", "VIS 21C",
            "VIS 22", "VIS 84"]
COLLEGES["marshall"] = F(
    "marshall", "Thurgood Marshall College General Education", "Marshall 学院通识",
    "Thurgood Marshall College", "https://marshall.ucsd.edu/academics/general-education-requirements.html",
    [{"label": "Marshall GE requirements", "url": "https://marshall.ucsd.edu/academics/general-education-requirements.html"},
     {"label": "First-year GE", "url": "https://marshall.ucsd.edu/academics/first-year-ge.html"},
     {"label": "UCSD catalog: Marshall", "url": "https://catalog.ucsd.edu/undergraduate/colleges/thurgood-marshall-college/index.html"}],
    "Marshall 学院官网 GE 页 + 一年级 GE 页（2026-10-28 核对）；学科广度可选系随专业而定，只写规则。",
    [("doc", "Dimensions of Culture", "文化维度核心序列", [
        R("doc", "Dimensions of Culture", "文化维度", 3, ["DOC 1", "DOC 2", "DOC 3"],
          "Three-course sequence DOC 1 (4 units, fall only), DOC 2 (6 units, winter only), DOC 3 (6 units, spring only). Must be taken at UCSD, letter grade only. ELWR must be satisfied before DOC 2/3.",
          "DOC 1（4 学分，仅秋）+ DOC 2（6 学分，仅冬）+ DOC 3（6 学分，仅春），须在 UCSD 修、只接受 letter grade；修 DOC 2/3 前须先满足 UC 入学写作要求。")]),
     ("natsci", "Natural Sciences", "自然科学", [
        R("natsci", "Natural Sciences", "自然科学", 3, MAR_BIO + MAR_CHEM + MAR_PHYS,
          "3 courses: one Biology + one Chemistry + one Physics, from the approved lists. Courses available for science and nonscience majors; overlap with major sciences encouraged.",
          "自然科学 3 门：生物、化学、物理各 1 门（批准清单内）；建议选可与专业科学课重叠的课。")]),
     ("math", "Mathematics, Statistics, and Logic", "数学、统计与逻辑", [
        R("math", "Mathematics, Statistics, and Logic", "数学、统计与逻辑", 2,
          MAR_MATH + MAR_STATS + MAR_PROG,
          "2 courses, three options: (A) two Mathematics/Advanced Statistics; (B) one Mathematics/Advanced Statistics + one Introductory Statistics or Computer Programming & Logic; (C) one Introductory Statistics + one Computer Programming & Logic.",
          "2 门，三种组合：(A) 数学/高阶统计 2 门；(B) 数学/高阶统计 1 门 + 入门统计或编程与逻辑 1 门；(C) 入门统计 1 门 + 编程与逻辑 1 门。")]),
     ("humanities", "Humanities and Cultural Studies", "人文与文化研究", [
        R("humanities", "Humanities and Cultural Studies", "人文与文化研究", 2, MAR_HUM,
          "2 courses from the approved list in domestic and global cultures.",
          "人文与文化研究 2 门（批准清单：本土与全球文化方向）。")]),
     ("arts", "Fine Arts", "美术", [
        R("arts", "Fine Arts", "美术", 1, MAR_ARTS,
          "1 course from Music, Theatre & Dance, or Visual Arts. MUS 80 must be taken for 4 units to count.",
          "美术 1 门（音乐/戏剧舞蹈/视觉艺术）；MUS 80 须修满 4 学分才计入。")]),
     ("breadth", "Disciplinary Breadth", "学科广度", [
        R("breadth", "Disciplinary Breadth", "学科广度", 4, [],
          "4 four-unit courses outside the major field of study; two must be upper division; at least one upper-division course must include significant writing (from the college Significant Writing list). Eligible departments depend on the major (see the college page major selector). The four-unit public service option may fulfill one breadth course and the upper-division writing requirement. Breadth courses cannot overlap major courses.",
          "学科广度 4 门（4 学分）：须在专业领域之外，其中 2 门高年级，至少 1 门高年级须含 significant writing（学院 Significant Writing 清单内）；可选系随专业而定（见学院页按专业查询）；4 学分公共服务课可抵 1 门广度并满足高年级写作要求；广度课不得与专业课重叠。")]),
     ("transfer", "Transfer Students", "转学生衔接", [
        R("transfer", "Upper-division writing + breadth", "转学生高年级写作与广度", None, [],
          "Transfer students (all): one four-unit upper-division college-approved writing course + one four-unit upper-division disciplinary breadth course noncontiguous to the major. IGETC/UC Reciprocity transfers: same two courses (no further lower-division coursework). Without an articulation agreement, see an academic advisor.",
          "转学生：一门 4 学分高年级学院批准写作课 + 一门 4 学分高年级学科广度课（须与专业不相关）；IGETC/UC Reciprocity 转学生同此两门，不再补低年级课；无衔接协议者见学术顾问。")])])

# ---------------- Warren ----------------
COLLEGES["warren"] = F(
"warren", "Earl Warren College General Education", "Warren 学院通识",
"Earl Warren College", "https://warren.ucsd.edu/academics/general-education/index.html",
[{"label": "UCSD catalog: Warren", "url": "https://catalog.ucsd.edu/undergraduate/colleges/earl-warren-college/index.html"},
{"label": "Warren Area Studies", "url": "https://warren.ucsd.edu/academics/general-education/area-studies.html"}],
"UCSD catalog Warren 章 + 学院 Area Studies 页（2026-10-28 核对）；形式技能现行清单未在官网单页核实，只写类别 + 规则，不录旧版清单。",
[("writing", "Writing", "写作", [
R("wcwp", "Warren College Writing Program", "Warren 写作", 2, ["WCWP 10A", "WCWP 10B"],
"WCWP 10A + 10B, letter grade, at UCSD, after ELWR. May not overlap any other GE or major requirement.",
"WCWP 10A + 10B，须 letter grade、在 UCSD 修，修前须满足 UC 入学写作要求；不得与其他 GE 或专业要求重叠。"),
R("wcwp-transfer", "Writing for transfer students", "转学生写作", 1, ["WCWP 100"],
"Transfer students with TAG, IGETC, or a reciprocity agreement take WCWP 100 only (restricted to students with 90+ units). Transfers without TAG/IGETC may need WCWP 10A + 100 depending on prior writing coursework.",
"TAG/IGETC/互认转学生只修 WCWP 100（限 90 学分以上学生）；无 TAG/IGETC 者按已有写作课情况可能须修 WCWP 10A + 100。")]),
("ethics", "Ethics and Society", "伦理与社会", [
R("ethics", "Ethics and Society", "伦理与社会", 2,
["PHIL 27", "POLI 27", "PHIL 28", "POLI 28"],
"PHIL 27 or POLI 27, plus PHIL 28 or POLI 28, letter grade, at UCSD, after WCWP 10A/10B. May not overlap any other GE or major requirement.",
"PHIL 27 或 POLI 27 一门 + PHIL 28 或 POLI 28 一门，须 letter grade、在 UCSD 修，须在 WCWP 10A/10B 之后；不得与其他 GE 或专业要求重叠。")]),
("formal", "Formal Skills", "形式技能", [
R("formal", "Formal Skills", "形式技能", 2, [],
"2 courses from the college-approved list in calculus, symbolic logic, computer programming, and/or statistics. May overlap lower-division major, minor, or Programs of Concentration courses. Current course list is published by the college; no stale handbook list is recorded here.",
"形式技能 2 门（学院批准清单：微积分、符号逻辑、编程、统计方向）；可与低年级专业/辅修/专攻课重叠；现行清单以学院公布为准，此处不录旧版手册清单。")]),
("concentration", "Programs of Concentration / Area Studies", "专攻 / 区域研究（二选一）", [
R("poc", "Programs of Concentration (non-engineering)", "专攻", 12, [],
"For BA/BS in arts/sciences: two Programs of Concentration, each six courses, each noncontiguous to the major and to each other. At least two courses in each program must be taken at UCSD. A noncontiguous minor may substitute for a program of concentration.",
"两个专攻方向，各 6 门，均须与专业及彼此不相关；每个专攻至少 2 门须在 UCSD 修；不相关辅修可代替一个专攻。"),
R("area", "Area Studies (BS engineering only)", "区域研究", 6, [],
"For BS in engineering only: two Area Studies, one in humanities/fine arts and one in social sciences, each three courses (at least two upper division), noncontiguous to the major and to each other. The major plus the two Area Studies must cover all three disciplines (humanities/fine arts; math/natural sciences/engineering; social sciences). No more than two language courses per Area Study; MGT courses may not be used; language courses may not be used for a Social Sciences Area Study.",
"两个区域研究：人文/美术方向一个 + 社会科学方向一个，各 3 门（至少 2 门高年级），均须与专业及彼此不相关；专业 + 两个区域研究须覆盖全部三个学科领域（人文/美术；数学/自然科学/工程；社会科学）。每个区域研究最多 2 门语言课；MGT 课不得用；社会科学区域研究不得用语言课。")])])

# ---------------- ERC / Roosevelt ----------------
ERC_QUANT = ["MATH 3B", "MATH 3C", "MATH 4C", "MATH 10A", "MATH 10B", "MATH 10C",
"MATH 20A", "MATH 20B", "MATH 20C",
"CSE 5", "CSE 6R", "CSE 8A", "CSE 8B", "CSE 11", "CSE 29", "ECE 15",
"COGS 18", "COGS 8", "COGS 9", "BILD 62",
"LIGN 17", "PHIL 10", "PHIL 12",
"BILD 5", "COGS 14A", "COGS 14B", "ECON 5", "POLI 5", "POLI 5D",
"POLI 30", "POLI 30D", "PSYC 60", "SOCI 60", "CSE 3", "MAE 5",
"MATH 11", "HDS 60", "CSS 1", "CSS 2", "CENG 15", "NANO 15",
"ECE 85", "ENG 30", "MGT 3"]
ERC_NAT = ["BILD 1", "BILD 2", "BILD 3", "BILD 60", "CHEM 4", "CHEM 6A", "CHEM 6B",
"CHEM 6C", "PHYS 1A", "PHYS 1B", "PHYS 1C", "PHYS 2A", "PHYS 2B",
"PHYS 2C", "PHYS 2D", "PHYS 4A", "PHYS 4B", "PHYS 4C", "PHYS 4D", "PHYS 4E",
"ASTR 1", "ASTR 2", "ASTR 3", "ASTR 4", "ASTR 15", "ANTH 2", "BILD 7",
"BILD 10", "BILD 12", "BILD 18", "BILD 20", "BILD 22", "BILD 26",
"BILD 28", "BILD 30", "BILD 32", "BILD 36", "BILD 38", "BILD 42",
"BILD 44", "BILD 46", "BILD 51", "BILD 61", "CHEM 11", "CHEM 12",
"CHEM 13", "COGS 11", "COGS 17", "ENVR 30", "ESYS 10", "GLBH 20",
"SIO 1", "SIO 3", "SIO 10", "SIO 12", "SIO 15", "SIO 16", "SIO 20",
"SIO 20R", "SIO 25", "SIO 30", "SIO 35", "SIO 40", "SIO 45", "SIO 50",
"PHYS 8", "PHYS 10", "PHYS 11", "PHYS 12", "PSYC 2"]
ERC_LANG = ["LISL 1D", "LIAB 1D", "LIFR 1D", "LIGM 1D", "LIIT 1D", "LIPO 1D",
"LISP 1D", "LTFR 2A", "LTGM 2A", "LTIT 2A", "LTSP 2A", "LTGK 101",
"LTLA 100", "LTKO 2A", "LTRU 2A", "CHIN 20A", "JAPN 20A", "JWSP 104"]
ERC_ARTS = ["FILM 71", "FILM 72", "FILM 73", "LTEA 120A", "LTEA 120B", "LTEA 120C",
"LTEA 138", "COMM 50", "COMM 80"]
COLLEGES["roosevelt"] = F(
"roosevelt", "Eleanor Roosevelt College General Education", "Roosevelt 学院通识",
"Eleanor Roosevelt College", "https://roosevelt.ucsd.edu/academics/gen-ed/index.html",
[{"label": "ERC GE", "url": "https://roosevelt.ucsd.edu/academics/gen-ed/index.html"},
{"label": "UCSD catalog: ERC", "url": "https://catalog.ucsd.edu/undergraduate/colleges/eleanor-roosevelt-college/index.html"}],
"ERC 学院官网 GE 页 + UCSD catalog（2026-10-28 核对）；PHYS 5/7/9/13 已停开（2024 春最后开课），不列入。",
[("mmw", "Making of the Modern World", "现代世界形成", [
R("mmw", "Making of the Modern World", "现代世界形成", 5,
["MMW 11", "MMW 12", "MMW 13", "MMW 14", "MMW 15"],
"MMW 11-15, letter grade, at UCSD only. AP/IB/transfer coursework exempts no quarter. ELWR is a prerequisite for MMW 12/13 (it does not waive MMW 11). R versions also count.",
"MMW 11–15，须 letter grade、只在 UCSD 修；AP/IB/转学分不免任何一季；修 MMW 12/13 前须满足 UC 入学写作要求（该要求不免 MMW 11）；R 远程版亦可。")]),
("quant", "Quantitative and Formal Skills", "定量与形式技能", [
R("quant", "Quantitative and Formal Skills", "定量与形式技能", 2, ERC_QUANT,
"2 courses from Mathematics, Computer Programming, Formal Logic, Statistics, or Other approved lists. Letter or P/NP (check major overlap rules).",
"定量与形式技能 2 门（数学/编程/形式逻辑/统计/其他批准清单）；letter 或 P/NP 均可（与专业重叠时按专业规定）。")]),
("natsci", "Natural Science", "自然科学", [
R("natsci", "Natural Science", "自然科学", 2, ERC_NAT,
"2 courses from Biology, Chemistry, Physics, Astronomy, Oceanography, or Physical Geology approved lists. Lab courses alone do not fulfill the requirement. Letter or P/NP (check major overlap rules). PHYS 5/7/9/13 (last offered Spring 2024) are excluded.",
"自然科学 2 门（生物/化学/物理/天文/海洋/地质批准清单）；单实验课不算；letter 或 P/NP 均可（与专业重叠时按专业规定）。PHYS 5/7/9/13 已停开，不列入。")]),
("language", "Foreign Language", "外语", [
R("language", "Foreign Language proficiency", "外语达标", None, ERC_LANG,
"Proficiency: completion of a fourth-quarter (or third-semester) college language course, placement into fifth-quarter level, or a UCSD proficiency exam; AP/IB scores may exempt part or all. 0-4 courses depending on placement. Fourth-quarter courses listed here (LISL/LIAB/LIFR/LIGM/LIIT/LIPO/LISP 1D/DX; LTFR/LTGM/LTIT 2A; LTSP 2A/2F; LTGK 101; LTLA 100; LTKO 2A; LTRU 2A; CHIN 20A; JAPN 20A; JWSP 104; upper-division LIHL heritage courses). Language courses may NOT overlap Regional Specialization (including prerequisites to the fourth-quarter course).",
"外语达标：修到第四学期（或第三学季）水平、考入第五学期水平、或通过 UCSD 达标考试；AP/IB 可免部分或全部，按 placement 从 0 到 4 门。下表为第四学期水平课程（另有高年级 LIHL 传承语言课）。外语课（含修到第四学期水平的前置课）不得与区域专攻重叠。")]),
("arts", "Fine Arts", "美术", [
R("arts", "Fine Arts", "美术", 1, ERC_ARTS,
"1 course (at least 4 units). Any 4-unit course in Music, Theatre & Dance, or Visual Arts qualifies (1-3 unit courses do not); plus FILM 71/72/73, LTEA 120A/120B/120C/138, COMM 50/80. Letter or P/NP. May NOT overlap Regional Specialization.",
"美术 1 门（至少 4 学分）：音乐/戏剧舞蹈/视觉艺术任一 4 学分课均可（1–3 学分课不算），另加 FILM 71/72/73、LTEA 120A/120B/120C/138、COMM 50/80；letter 或 P/NP 均可；不得与区域专攻重叠。")]),
("regional", "Regional Specialization", "区域专攻", [
R("regional", "Regional Specialization", "区域专攻", 3, [],
"3 courses from the same designated region (FA21 and after: Africa; Multiculturalism in North America; Latin America; Asia/Pacific; Europe; Middle East). At least two must be upper division; one may be P/NP, the other two letter grade. Regional course lists are published per region by the college (see source link). May overlap the Upper-Division Writing requirement; may NOT overlap Fine Arts or Language.",
"区域专攻 3 门（同一指定区域；2021 秋及以后入学的区域：非洲、北美多元文化、拉丁美洲、亚太、欧洲、中东）。至少 2 门高年级；1 门可 P/NP、其余须 letter grade。各区域课单由学院分区域公布（见来源链接）。可与高年级写作重叠；不得与美术或外语重叠。")]),
("writing", "Upper-Division Writing", "高年级写作", [
R("udwriting", "Upper-Division Writing (paper requirement)", "高年级写作（论文要求）", None, [],
"Not a course: at least one upper-division course in the program must include a significant writing component (4500-5000 words, or an 18-20 page paper), from the college Approved Upper-Division Writing list, or by petition with syllabus + graded paper(s) (Option A: one 2500+ word paper; Option B: portfolio totaling 3000+ words with one 1500+ word paper). Papers must be in English, graded C- or better. Poetry, short stories, in-class exams, group projects, lab reports do not count.",
"非课程要求：至少一门高年级课须含 significant writing（4500–5000 词或 18–20 页论文），选学院批准清单内的课，或凭大纲 + 成绩论文 petition（A：单篇 2500+ 词；B：作品集共 3000+ 词、其中一篇 1500+ 词）。论文须英文、C- 及以上；诗歌、短篇、在堂考试、小组项目、实验报告不算。")]),
("transfer", "Transfer Students", "转学生衔接", [
R("transfer", "MMW for transfers", "转学生 MMW", 1, ["MMW 122"],
"IGETC/Cal-GETC/UC Reciprocity transfers: MMW 122 (letter grade, D or better). Partial IGETC: MMW 122 if IGETC Areas 1A and 1B are done, else MMW 12 (6 units); plus the 1-2 missing IGETC requirements. CalGETC without LOTE certification: MMW 122 plus one college-level LOTE course or LOTE proficiency. Transfers: 2 regional courses from the same region, both upper division (instead of 3).",
"IGETC/Cal-GETC/UC Reciprocity 转学生：MMW 122（letter grade、D 及以上）。部分 IGETC：1A 与 1B 均完成者修 MMW 122，否则修 MMW 12（6 学分），另补 1–2 门缺失 IGETC 要求；CalGETC 缺 LOTE 认证者另补 1 门大学 LOTE 课或证明 LOTE 达标。转学生区域专攻为同一区域 2 门、均为高年级（非 3 门）。")])])

# ---------------- Sixth ----------------
COLLEGES["sixth"] = F(
"sixth", "Sixth College General Education", "Sixth 学院通识",
"Sixth College", "https://sixth.ucsd.edu/academics/requirements/index.html",
[{"label": "Sixth GE requirements", "url": "https://sixth.ucsd.edu/academics/requirements/index.html"},
{"label": "UCSD catalog: Sixth", "url": "https://catalog.ucsd.edu/undergraduate/colleges/sixth-college/index.html"}],
"Sixth 学院官网 GE 要求页 + UCSD catalog（2026-10-28 核对）；低年级广度课单按学期公布，只写规则 + 链接。",
[("cat", "Culture, Art, and Technology", "文化、艺术与技术核心序列", [
R("cat", "Culture, Art, and Technology", "文化、艺术与技术", 3, ["CAT 1", "CAT 2", "CAT 3"],
"CAT 1 (4 units, fall), CAT 2 (6 units, winter), CAT 3 (6 units, spring). CAT 2/3 include intensive instruction in university-level writing.",
"CAT 1（4 学分，秋）+ CAT 2（6 学分，冬）+ CAT 3（6 学分，春）；CAT 2/3 含大学写作强化训练。")]),
("breadth", "Lower-Division Breadth", "低年级广度", [
R("it", "Information Technology Fluency", "信息技术 fluency", 1, [],
"1 computing or programming course from the college-approved breadth list (published each quarter).",
"信息技术 fluency 1 门（编程/计算方向），按学院每学期公布的广度清单选。"),
R("social", "Social Analysis", "社会分析", 2, [],
"2 social science courses from the college-approved breadth list.",
"社会分析 2 门（社会科学），按学院广度清单选。"),
R("narrative", "Narrative, Aesthetic, and Historical Reasoning", "叙事、审美与历史推理", 2, [],
"2 humanities courses from the college-approved breadth list.",
"叙事、审美与历史推理 2 门（人文），按学院广度清单选。"),
R("analytical", "Analytical and Scientific Methods", "分析与科学方法", 2, [],
"2 science courses from the college-approved breadth list (options for science and nonscience majors).",
"分析与科学方法 2 门（科学），按学院广度清单选（分理工/非理工方向）。"),
R("structured", "Structured Reasoning", "结构化推理", 1, [],
"1 math or logic course from the college-approved breadth list.",
"结构化推理 1 门（数学或逻辑），按学院广度清单选。"),
R("data", "Exploring Data", "探索数据", 1, [],
"1 statistics course from the college-approved breadth list.",
"探索数据 1 门（统计），按学院广度清单选。"),
R("artmaking", "Art Making", "艺术创作", 2, [],
"Art Making, 8 units (2 courses) in literature, music, theatre and dance, or visual arts, from the college-approved breadth list.",
"艺术创作 8 学分（2 门：文学/音乐/戏剧舞蹈/视觉艺术），按学院广度清单选。")]),
("upper", "Upper-Division Requirements", "高年级要求", [
R("experiential", "Experiential Learning", "体验学习", 1, ["CAT 90", "CAT 124"],
"1 four-unit upper-division experiential learning course (CAT 90 or CAT 124, or an approved department course, Academic Internship Program, or Study Abroad Program course). May overlap major, minor, and university requirements.",
"体验学习 1 门（4 学分高年级：CAT 90 或 CAT 124，或学院批准的系课、学术实习、留学项目课）；可与专业/辅修/校级要求重叠。"),
R("cat125", "Upper-Division Writing", "高年级写作", 1, ["CAT 125", "CAT 125R"],
"CAT 125 or CAT 125R (Public Rhetoric and Practical Communication), 4 units.",
"CAT 125 或 CAT 125R（公共修辞与实用沟通），4 学分。")])])

# ---------------- Seventh ----------------
COLLEGES["seventh"] = F(
"seventh", "Seventh College General Education", "Seventh 学院通识",
"Seventh College", "https://seventh.ucsd.edu/academics/degree-requirements.html",
[{"label": "UCSD catalog: Seventh", "url": "https://catalog.ucsd.edu/undergraduate/colleges/seventh-college/index.html"},
{"label": "Seventh FAQs", "url": "https://seventh.ucsd.edu/about/faq/index.html"}],
"UCSD catalog Seventh 章 + 学院 FAQ 页（2026-10-28 核对）；备选区课单按学期公布，只写规则 + 链接。",
[("synthesis", "Synthesis", "综合", [
R("syn", "Synthesis sequence", "综合序列", 3, ["SYN 1", "SYN 2", "SYN 100"],
"SYN 1 and SYN 2 (intensive university-level writing; R remote versions also offered) plus SYN 100 (project-based, requires junior or senior standing). Synthesis courses are exclusive to Seventh College and cannot overlap other requirements. Transfer students must complete SYN 100; SYN 150 (letter grade) is recommended preparation and fulfills the high-impact requirement.",
"SYN 1、SYN 2（大学写作强化，另有 R 远程版）+ SYN 100（项目制，须高年级 standing）；综合课为 Seventh 专属，不得与其他要求重叠。转学生须修 SYN 100；建议先修 SYN 150（letter grade 可抵高影响要求）。")]),
("alternatives", "Alternatives", "备选区", [
R("alt-arts", "Arts", "艺术", 2, [],
"2 courses from the college-approved Arts list (published each quarter). May overlap major, minor, and university requirements.",
"艺术区 2 门，按学院每学期公布的批准清单选；可与专业/辅修/校级要求重叠。"),
R("alt-humanities", "Humanities", "人文", 2, [],
"2 courses from the college-approved Humanities list.",
"人文区 2 门，按学院批准清单选；可重叠。"),
R("alt-nateng", "Natural Sciences and Engineering", "自然科学与工程", 2, [],
"2 courses from the college-approved Natural Sciences and Engineering list.",
"自然科学与工程区 2 门，按学院批准清单选；可重叠。"),
R("alt-quant", "Quantitative Reasoning", "定量推理", 2, [],
"2 courses from the college-approved Quantitative Reasoning list.",
"定量推理区 2 门，按学院批准清单选；可重叠。"),
R("alt-social", "Social Sciences", "社会科学", 2, [],
"2 courses from the college-approved Social Sciences list.",
"社会科学区 2 门，按学院批准清单选；可重叠。")]),
("highimpact", "High-Impact", "高影响", [
R("highimpact", "High-Impact", "高影响", 1, [],
"1 course (2-4 units) from approved experiential learning options: internship, mentored research, study abroad, or other significant experiential learning (including SYN 150 taken for a letter grade, SYN 198/199 after SYN 100). May overlap major, minor, and university requirements. Transfer students must complete SYN 100 + high-impact; IGETC exempts the Alternatives areas.",
"高影响 1 门（2–4 学分）：实习、导师制研究、留学或其他重要体验学习（含 letter grade 的 SYN 150、SYN 100 之后的 SYN 198/199）；可重叠。转学生须完成 SYN 100 + 高影响；IGETC 免备选区。")])])

# ---------------- section notes（与 UCSB 文件同口径：每区一句话说明） ----------------
SEC_NOTES = {
    ("revelle", "humanities"): ("Five-course humanities sequence, letter grade required.", "人文序列 5 门，须 letter grade。"),
    ("revelle", "math"): ("1 calculus course + 2 more, letter grade required.", "微积分 1 门 + 再 2 门，须 letter grade。"),
    ("revelle", "natsci"): ("5 courses: 1 Biology + 1 Chemistry + 1 Physics + 2 additional.", "5 门：生物、化学、物理各 1 门 + 另 2 门。"),
    ("revelle", "social"): ("2 courses, letter grade; department restrictions in the requirement note.", "2 门，须 letter grade；系所限课见要求备注。"),
    ("revelle", "arts"): ("1 course (2-4 units).", "1 门（2–4 学分）。"),
    ("revelle", "language"): ("Proficiency by exam or fourth-quarter level, 0-4 courses.", "达标制：考试或第四学期水平，0–4 门不等。"),
    ("revelle", "transfer"): ("Transfers: HUM 100 + full Math/Natural Science (IGETC included).", "转学生：HUM 100 + 数学/自然科学全修（IGETC 亦同）。"),
    ("muir", "writing"): ("MCWP 40 + 50 (transfers: MCWP 125), letter grade.", "MCWP 40 + 50（转学生 MCWP 125），须 letter grade。"),
    ("muir", "sequences"): ("Four 3-course sequences, 12 courses (48 units), from quarterly approved lists.", "4 个 3 门序列共 12 门（48 学分），按学期批准清单选。"),
    ("muir", "transfer"): ("IGETC waives sequences; up to 3 major courses may overlap.", "IGETC 可免序列；最多 3 门专业课重叠。"),
    ("marshall", "doc"): ("DOC 1/2/3, at UCSD only, letter grade only.", "DOC 1/2/3，须在 UCSD 修、只接受 letter grade。"),
    ("marshall", "natsci"): ("1 Biology + 1 Chemistry + 1 Physics.", "生物、化学、物理各 1 门。"),
    ("marshall", "math"): ("2 courses, three combination options.", "2 门，三种组合方式。"),
    ("marshall", "humanities"): ("2 courses in domestic and global cultures.", "本土与全球文化方向 2 门。"),
    ("marshall", "arts"): ("1 course in Music, Theatre & Dance, or Visual Arts.", "音乐/戏剧舞蹈/视觉艺术 1 门。"),
    ("marshall", "breadth"): ("4 courses outside the major; 2 upper division, 1 with writing.", "专业领域外 4 门，2 门高年级、1 门高年级含写作。"),
    ("marshall", "transfer"): ("Transfers: 1 upper-division writing + 1 upper-division breadth.", "转学生：高年级写作 1 门 + 高年级广度 1 门。"),
    ("warren", "writing"): ("WCWP 10A/10B (transfers: WCWP 100), letter grade.", "WCWP 10A/10B（转学生 WCWP 100），须 letter grade。"),
    ("warren", "ethics"): ("PHIL/POLI 27 + 28, after WCWP, letter grade.", "PHIL/POLI 27 + 28，须在 WCWP 之后、letter grade。"),
    ("warren", "formal"): ("2 courses from the college-approved list (calculus/logic/programming/statistics).", "学院批准清单 2 门（微积分/逻辑/编程/统计方向）。"),
    ("warren", "concentration"): ("Either: non-engineering concentrations (12) or engineering Area Studies (6).", "二选一：非工程专攻 12 门，工程 BS 区域研究 6 门。"),
    ("roosevelt", "mmw"): ("MMW 11-15, letter grade, at UCSD only.", "MMW 11–15，须 letter grade、只在 UCSD 修。"),
    ("roosevelt", "quant"): ("2 courses from approved lists.", "2 门（批准清单）。"),
    ("roosevelt", "natsci"): ("2 courses from approved lists; lab alone does not count.", "2 门（批准清单）；单实验课不算。"),
    ("roosevelt", "language"): ("Proficiency: fourth-quarter level or exam, 0-4 courses.", "达标制：第四学期水平或考试，0–4 门不等。"),
    ("roosevelt", "arts"): ("1 course (at least 4 units).", "1 门（至少 4 学分）。"),
    ("roosevelt", "regional"): ("3 courses in one region, at least 2 upper division.", "同一区域 3 门，至少 2 门高年级。"),
    ("roosevelt", "writing"): ("Paper requirement, not a course.", "论文要求，非课程。"),
    ("roosevelt", "transfer"): ("Transfers: MMW 122 (or MMW 12) + 2 regional courses.", "转学生：MMW 122（或 MMW 12）+ 区域 2 门。"),
    ("sixth", "cat"): ("CAT 1/2/3; CAT 2/3 include intensive writing.", "CAT 1/2/3；CAT 2/3 含写作强化。"),
    ("sixth", "breadth"): ("11 lower-division breadth courses from quarterly lists.", "低年级广度 11 门，按学期清单选。"),
    ("sixth", "upper"): ("Experiential learning + CAT 125 upper-division writing.", "体验学习 1 门 + CAT 125 高年级写作 1 门。"),
    ("seventh", "synthesis"): ("SYN 1/2 + SYN 100; transfers must take SYN 100.", "SYN 1/2 + SYN 100；转学生须 SYN 100。"),
    ("seventh", "alternatives"): ("2 courses in each of 5 areas from quarterly lists; may overlap major.", "5 区各 2 门，按学期清单选；可与专业重叠。"),
    ("seventh", "highimpact"): ("1 course (2-4 units) of experiential learning.", "1 门（2–4 学分）体验学习。"),
}
for _key, _doc in COLLEGES.items():
    for _sec in _doc["sections"]:
        _n = SEC_NOTES.get((_key, _sec["id"]))
        assert _n, ("missing section note", _key, _sec["id"])
        _sec["note"], _sec["note_zh"] = _n

# ---------------- emit + validate ----------------
def norm(code):
    return " ".join(code.replace("-", " ").split()).upper()

def main():
    total = 0
    for key, doc in COLLEGES.items():
        for base in ("data/ge", "web/data/ge"):
            p = os.path.join(BASE, base, "ucsd-%s.json" % key)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write("\n")
        n_req = sum(len(s["requirements"]) for s in doc["sections"])
        n_courses = sum(len(r["courses"]) for s in doc["sections"] for r in s["requirements"])
        # name_zh 齐全检查
        missing = [r["id"] for s in doc["sections"] for r in s["requirements"]
                   if not r.get("name_zh")]
        assert not missing, (key, missing)
        print("ucsd-%s: %d sections, %d requirements, %d course entries"
              % (key, len(doc["sections"]), n_req, n_courses))
        total += 1
    # 快照覆盖检查（仅报告，不阻断；R 版/范围写法会自然缺失）
    snap = json.load(open(os.path.join(BASE, "data/raw/ucsd-courses.json")))
    have = set()
    for c in snap:
        have.add(norm(c["code"]))
    for key, doc in COLLEGES.items():
        miss = sorted({co for s in doc["sections"] for r in s["requirements"]
                       for co in r["courses"] if norm(co) not in have})
        print("ucsd-%s snapshot-missing: %s" % (key, miss))
    print("wrote %d colleges x 2 copies" % total)

if __name__ == "__main__":
    main()
