#!/usr/bin/env python3
"""i18n updates for the 2026-10-23 cognitive-chain fixes.
- Refreshes stale copy (L4 version strings, L2 jargon-first hints).
- Adds keys used by the new UI: campus-switch confirm, plan scope
  statement + degree coverage, major progress counting / add-all
  disclosure / import banner / campus mismatch, trajectory source
  notes + unplaced-course warnings, courses campus label + go-plan.
All four locales are patched with the same key set; zh-TW/es follow
the existing dictionaries' completeness standard.
"""
import json, os

DIR = "/home/hatch/workspace/uc-course/web/data/i18n"

PATCH = {
 "zh-CN": {
  "index.campusHint": "已上线三校：UCI、UCSD、UCSB（课程数据已入库），更多校区陆续接入。",
  "index.footnote": "课程搜索 + 先修链排课 + 转学分导入。UCLA/UCB 数据管线进行中。",
  "index.gradHint": "成绩（GPA）优先，多修科研课和高阶课",
  "index.jobHint": "项目课优先，给招聘季留出面试时间",
  "index.quickPlan": "直接去排课 →",
  "index.quickTraj": "看我的轨迹 →",
  "sub.plan": "按先修顺序排课 · 自动计算",
  "plan.years": "目标毕业年限",
  "plan.maxU": "每学季（quarter）学分上限",
  "plan.qunit": "个学季（quarter）",
  "plan.draftNote": "导出的是课程代码（CCN 是每学期选课时才分配的编号，在学校官网查）。",
  "plan.scopeNote": "⚠️ 本评估只针对已选的 {n} 门课，未包含尚未选入的毕业要求（通识、专业其余课程等），不能当作整个学位的毕业结论。",
  "plan.coverageLine": "已选 {u} 学分 / 学位总学分约 180（UC 学士学位通行总量）≈ {p}%",
  "plan.genEmpty": "清单是空的，先加几门课再回来生成排课。",
  "common.campusSwitchMsg": "切换到 {campus} 后，当前校区的意向专业、选课清单、已修标记和排课草稿都会清空（不同校区的课程不能混用）。确定切换吗？",
  "common.foreignTag": "其他校区",
  "common.clearForeign": "清除旧校区课程",
  "major.progressCount": "已修/已选 {n}/{m}",
  "major.addAllNote": "其中 {n} 条多方案必修要求已按第一组（方案A）加入；想换组，点要求卡里的「选这组」即可。",
  "major.campusMismatch": "当前意向专业属于 {fc}，与当前校区 {campus} 不一致，数据无法对应。请回首页重新选择校区与专业。",
  "major.importBannerN": "🎓 已从转学分导入 {n} 门「已修」课，下方进度已更新。",
  "major.importBanner0": "🎓 转学分导入完成：所选课程之前已导入过，没有新增。",
  "traj.draftNote": "按你在排课页的课表草稿呈现（含手工调整的顺序）。",
  "traj.autoNote": "还没有课表草稿，以下按先修顺序自动排课（每学季上限 {maxu} 学分，与排课页一致）。去排课页可手工调整顺序。",
  "traj.notInDraft": "⚠️ 以下课程在选课清单里，但还没排进草稿：{list}。去排课页重新生成排课，或在草稿箱里手工排入。",
  "traj.notPlaced": "⚠️ 以下 {n} 门课在 12 个学季内排不下，未列入轨迹：{list}。去排课页提高学分上限或延长目标年限。",
  "courses.campusLabel": "校区",
  "courses.goPlan": "去排课 →",
 },
 "en": {
  "index.campusHint": "Three campuses live: UCI, UCSD, UCSB (course data loaded). More campuses on the way.",
  "index.footnote": "Course search + prerequisite-chain planning + transfer-credit import. UCLA/UCB data in the pipeline.",
  "index.gradHint": "GPA first, plus research and graduate-level courses",
  "index.jobHint": "Project courses first, keep recruiting season light for interviews",
  "index.quickPlan": "Go straight to planning →",
  "index.quickTraj": "View my trajectory →",
  "sub.plan": "Prerequisite-ordered planning · automatic",
  "plan.years": "Target years",
  "plan.maxU": "Max units per quarter",
  "plan.qunit": "quarters",
  "plan.draftNote": "Exports course codes (CCN is the per-term enrollment number assigned when classes open — look it up on the registrar site).",
  "plan.scopeNote": "⚠️ This assessment covers only the {n} course(s) you selected. Requirements you haven't added (GE, remaining major courses, etc.) are not included — it is not a verdict for the whole degree.",
  "plan.coverageLine": "Selected: {u} units / ~180 total for a UC bachelor's degree ≈ {p}%",
  "plan.genEmpty": "Your list is empty — add some courses first, then generate a plan.",
  "common.campusSwitchMsg": "Switching to {campus} clears your intended majors, course list, completed marks and plan draft for the current campus (courses can't be mixed across campuses). Continue?",
  "common.foreignTag": "other campus",
  "common.clearForeign": "Remove other-campus courses",
  "major.progressCount": "Done/picked {n}/{m}",
  "major.addAllNote": "{n} multi-option required item(s) were added using the first option group (Option A). To switch groups, use “Pick this group” in the requirement card.",
  "major.campusMismatch": "Your intended major belongs to {fc}, which doesn't match the current campus {campus}. Please go back to the home page and re-select campus and major.",
  "major.importBannerN": "🎓 Imported {n} completed course(s) from transfer credits — the progress below is updated.",
  "major.importBanner0": "🎓 Transfer import finished: the selected courses were already imported, nothing new was added.",
  "traj.draftNote": "Shown from your planning-page draft, including your manual adjustments.",
  "traj.autoNote": "No draft yet — auto-arranged by prerequisite order (cap {maxu} units per quarter, same as the planning page). Visit the planning page to adjust by hand.",
  "traj.notInDraft": "⚠️ These courses are in your list but not placed in the draft yet: {list}. Regenerate on the planning page or place them in the draft box.",
  "traj.notPlaced": "⚠️ {n} course(s) could not fit within 12 quarters and are not shown: {list}. Raise the unit cap or extend the timeline on the planning page.",
  "courses.campusLabel": "Campus",
  "courses.goPlan": "Go to planning →",
 },
 "zh-TW": {
  "index.campusHint": "已上線三校：UCI、UCSD、UCSB（課程資料已入庫），更多校區陸續接入。",
  "index.footnote": "課程搜尋 + 先修鏈排課 + 轉學分導入。UCLA/UCB 資料管線進行中。",
  "index.gradHint": "成績（GPA）優先，多修科研課和高階課",
  "index.jobHint": "專案課優先，給招聘季留出面試時間",
  "index.quickPlan": "直接去排課 →",
  "index.quickTraj": "看我的軌跡 →",
  "sub.plan": "按先修順序排課 · 自動計算",
  "plan.years": "目標畢業年限",
  "plan.maxU": "每學季（quarter）學分上限",
  "plan.qunit": "個學季（quarter）",
  "plan.draftNote": "導出的是課程代碼（CCN 是每學期選課時才分配的編號，在學校官網查）。",
  "plan.scopeNote": "⚠️ 本評估只針對已選的 {n} 門課，未包含尚未選入的畢業要求（通識、專業其餘課程等），不能當作整個學位的畢業結論。",
  "plan.coverageLine": "已選 {u} 學分 / 學位總學分約 180（UC 學士學位通行總量）≈ {p}%",
  "plan.genEmpty": "清單是空的，先加幾門課再回來生成排課。",
  "common.campusSwitchMsg": "切換到 {campus} 後，目前校區的意向專業、選課清單、已修標記和排課草稿都會清空（不同校區的課程不能混用）。確定切換嗎？",
  "common.foreignTag": "其他校區",
  "common.clearForeign": "清除舊校區課程",
  "major.progressCount": "已修/已選 {n}/{m}",
  "major.addAllNote": "其中 {n} 條多方案必修要求已按第一組（方案A）加入；想換組，點要求卡裡的「選這組」即可。",
  "major.campusMismatch": "目前意向專業屬於 {fc}，與目前校區 {campus} 不一致，資料無法對應。請回首頁重新選擇校區與專業。",
  "major.importBannerN": "🎓 已從轉學分導入 {n} 門「已修」課，下方進度已更新。",
  "major.importBanner0": "🎓 轉學分導入完成：所選課程之前已導入過，沒有新增。",
  "traj.draftNote": "按你在排課頁的課表草稿呈現（含手動調整的順序）。",
  "traj.autoNote": "還沒有課表草稿，以下按先修順序自動排課（每學季上限 {maxu} 學分，與排課頁一致）。去排課頁可手動調整順序。",
  "traj.notInDraft": "⚠️ 以下課程在選課清單裡，但還沒排進草稿：{list}。去排課頁重新生成排課，或在草稿箱裡手動排入。",
  "traj.notPlaced": "⚠️ 以下 {n} 門課在 12 個學季內排不下，未列入軌跡：{list}。去排課頁提高學分上限或延長目標年限。",
  "courses.campusLabel": "校區",
  "courses.goPlan": "去排課 →",
 },
 "es": {
  "index.campusHint": "Tres campus activos: UCI, UCSD, UCSB (datos de cursos cargados). Más campus en camino.",
  "index.footnote": "Búsqueda de cursos + horario por prerrequisitos + importación de créditos. Datos de UCLA/UCB en curso.",
  "index.gradHint": "GPA primero, más investigación y cursos de posgrado",
  "index.jobHint": "Cursos con proyecto primero y temporada de reclutamiento ligera para entrevistas",
  "index.quickPlan": "Ir directo a planificar →",
  "index.quickTraj": "Ver mi trayectoria →",
  "sub.plan": "Horario en orden de prerrequisitos · automático",
  "plan.years": "Años objetivo",
  "plan.maxU": "Límite de unidades por quarter",
  "plan.qunit": "quarters",
  "plan.draftNote": "Exporta códigos de curso (el CCN es el número de inscripción de cada trimestre; consúltalo en el sitio de registro).",
  "plan.scopeNote": "⚠️ Esta evaluación cubre solo los {n} curso(s) que seleccionaste. Los requisitos no agregados (GE, cursos restantes de la carrera, etc.) no están incluidos: no es un veredicto para todo el título.",
  "plan.coverageLine": "Seleccionado: {u} unidades / ~180 total de una licenciatura UC ≈ {p}%",
  "plan.genEmpty": "Tu lista está vacía: agrega algunos cursos primero y luego genera el horario.",
  "common.campusSwitchMsg": "Cambiar a {campus} borra tus carreras previstas, lista de cursos, marcas de completado y borrador del campus actual (los cursos no se pueden mezclar entre campus). ¿Continuar?",
  "common.foreignTag": "otro campus",
  "common.clearForeign": "Quitar cursos de otro campus",
  "major.progressCount": "Hecho/elegido {n}/{m}",
  "major.addAllNote": "{n} requisito(s) obligatorio(s) con varias opciones se agregaron usando el primer grupo (Opción A). Para cambiar de grupo, usa «Elegir este grupo» en la tarjeta del requisito.",
  "major.campusMismatch": "Tu carrera prevista pertenece a {fc}, que no coincide con el campus actual {campus}. Vuelve a la página de inicio y vuelve a elegir campus y carrera.",
  "major.importBannerN": "🎓 Se importaron {n} curso(s) completado(s) desde créditos de transferencia: el progreso de abajo está actualizado.",
  "major.importBanner0": "🎓 Importación terminada: los cursos seleccionados ya estaban importados, no hay novedades.",
  "traj.draftNote": "Se muestra desde tu borrador de la página de planificación, con tus ajustes manuales.",
  "traj.autoNote": "Aún no hay borrador: orden automático por prerrequisitos (límite de {maxu} unidades por quarter, igual que en la página de planificación). Visita la página de planificación para ajustar a mano.",
  "traj.notInDraft": "⚠️ Estos cursos están en tu lista pero aún no están en el borrador: {list}. Regenera en la página de planificación o colócalos en el borrador.",
  "traj.notPlaced": "⚠️ {n} curso(s) no cupieron en 12 quarters y no se muestran: {list}. Sube el límite de unidades o extiende el plazo en la página de planificación.",
  "courses.campusLabel": "Campus",
  "courses.goPlan": "Ir a planificar →",
 },
}

def set_key(d, dotted, val):
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = val

def flat(d, prefix=""):
    out = set()
    for k, v in d.items():
        kk = prefix + k
        if isinstance(v, dict):
            out |= flat(v, kk + ".")
        else:
            out.add(kk)
    return out

def main():
    ref = None
    for loc, patch in PATCH.items():
        p = os.path.join(DIR, loc + ".json")
        d = json.load(open(p, encoding="utf-8"))
        for k, v in patch.items():
            set_key(d, k, v)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")
        keys = flat(d)
        if ref is None:
            ref = keys
        else:
            assert keys == ref, f"{loc} key set differs: missing {ref-keys} extra {keys-ref}"
        print(loc, "keys:", len(keys))
    print("all four locales key-aligned")

if __name__ == "__main__":
    main()
