// 첫 화면용 요약 파일 만들기 — data.js(13만 건)를 읽어 홈 화면 수치만 뽑아 data_summary.js로 낸다.
// 사용: node make_summary.js        (build_data.py가 빌드 끝에 자동으로 부른다)
//
// 홈 화면은 조건을 건드리기 전까지 늘 같은 값을 보여준다. 그 값만 미리 계산해 두면
// 첫 화면을 수십 KB로 그릴 수 있고, 원자료는 그림이 나온 뒤에 받아도 된다.
// 계열 묶음 규칙은 app.js의 recLeaf/idxGroup을 그대로 옮긴 것이다 — 한쪽을 고치면 이쪽도 고쳐야 한다.
// (어긋나면 원자료가 도착하는 순간 홈 수치가 바뀌므로 눈에 띈다)
const fs = require("fs");

function loadDB(path) {
  const s = fs.readFileSync(path, "utf8");
  let body;
  if (s.slice(0, 200).includes("JSON.parse(")) {
    const lit = s.slice(s.indexOf("'") + 1, s.lastIndexOf("'"));
    body = lit.replace(/\\'/g, "'").replace(/\\\\/g, "\\");
  } else {
    body = s.slice(s.indexOf("{"), s.lastIndexOf("}") + 1);
  }
  return JSON.parse(body);
}

const d = loadDB("data.js");
const cols = d.cols, dict = d.dict || {}, tagList = d.tagList;
const records = d.rows.map(row => {
  const o = {};
  for (let c = 0; c < cols.length; c++) {
    const k = cols[c];
    let v = row[c];
    if (k === "tags") v = v.map(n => tagList[n]);
    else if (dict[k] && typeof v === "number") v = dict[k][v];
    o[k] = v;
  }
  return o;
});
for (const k in (d.sparse || {})) for (const i of d.sparse[k]) records[i][k] = 1;

// ---- app.js와 같은 계열 묶음 ----
const PARENT_LABEL = {elem: "초등학교", mid: "중학교", gen: "일반고", voc: "특성화고·마이스터고",
                      spc: "특목고", aut: "자율고", etc: "특수·기타학교"};
const PARENT_OF = {elem: "elem", mid: "mid", gen: "gen", voc_v: "voc", voc_m: "voc",
                   spc_sci: "spc", spc_lang: "spc", spc_art: "spc", aut: "aut", spe: "etc", alt: "etc"};
const ETC_LV = /방송통신|각종학교|평생학교|고등기술|고등공민/;
const idxByCode = new Map((d.schoolIndex || []).map(s => [s.c, s]));
const spcLeaf = (name, detail) => {
  const dd = detail || "";
  if (dd.includes("과학")) return "spc_sci";
  if (dd.includes("외국어") || dd.includes("국제")) return "spc_lang";
  if (dd.includes("예술") || dd.includes("체육")) return "spc_art";
  if (/영재|과학고/.test(name)) return "spc_sci";
  if (/외국어고|국제고/.test(name)) return "spc_lang";
  if (/예술고|예고|체육고|국악고/.test(name)) return "spc_art";
  return "spc_sci";
};
const idxGroup = s => s.l === "초등학교" ? "elem" : s.l === "중학교" ? "mid"
  : s.l === "특수학교" ? "spe" : ETC_LV.test(s.l || "") ? "alt"
  : s.m ? "voc_m" : s.h === "특성화고" ? "voc_v"
  : s.h === "특목고" ? spcLeaf(s.n, s.d) : s.h === "자율고" ? "aut" : "gen";
function recLeaf(r) {
  const t = r.type;
  if (t === "초등학교") return "elem";
  if (t === "중학교") return "mid";
  if (t === "특수학교") return "spe";
  if (ETC_LV.test(t || "")) return "alt";
  if (t === "일반고") return "gen";
  if (t === "자율고") return "aut";
  if (t === "특성화고" || t === "특성화고·마이스터고") return "voc_v";
  if (t === "마이스터고") return "voc_m";
  if (t === "과학고" || t === "영재학교") return "spc_sci";
  if (t === "특목고") {
    const s = r.schoolCode ? idxByCode.get(r.schoolCode) : null;
    return s ? idxGroup(s) : "spc_sci";
  }
  return null;
}

// ---- app.js와 같은 제품군 목록 ----
const GENERIC = ["기기(PC·태블릿·전자칠판 등)", "SW·플랫폼(제품명 미상)", "SW·플랫폼",
  "인프라(교실·설비)", "로봇·교구·키트", "코스웨어(기타)", "코스웨어", "VR/XR 장비", "드론",
  "3D 프린팅/CAD", "운영 부대구매(제품 미상)", "운영 부대구매", "AI 면접시스템"];
const isGeneric = t => GENERIC.indexOf(t) >= 0;
const hasProduct = r => r.tags.some(t => !isGeneric(t));

const count = (arr, key) => {
  const m = new Map();
  for (const x of arr) { const k = key(x); if (!k) continue; m.set(k, (m.get(k) || 0) + 1); }
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
};

const BASE = records.filter(r => !r.dup);
function homeOf(scope) {
  const RF = scope === "product" ? BASE.filter(hasProduct) : BASE;
  // 첫 화면 막대도 학교 선택 창과 같은 층으로 — 초·중·고·특수기타
  // (app.js의 LEVELS와 같은 묶음이다. 여기서 다르게 묶으면 자료가 다 온 뒤 막대가 바뀌어 보인다)
  const LEVELS = [
    ["초등학교", ["elem"]], ["중학교", ["mid"]],
    ["고등학교", ["gen", "voc_v", "voc_m", "spc_sci", "spc_lang", "spc_art", "aut"]],
    ["특수·기타학교", ["spe", "alt"]],
  ];
  const types = count(RF, r => {
    const g = recLeaf(r);
    if (g) { const lv = LEVELS.find(x => x[1].includes(g)); if (lv) return lv[0]; }
    // 고교 유형을 모를 뿐 학교급은 교명이 말해 준다 (app.js의 levelLabelOf와 같은 기준)
    const t = r.type || "", sc = r.school || "";
    if (/고등학교|고$/.test(t) || /고등학교$/.test(sc)) return "고등학교";
    if (/중학교/.test(t) || /중학교$/.test(sc)) return "중학교";
    if (/초등학교/.test(t) || /초등학교$/.test(sc)) return "초등학교";
    return "기타·미분류";
  });
  const sidos = count(RF, r => r.sido).slice(0, 12);
  const tagPairs = count(RF.flatMap(r => r.tags.map(t => [t])), x => x[0]);
  const names = tagPairs.map(([t]) => t).filter(t => scope !== "product" || !isGeneric(t));
  const schoolsOf = t => new Set(RF.filter(r => r.tags.includes(t)).map(r => r.school)).size;
  const tags = names.slice(0, 12).map(t => [t, schoolsOf(t)]).sort((a, b) => b[1] - a[1]);
  // 공급 기업 상위 12곳 — 온라인몰·조달 대행·제조사는 만든 곳이 아니라 사는 창구라 뺀다
  // (app.js의 CHANNEL/MAKER와 같은 기준. 여기서 다르면 자료가 온 뒤 막대가 바뀌어 보인다)
  const CHANNEL = /지마켓|쿠팡|11번가|인터파크|위메프|티몬|네이버|카카오|이베이|옥션|스마트스토어|우체국|조달청|학교장터|이웃닷컴|다나와|하이마트/;
  const MAKER = /삼성전자|엘지전자|LG전자|애플|레노버|한국HP|에이수스|델테크/;
  const vnorm = n => (n || "")
    .replace(/\(주\)|주식회사|㈜|\(유\)|유한회사|\(재\)|재단법인|\(사\)|사단법인|유한책임회사/g, "")
    .replace(/[（(][^)）]*[)）]/g, "").replace(/[\s.,·\-_*/&'"]+/g, "").toLowerCase().trim();
  const vm = new Map();
  for (const r of RF) {
    const raw = r.vendor || "";
    const k = vnorm(raw);
    if (!k || CHANNEL.test(k) || MAKER.test(k)) continue;
    let e = vm.get(k);
    if (!e) { e = {name: raw, sch: new Set()}; vm.set(k, e); }
    e.sch.add(r.school);
  }
  const vendors = [...vm.values()].map(e => [e.name, e.sch.size])
    .sort((a, b) => b[1] - a[1]).slice(0, 12);
  return {tags, types, sidos, vendors, total: RF.length};
}

const out = {
  meta: d.meta,
  idxCount: (d.schoolIndex || []).length,
  generic: GENERIC,
  home: {product: homeOf("product"), all: homeOf("all")},
};
const t = JSON.stringify(out).replace(/\\/g, "\\\\").replace(/'/g, "\\'")
  .replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
fs.writeFileSync("data_summary.js",
  "// make_summary.js가 생성한 파일 — 직접 수정 금지 (첫 화면을 이것만으로 그린다)\n" +
  "const DB_SUM = JSON.parse('" + t + "');\n");
const kb = (fs.statSync("data_summary.js").size / 1024).toFixed(1);
console.log(`data_summary.js ${kb}KB — 제품 상위 ${out.home.product.tags.length}종 · ` +
  `계열 ${out.home.product.types.length}칸 · 지역 ${out.home.product.sidos.length}곳 · ` +
  `사례 ${out.home.product.total.toLocaleString()}건(제품 확인 기준)`);
