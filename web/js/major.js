/* UC SmartPick 专业模块：毕业要求索引 + 下游课程索引 */
"use strict";

var REQ_TYPE_BADGE = { required: "major.reqRequired", elective: "major.reqElective", prereq: "major.reqPrereq" };

function fetchMajor(campus, file) {
  return fetch("data/majors/" + file).then(function (r) { return r.json(); });
}

/* 课号 -> [requirement] 反向索引（归一化后） */
function buildReqIndex(majorData) {
  var idx = {};
  (majorData.requirements || []).forEach(function (req) {
    (req.courses || []).forEach(function (c) {
      var k = normCode(c);
      if (!idx[k]) idx[k] = [];
      idx[k].push(req);
    });
  });
  return idx;
}

/* 下游索引：某课是哪些课的前置（用课程搜索索引的 pre 字段） */
function buildDownstreamIndex(campusIndex) {
  var idx = {};
  campusIndex.forEach(function (c) {
    (c.pre || []).forEach(function (p) {
      var k = normCode(p);
      if (!idx[k]) idx[k] = [];
      if (idx[k].indexOf(c.code) < 0) idx[k].push(c.code);
    });
  });
  return idx;
}
