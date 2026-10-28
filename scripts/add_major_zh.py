#!/usr/bin/env python3
"""Add Chinese layer (name_zh / note_zh) to major requirement data.
Translations cover labels & notes only — course codes and factual
fields (name / note originals) are left untouched. Long catalog
regulation notes get a faithful Chinese summary in note_zh; the UI
shows the English original alongside in that case.
Applies to both copies: web/data/majors/ and data/majors/.
"""
import json, os, sys

BASE = "/home/hatch/workspace/uc-course"
DIRS = [f"{BASE}/web/data/majors", f"{BASE}/data/majors"]

# (file, req id) -> (name_zh, note_zh or None)
ZH = {
 # ---------------- UCI Biology ----------------
 ("uci-biology.json", "A"): ("A. 专业核心课（选 3 门）", None),
 ("uci-biology.json", "B"): ("B. 高年级实验课（选 2 门）",
   "其中一门实验课可用「生物科学卓越研究」（Excellence in Research in Biological Sciences）替代"),
 ("uci-biology.json", "C"): ("C. 高年级生物选修（选 4 门 4 学分的课）",
   "范围：BIO SCI D103-D190、E106-E190、M114-M190、N110-N190，以及列出的 CHEM/PHRMSCI 课程"),
 # ---------------- UCI Computer Science ----------------
 ("uci-computer-science.json", "lower-A"): ("低年级 A：编程入门系列（选一个系列）",
   "系列一：I&C SCI 31-32-33；或系列二：I&C SCI H32-33（加速班）"),
 ("uci-computer-science.json", "lower-B"): ("低年级 B：全部必修", "I&C SCI 6N 或 MATH 3A（二选一）"),
 ("uci-computer-science.json", "upper-A"): ("高年级 A：核心课（2 门）", None),
 ("uci-computer-science.json", "upper-B"): ("高年级 B：灵活核心（4 门，至少覆盖 4 个不同方向）",
   "方向：FA1 视觉/图形；FA2 信息管理；FA3 网络/安全；FA4 系统；FA5 体系结构；FA6 算法；FA7 人工智能/机器学习"),
 ("uci-computer-science.json", "upper-C"): ("高年级 C：选修（9 门）", "含 COMPSCI 103-189 号段课程"),
 ("uci-computer-science.json", "upper-D"): ("高年级 D：项目课（2 门）", None),
 # ---------------- UCI Economics ----------------
 ("uci-economics.json", "A"): ("A. 低年级必修", None),
 ("uci-economics.json", "B"): ("B. 高年级核心", None),
 ("uci-economics.json", "C"): ("C. 另选 6 门 ECON 课（其中一门可为低年级）",
   "开放池：任意 ECON 课程；另受 D 项上限约束"),
 ("uci-economics.json", "D"): ("D. 上限：ECON 190-199 中最多 3 门 4 学分课计入专业",
   "这是上限规定，不是要求修满 3 门"),
 # ---------------- UCI Electrical Engineering ----------------
 ("uci-electrical-engineering.json", "math-sci"): ("数学与基础科学", "ENGR 1A 或 CHEM 1A（二选一）"),
 ("uci-electrical-engineering.json", "eng-topics"): ("工程专业课（每组都要完成）", None),
 ("uci-electrical-engineering.json", "tech-electives"): ("技术选修（至少 3 门、≥10 学分）",
   "任意未被列为专业必修的 EECS 课；至少一门在本方向之外；EECS 199 的 4 学分 = 1 门选修"),
 ("uci-electrical-engineering.json", "prof-topics"): ("工程职业素养课", None),
 ("uci-electrical-engineering.json", "spec-electronic-circuit-design"): ("方向：电子电路设计（先修 + 选 4 门）",
   "先修：EECS 170D、EECS 170E；再从池中选 4 门"),
 ("uci-electrical-engineering.json", "spec-semiconductors-and-optoelectronics"): ("方向：半导体与光电子（先修 + 选 3 门）",
   "先修：EECS 174、EECS 188、PHYSICS 52A；再选 3 门"),
 ("uci-electrical-engineering.json", "spec-rf-antennas-and-microwaves"): ("方向：射频、天线与微波（先修 + 选 3 门）",
   "先修：EECS 144、EECS 180B、EECS 182；再选 3 门"),
 ("uci-electrical-engineering.json", "spec-digital-signal-processing"): ("方向：数字信号处理（先修 + 选 3 门）",
   "先修：EECS 22、EECS 152A、EECS 152B；再选 3 门"),
 ("uci-electrical-engineering.json", "spec-communications"): ("方向：通信（先修 + 选 4 门）",
   "先修：EECS 141A、EECS 141B；再选 4 门"),
 # ---------------- UCI Mathematics ----------------
 ("uci-mathematics.json", "core-A"): ("A. 核心：微积分、线性代数与分析基础",
   "MATH 2A-2B 单变量微积分 I-II；MATH 2D 多变量微积分 I；MATH 3A 线性代数；MATH 3D 微分方程；MATH 9 数值分析编程；MATH 13 抽象数学；MATH 120A 抽象代数：群；MATH 121A 线性代数 I；MATH 130A 概率 I；MATH 140A-140B 初等分析 I-II"),
 ("uci-mathematics.json", "core-B"): ("B. 核心：一个三学季的科学系列",
   "三选一：CHEM 1A-1B-1C 普通化学；PHYSICS 7C-7D-7E 经典物理；或 STATS 7 + MATH 10 + PHYSICS 7C"),
 ("uci-mathematics.json", "pure-lower"): ("纯数学方向 — 低年级",
   "纯数学专业要求 = 全部数学专业共同核心 + 以下各项"),
 ("uci-mathematics.json", "pure-upper-A"): ("纯数学方向 — 高年级核心",
   "MATH 120B 抽象代数：环与域；MATH 121B 线性代数 II；MATH 147 复分析"),
 ("uci-mathematics.json", "pure-upper-B"): ("纯数学方向 — 另选 5 门 MATH 选修",
   "另选 5 门 100–189 号段的 4 学分 MATH 讲座课。未在此编码的变体：应用与计算数学 B.S. 是独立专业页；教育方向需申请 + 面试，有自己的课程表。"),
 # ---------------- UCI Psychology ----------------
 ("uci-psychology.json", "A"): ("A. 心理学基础（8 学分）", None),
 ("uci-psychology.json", "B"): ("B. 四门高年级核心课（16 学分）", None),
 ("uci-psychology.json", "C1"): ("C-1. 从三个不同组各选一门（发展 / 健康 / 临床前 / 社会-人格）",
   "分组：G1 发展（PSY 110D-134D, 138H, 152C, 153C, 155C）；G2 健康（PSY 118D, 136H-149H, 159C, 160C, 163C, 164C, 167C, 184S）；G3 临床前（PSY 139H, 141H, 143H, 150C-169C, 173S, 178S）；G4 社会/人格/环境（PSY 116D, 121D, 126D, 127D, 170S-189S）"),
 ("uci-psychology.json", "C2"): ("C-2. 另选三门高年级课",
   "来自 C-1 的专业领域，或 PSY 100、PSY 190A-193Z、PSY 196、SOCECOL 190/H190A/H190W"),
 # ---------------- UCSB Biology ----------------
 ("ucsb-biology.json", "chemistry-requirement"): ("化学要求",
   "转入完整专业（full major）有门槛：须满足专业预备（Pre-Biology）课程与 GPA 要求（以 General Catalog 与 Pre-Biological Sciences Major Sheet 为准）；至少完成 11 门指定预备课且 UC GPA ≥ 2.0。一门课只能满足一条要求；连字符表示整组系列须一起修完。"),
 ("ucsb-biology.json", "lower-division-biology"): ("低年级生物", None),
 ("ucsb-biology.json", "organic-chemistry-and-labs"): ("有机化学与实验", None),
 ("ucsb-biology.json", "mathematics"): ("数学", None),
 ("ucsb-biology.json", "statistics"): ("统计", "以下完成 1 门即可"),
 ("ucsb-biology.json", "physics"): ("物理", None),
 ("ucsb-biology.json", "a-genetics"): ("A. 遗传学",
   "同一门课出现在多个领域时只能计入一个领域；B7 的课可同时满足 B1-B6 中列出的领域。高年级共需 48 学分，按 A、B1-B7 分布；每组按注明的组数完成。"),
 ("ucsb-biology.json", "b1-physiology"): ("B1. 生理学", "以下每组完成 1 门或 1 个系列"),
 ("ucsb-biology.json", "b2-developmental-and-cell-biology"): ("B2. 发育与细胞生物学", "以下完成 1 门"),
 ("ucsb-biology.json", "b3-biochemistry-and-molecular-biology"): ("B3. 生物化学与分子生物学", "以下完成 1 门"),
 ("ucsb-biology.json", "b4-ecology"): ("B4. 生态学", "以下完成 1 门"),
 ("ucsb-biology.json", "b5-evolution"): ("B5. 进化", "以下完成 1 门"),
 ("ucsb-biology.json", "b6-biodiversity-and-systematics"): ("B6. 生物多样性与系统学", "以下完成 1 门"),
 ("ucsb-biology.json", "b7-laboratory"): ("B7. 实验",
   "本领域的课若同时列在 B1-B6，可同时满足原领域。专业课（预备与高年级）原则上不许 P/NP 计分（不提供字母成绩的课最多 8 学分除外）；替换课程须经系主任与院长批准（petition）；高年级专业课及全部专业课 UC 平均 ≥ 2.0；双专业经双方系主任批准，最多 8 学分可同时计入两个专业。"),
 # ---------------- UCSB Computer Science ----------------
 ("ucsb-computer-science.json", "computer-science-courses"): ("计算机科学课",
   "计入专业要求的课程（系内或系外）必须以字母成绩（letter grade）修读"),
 ("ucsb-computer-science.json", "mathematics-courses"): ("数学课", None),
 ("ucsb-computer-science.json", "statistics-and-applied-probability-course"): ("统计与应用概率课", None),
 ("ucsb-computer-science.json", "required-courses"): ("必修课", None),
 ("ucsb-computer-science.json", "major-field-electives"): ("专业选修",
   "从下列清单选 14 门（至少 7 门须为 CMPSC）；CMPSC 192 与 196 合计最多计 4 学分，且仅限 GPA ≥ 3.0 的学生；CMPSC 196B 另有资格要求，详询系顾问。"),
 ("ucsb-computer-science.json", "science-electives-list-a"): ("科学选修 — 清单 A",
   "至少 8 学分；批准课程清单见计算机科学系"),
 ("ucsb-computer-science.json", "science-electives-list-b"): ("科学选修 — 清单 B",
   "至少 12 学分；批准课程清单见计算机科学系"),
 # ---------------- UCSB Economics ----------------
 ("ucsb-economics.json", "pre-major"): ("专业预备（Pre-Major）",
   "准入门槛：Economics 1、2、10A 三门 UC GPA ≥ 2.85，且预备课成绩不得低于 C；另须完成 Economics 5 或 PSTAT 120A、Math 2A-B 或 3A-B 或 34A-B（成绩 ≥ C，这几门不计入预备 GPA 但计入专业总 GPA）。Econ 10A 必须在 UCSB 修。"),
 ("ucsb-economics.json", "preparation-for-the-major"): ("专业准备课", "以下完成一组；Econ 5 必须在 UCSB 修"),
 ("ucsb-economics.json", "preparation-for-the-major-2"): ("专业准备课", "以下完成一组"),
 ("ucsb-economics.json", "a"): ("A. 高年级核心", "高年级经济学共需 40 学分"),
 ("ucsb-economics.json", "b"): ("B. 高年级核心", None),
 ("ucsb-economics.json", "c"): ("C. 高年级核心", None),
 ("ucsb-economics.json", "d"): ("D. 高年级选修", "以下完成 6 门：ECON 191AA-ZZ 等高年级经济学选修"),
 ("ucsb-economics.json", "e"): ("E. 高年级选修（另选 1 门）",
   "以下完成 1 门。E 区所列部分课程要求先修 Econ 3A-B；未修 3A-B 的学生改为从 D 区共选 7 门选修。Economics 199 最多 4 学分计入专业，199RA 不计入。专业课原则上不许 P/NP；替换须经 petition 批准；高年级专业课及全部专业课 UC 平均 ≥ 2.0；双专业最多 8 学分可双计。"),
 # ---------------- UCSB Electrical Engineering ----------------
 ("ucsb-electrical-engineering.json", "preparation"): ("专业准备课", None),
 ("ucsb-electrical-engineering.json", "required-upper-division"): ("高年级必修",
   "计入专业要求的课程（系内或系外）必须以字母成绩修读。ECE 153A 与 153B 都修时，一门可作系选修、另一门作必修。"),
 ("ucsb-electrical-engineering.json", "approved-departmental-electives"): ("批准的系选修",
   "至少 36 学分。含 ECE 194AA-ZZ（不含 194R）、ECE 192 或 196（合计最多 4 学分）、TMP 120、122（最多 1 门）；选修组合须经导师（faculty adviser）批准，且须包含所选方向的一个深度系列（或经导师批准的至少 4 门深度系列）。各方向课程清单见 ECE 系学生办公室。"),
 # ---------------- UCSB Mathematics ----------------
 ("ucsb-mathematics.json", "calculus"): ("微积分",
   "转入完整专业门槛：预备数学课 UC GPA ≥ 2.5，且每门成绩 ≥ C；准备课不计入预备 GPA，但计入专业总 GPA。进入预备（pre-major）不保证能转入完整专业；完成准备期间学生身份为 pre-major。"),
 ("ucsb-mathematics.json", "linear-algebra-and-differential-equations"): ("线性代数与微分方程",
   "Math 4A、4B、6A、6B 中任一门须达到 B 或以上，才能修 Math 8"),
 ("ucsb-mathematics.json", "vector-calculus"): ("向量微积分",
   "Math 4A、4B、6A、6B 中任一门须达到 B 或以上，才能修 Math 8"),
 ("ucsb-mathematics.json", "higher-mathematics"): ("高等数学", None),
 ("ucsb-mathematics.json", "computer-programming"): ("计算机编程", "以下完成 1 门"),
 ("ucsb-mathematics.json", "physics"): ("物理", "以下完成 1 门"),
 ("ucsb-mathematics.json", "upper-division-major"): ("高年级专业课",
   "经导师批准，52 个高年级学分中最多 4 学分可为连贯数学项目内的非数学课。以下课程不计入专业：Math 100A-B、193、195A-B；PSTAT 109、188、190、193。"),
 ("ucsb-mathematics.json", "upper-division-major-2"): ("高年级专业课", "以下完成一组"),
 ("ucsb-mathematics.json", "upper-division-major-3"): ("高年级专业课", "以下完成一组"),
 ("ucsb-mathematics.json", "upper-division-electives"): ("高年级选修",
   "至少 12 学分；课程池以官方项目页为准。专业课原则上不许 P/NP；替换须经 petition 批准；高年级专业课及全部专业课 UC 平均 ≥ 2.0；双专业最多 8 学分可双计。"),
 # ---------------- UCSB Psychology ----------------
 ("ucsb-psychology.json", "area-i-courses"): ("领域 I 课程",
   "准入门槛：领域 I 的 UC GPA ≥ 2.7、领域 II ≥ 2.0；全部课程须以字母成绩修读；领域 I、II 中低于 C- 的课不接受，且 C- 最多只能有一门。须向系办公室（1814 Psychology East）提交「Petition to Change Major」申请进入预备与正式专业。修 PSY 10A 前须先完成 PSY 1、MATH 34A（或 2A 或 3A）、PSTAT 5ALS 或等效课、CHEM 1A-B（或 2A-B）；PSY 10A 是 PSY 10B 的先修。"),
 ("ucsb-psychology.json", "area-ii-courses"): ("领域 II 课程", "注：CHEM 1C 是 MCDB 1A 的先修，可与 MCDB 1A 同时修"),
 ("ucsb-psychology.json", "area-iii-courses"): ("领域 III 课程",
   "以下完成 4 门。注：下列课程不是专业准入要求，但完成专业必须修"),
 ("ucsb-psychology.json", "area-a"): ("领域 A", None),
 ("ucsb-psychology.json", "area-b"): ("领域 B", "至少 8 学分；课程池以官方项目页为准"),
 ("ucsb-psychology.json", "area-c"): ("领域 C", "以下完成 1 门；至少包含一门下列实验课"),
 ("ucsb-psychology.json", "area-d"): ("领域 D",
   "从下列组合另选 16 学分。PSY 199P 最多 8 学分可按 P/NP 计入专业，其余专业课（预备/高年级，含他系计入的课）必须以字母成绩修读；替换须经 petition 批准；高年级及全部专业课 UC 平均 ≥ 2.0；双专业最多 8 学分可双计。"),
 # ---------------- UCSB Environmental Science ----------------
 ("ucsb-environmental-science.json", "lower-division-environmental-studies"): ("低年级环境研究", None),
 ("ucsb-environmental-science.json", "economics"): ("经济学（四选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "earth-science"): ("地球科学（五选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "calculus"): ("微积分（两组选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "statistics"): ("统计（三选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "chemistry"): ("化学", None),
 ("ucsb-environmental-science.json", "biology"): ("生物", None),
 ("ucsb-environmental-science.json", "physics"): ("物理（两组选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "preparation-for-the-major"): ("专业预备（七选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "preparation-for-the-major-2"): ("专业预备（十六选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "1"): ("A-1：ENV S 190 研讨课",
   "全部课程（含交叉开设课）只能计入专业的一个方向；A、B 两区高年级共需 49–50 学分，另加 C 区 16 学分校外集中方向"),
 ("ucsb-environmental-science.json", "2"): ("A-2（七选一）", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "3-1-ecosystems-and-society"): ("A-3.1 生态系统与社会", "三个群组各选 1 门；以下完成 1 门"),
 ("ucsb-environmental-science.json", "3-2-energy-water-and-climate"): ("A-3.2 能源、水与气候", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "3-3-built-environment"): ("A-3.3 建筑环境", "以下完成 1 门"),
 ("ucsb-environmental-science.json", "b-1"): ("B-1 专业选修（32 学分）",
   "A 区未用过的 32 学分高年级环境研究选修，其中至少 20 学分来自 B-1；交叉开设课可通过其他系修读"),
 ("ucsb-environmental-science.json", "b-2"): ("B-2（四选一）",
   "以下完成 1 门；ENV S 192、194、199、199RA 合计最多 8 学分、每门最多 4 学分。专业课先修以 General Catalog 为准；ENV S 190 必须 P/NP，ENV S 192 最多 4 学分可 P/NP，其余专业课须字母成绩；替换须 petition 批准；高年级及全部专业课 UC 平均 ≥ 2.0；双专业最多 8 学分可双计。"),
 ("ucsb-environmental-science.json", "c-outside-concentration"): ("C. 校外集中方向（16 学分）",
   "三选一：方案一，16 学分高年级课选自以下系之一（课程表以官方项目页的课程集为准）；方案二，16 学分选自方案一所列系、形成连贯方向，学习计划须经系主任 petition 批准、开始前须咨询系顾问；方案三，在方案一所列系之一或心理与脑科学 B.S. 双专业，16 学分可同时计入两个专业。"),
 # ---------------- UCSD Biology ----------------
 ("ucsd-biology.json", "lower-bio"): ("低年级生物", None),
 ("ucsd-biology.json", "lower-chem"): ("普通化学", None),
 ("ucsd-biology.json", "lower-ochem"): ("有机化学", None),
 ("ucsd-biology.json", "lower-math"): ("数学", "MATH 10A-B + 11，或 MATH 20A-B + 11"),
 ("ucsd-biology.json", "lower-phys"): ("物理", "PHYS 1A/1AL+1B/1BL+1C/1CL，或 PHYS 2A-B-C +（2BL 或 2CL 或 2DL）"),
 ("ucsd-biology.json", "upper-biochem"): ("生物化学（选一门）", None),
 ("ucsd-biology.json", "upper-gen"): ("遗传学", None),
 ("ucsd-biology.json", "upper-bieb"): ("一门 4 学分 BIEB 课", "推荐 BIEB 102 或 BIEB 150"),
 ("ucsd-biology.json", "upper-molbio"): ("分子生物学", None),
 ("ucsd-biology.json", "upper-physio"): ("人体生理学 I", None),
 ("ucsd-biology.json", "upper-lab"): ("高年级实验（方案 A：一门 6 学分实验；方案 B：两门 4+ 学分实验）",
   "方案 A：一门 6 学分高年级实验；方案 B：生物科学学院两门高年级实验课（每门 4+ 学分）；可计一门 BISP 196/197/199（4+ 学分）"),
 ("ucsd-biology.json", "upper-elect"): ("专业选修（20-22 学分）",
   "须为生物科学学院的高年级生物课；院外课程须事先批准并提交 petition"),
 # ---------------- UCSD Computer Science ----------------
 ("ucsd-computer-science.json", "lower-cs"): ("低年级 CS 核心",
   "CSE 8B 或 CSE 11；CSE 15L 或 CSE 29；CSE 20 或 MATH 15A/31CH/109；CSE 21 或 MATH 154/184"),
 # ---------------- UCSD Mathematics-Computer Science ----------------
 ("ucsd-mathematics-computer-science.json", "ld-calc"): ("低年级：线性代数与微积分系列（二选一）", None),
 ("ucsd-mathematics-computer-science.json", "ld-cse11"): ("低年级：CSE 11 加速编程入门", None),
 ("ucsd-mathematics-computer-science.json", "ld-tools"): ("低年级：软件工具实验（二选一）", None),
 ("ucsd-mathematics-computer-science.json", "ld-cse12"): ("低年级：CSE 12 数据结构与面向对象设计", None),
 ("ucsd-mathematics-computer-science.json", "ud-math109"): ("高年级：数学推理（MATH 109）",
   "修完 MATH 31AH-BH-CH 的学生可用一门 4 学分高年级数学选修课替代 MATH 109。"),
 ("ucsd-mathematics-computer-science.json", "ud-algebra"): ("高年级：现代应用代数或现代代数（选一序列）", None),
 ("ucsd-mathematics-computer-science.json", "ud-cse105"): ("高年级：可计算性理论（CSE 105）",
   "修 CSE 105 之前须先修 CSE 21、MATH 100A、MATH 103A、MATH 184 或 MATH 184A 其中之一。"),
 ("ucsd-mathematics-computer-science.json", "ud-cse100"): ("高年级：数据结构实现（CSE 100）",
   "修 CSE 100 之前须先修 CSE 21、MATH 154、MATH 184 或 MATH 184A 其中之一。"),
 ("ucsd-mathematics-computer-science.json", "ud-prob"): ("高年级：概率论入门（二选一）",
   "MATH 183 不是 MATH 181A 的先修课；MATH 180A/183 与 ECON 120A 存在学分重复。"),
 ("ucsd-mathematics-computer-science.json", "ud-discrete"): ("高年级：离散数学或组合数学（四选一）", None),
 ("ucsd-mathematics-computer-science.json", "ud-cse101"): ("高年级：算法设计与分析（CSE 101）", None),
 ("ucsd-mathematics-computer-science.json", "ud-app-elect"): ("高年级：应用数学选修（8 学分）",
   "从所列课程中修满 8 学分；单门课不能同时满足两条专业要求。"),
 ("ucsd-mathematics-computer-science.json", "ud-comp-elect"): ("高年级：计算选修（8 学分）",
   "从所列课程中修满 8 学分；单门课不能同时满足两条专业要求；想选计算机体系结构方向（CSE 140-140L、141-141L、142）建议先修 CSE 30。"),
 ("ucsd-mathematics-computer-science.json", "ud-gen-elect"): ("高年级：数学-计算机综合选修（8 学分）",
   "从应用数学/计算选修清单或所列课程中另修 8 学分；单门课不能同时满足两条专业要求。"),
 ("ucsd-computer-science.json", "lower-cs-extra"): ("低年级 CS：从清单至少修 4 学分",
   "至少 4 学分；未在别处使用的任意 CSE 高年级课也可计入"),
 ("ucsd-computer-science.json", "lower-math"): ("低年级数学（16 学分）", "MATH 20C 或 MATH 31BH；MATH 18 或 MATH 31AH"),
 ("ucsd-computer-science.json", "lower-sci"): ("通识科学（一门，4 学分）", None),
 ("ucsd-computer-science.json", "lower-prob"): ("概率与统计（4 学分）", "选一门"),
 ("ucsd-computer-science.json", "upper-core"): ("高年级核心（12 学分）", "数据结构/编程；算法；软件工程"),
 ("ucsd-computer-science.json", "upper-elect"): ("高年级选修（60 学分，含广度要求）",
   "共 60 学分：Systems 类 ≥12、Theory/Abstraction 类 ≥12、Applications 类 ≥12，另加 24 学分。门数按每门 4 学分估算为 15 门；标签清单见官方目录"),
 # ---------------- UCSD Economics ----------------
 ("ucsd-economics.json", "lower-math"): ("低年级数学", "必须 MATH 10A-B-C；推荐 MATH 20A-B-C（读研准备需要）"),
 ("ucsd-economics.json", "lower-econ"): ("低年级经济学", None),
 ("ucsd-economics.json", "upper-core"): ("高年级核心", "100A-B 微观、110A-B 宏观、120A-B-C 计量经济学"),
 ("ucsd-economics.json", "upper-elect"): ("高年级选修（5 门）",
   "任意 4 学分 ECON 100-199；核心课不能重复计入；ECON 100C 可作选修计入"),
 # ---------------- UCSD Electrical Engineering ----------------
 ("ucsd-electrical-engineering.json", "lower-ee"): ("低年级 EE（24 学分）", None),
 ("ucsd-electrical-engineering.json", "lower-prog"): ("编程",
   "ECE 15 所有方向必修；通信/系统/机器学习/信号方向另加 ECE 17 或 18"),
 ("ucsd-electrical-engineering.json", "lower-math"): ("数学（24 学分）", None),
 ("ucsd-electrical-engineering.json", "lower-phys"): ("物理", "PHYS 2A-B-C 或 4A-B-C（部分方向：2A-B-C-D 或 4A-B-C-D-E）"),
 ("ucsd-electrical-engineering.json", "design"): ("设计课（选一门，成绩 ≥ C-）", "毕业必须；须提交书面设计项目"),
 ("ucsd-electrical-engineering.json", "prof-elect"): ("职业选修（两门高年级课）", "开放池：任意两门高年级课"),
 ("ucsd-electrical-engineering.json", "depth-communication-systems"): ("深度方向：通信系统（须选一个方向）",
   "广度课全修 + 6 门深度课全修"),
 ("ucsd-electrical-engineering.json", "depth-computer-system-design"): ("深度方向：计算机系统设计（须选一个方向）",
   "广度课全修；深度清单任选 5 门（ECE 111 必须作为深度课、技术选修或设计课修读）"),
 ("ucsd-electrical-engineering.json", "depth-electronic-circuits-and-systems"): ("深度方向：电子电路与系统（须选一个方向）",
   "广度课全修 + 3 门深度课全修"),
 ("ucsd-electrical-engineering.json", "depth-electronic-devices-and-materials"): ("深度方向：电子器件与材料（须选一个方向）",
   "广度课全修 + 4 门深度课全修"),
 ("ucsd-electrical-engineering.json", "depth-machine-learning-and-controls"): ("深度方向：机器学习与控制（须选一个方向）",
   "广度课全修；深度：171A+174+175A，再加 171B/172A/175B 之一"),
 ("ucsd-electrical-engineering.json", "depth-photonics"): ("深度方向：光子学（须选一个方向）",
   "广度课全修；深度：181+182+183，再加 184 或 185"),
 ("ucsd-electrical-engineering.json", "depth-power-engineering"): ("深度方向：电力工程（须选一个方向）",
   "广度课全修；深度：121A-B+125A+128A，再加 125B 或 128B"),
 ("ucsd-electrical-engineering.json", "depth-signal-and-image-processing"): ("深度方向：信号与图像处理（须选一个方向）",
   "广度课全修 + 4 门深度课全修"),
 # ---------------- UCSD Mathematics ----------------
 ("ucsd-mathematics.json", "lower-seq"): ("低年级：一条微积分/线性代数系列",
   "二选一：MATH 18 + MATH 20A-B-C-D-E（线性代数与微积分），或 MATH 31AH-BH-CH + MATH 20D（荣誉微积分）。MATH 20D 与 20E 不必按顺序修；建议尽早修 MATH 18。"),
 ("ucsd-mathematics.json", "upper-reasoning"): ("数学推理",
   "完成 MATH 31AH-BH-CH 的学生可用一门 4 学分高年级数学选修替代 MATH 109"),
 ("ucsd-mathematics.json", "upper-analysis"): ("分析系列（二选一）",
   "二选一：MATH 140A-B 实分析基础，或 MATH 142A-B + MATH 120A 分析导论。读研推荐 MATH 140A-B-C。"),
 ("ucsd-mathematics.json", "upper-algebra"): ("代数系列（二选一）",
   "二选一：MATH 100A-B 抽象代数，或 MATH 103A-B + MATH 102 现代应用代数。读研推荐 MATH 100A-B-C。"),
 ("ucsd-mathematics.json", "upper-electives"): ("高年级选修（凑满 13 门 / 52 学分）",
   "高年级共需 13 门四学分课（52 学分）。选修可选任意 MATH 100–194（195/196/197/198/199/199H 不计）。通常需选 6–8 门（本数据按上限 8 门编码，实际剩余门数按已完成必修计算）。全部专业课须 ≥ C-，高年级专业课 GPA ≥ 2.0。"),
 # ---------------- UCSD Psychology ----------------
 ("ucsd-psychology.json", "lower-natsci"): ("低年级：两门自然科学课",
   "BILD 12 / COGS 17 / PSYC 2 只能计一门；CHEM 4 / CHEM 11 只能计一门"),
 ("ucsd-psychology.json", "lower-formal"): ("低年级：一门形式技能课", None),
 ("ucsd-psychology.json", "lower-prog"): ("低年级：一门编程课", "走科研方向推荐 COGS 18 / CSS 1 / ECE 15 / MAE 8"),
 ("ucsd-psychology.json", "lower-methods"): ("低年级：一门研究方法课", "推荐 PSYC 70"),
 ("ucsd-psychology.json", "lower-stats"): ("低年级：一门统计课", "推荐 PSYC 60；统计课必须以字母成绩修读"),
 ("ucsd-psychology.json", "upper-core"): ("高年级：四门心理学核心课", None),
 ("ucsd-psychology.json", "upper-elect"): ("高年级：八门心理学选修课",
   "范围 PSYC 100-111、122-193；PSYC 195P（4 学分）与 AIP 197 须事先批准；PHIL 137/149 最多计一门"),
}

def main():
    missing = []
    total_reqs = 0
    for d in DIRS:
        for fn in sorted(os.listdir(d)):
            if fn == "index.json" or not fn.endswith(".json"):
                continue
            p = os.path.join(d, fn)
            data = json.load(open(p, encoding="utf-8"))
            for r in data["requirements"]:
                total_reqs += 1
                key = (fn, r["id"])
                if key not in ZH:
                    missing.append(key)
                    continue
                name_zh, note_zh = ZH[key]
                r["name_zh"] = name_zh
                if r.get("note"):
                    if note_zh is None:
                        missing.append((fn, r["id"], "note has no zh"))
                    else:
                        r["note_zh"] = note_zh
                elif note_zh is not None:
                    missing.append((fn, r["id"], "zh note but no source note"))
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
    print("requirements processed per dir-set:", total_reqs // len(DIRS))
    if missing:
        print("MISSING/ISSUES:", len(missing))
        for m in missing:
            print("  ", m)
        sys.exit(1)
    print("all requirements have name_zh; all notes have note_zh")

if __name__ == "__main__":
    main()
