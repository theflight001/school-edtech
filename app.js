// index.html에서 떼어낸 화면 코드 — 요약으로 첫 화면을 그린 뒤에 원자료와 함께 읽는다.
// (전역 이름과 inline onclick 핸들러가 그대로 동작하도록 일반 스크립트로 둔다)
// data.js는 열 이름을 한 번만 적고 되풀이되는 문자열을 사전으로 치환한 압축 형식이다.
// 화면 코드는 예전과 같은 객체 배열을 기대하므로 여기서 원래 모양으로 되돌린다.
// 행을 원래 모양으로 되돌리는 일은 2020~2022년 자료에도 그대로 쓰이므로 떼어 둔다.
// 열 이름·사전·태그표는 data.js 것 하나뿐이다 — data_old.js는 행만 싣는다.
function decodeRows(rows, sparse, base) {
  const d = DB_RAW, cols = d.cols, dict = d.dict || {}, pre = d.urlPrefix || "";
  const out = new Array(rows.length);
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i], o = {};
    for (let c = 0; c < cols.length; c++) {
      const k = cols[c];
      let v = row[c];
      if (k === "tags") v = v.map(n => d.tagList[n]);
      else if (dict[k] && typeof v === "number") v = dict[k][v];
      else if (k === "url" && typeof v === "string" && v[0] === "~") v = pre + v.slice(1);
      o[k] = v;
    }
    o._i = base + i;
    out[i] = o;
  }
  for (const k in (sparse || {})) for (const i of sparse[k]) out[i][k] = 1;
  const won = a => !a ? "" : (a >= 10000
    ? `(${Math.round(a / 10000).toLocaleString()}만원)` : `(${a.toLocaleString()}원)`);
  for (const r of out) {
    if (r.content == null && r.ctpl) {
      r.content = r.ctpl + (r.amt ? " " + won(r.amt) : "")
        + (r.vendor ? " · 계약업체: " + r.vendor : "");
    }
  }
  return out;
}
const DB = (() => {
  const d = DB_RAW, cols = d.cols, dict = d.dict || {}, pre = d.urlPrefix || "";
  const records = new Array(d.rows.length);
  for (let i = 0; i < d.rows.length; i++) {
    const row = d.rows[i], o = {};
    for (let c = 0; c < cols.length; c++) {
      const k = cols[c];
      let v = row[c];
      if (k === "tags") v = v.map(n => d.tagList[n]);
      else if (dict[k] && typeof v === "number") v = dict[k][v];
      else if (k === "url" && typeof v === "string" && v[0] === "~") v = pre + v.slice(1);
      o[k] = v;
    }
    o._i = i;                                   // 상세 열을 나중에 찾아올 때 쓰는 행 번호
    records[i] = o;
  }
  // 값이 거의 없는 표시 열은 해당 행 번호만 넘어온다
  for (const k in (d.sparse || {})) for (const i of d.sparse[k]) records[i][k] = 1;
  // '내용'은 같은 문구가 수만 번 반복돼 조각만 받는다 — 여기서 조립한다
  const won = a => !a ? "" : (a >= 10000
    ? `(${Math.round(a / 10000).toLocaleString()}만원)` : `(${a.toLocaleString()}원)`);
  for (const r of records) {
    if (r.content == null && r.ctpl) {
      r.content = r.ctpl + (r.amt ? " " + won(r.amt) : "")
        + (r.vendor ? " · 계약업체: " + r.vendor : "");
    }
  }
  return { meta: d.meta, records, schoolIndex: d.schoolIndex,
           officeBuy: d.officeBuy || {} };
})();
const R = DB.records;
// ?perf=1 로 열면 단계별 시간을 콘솔에 찍는다 (첫 화면이 느릴 때 어디가 오래 걸리는지 보기 위함)
const PERF = location.search.includes("perf");
const perfMark = (() => { let last = performance.now(); const t0 = last;
  return label => { if (!PERF) return; const n = performance.now();
    console.log(`[perf] ${label}: ${Math.round(n - last)}ms (누적 ${Math.round(n - t0)}ms)`); last = n; }; })();
perfMark("자료 해석·객체화");

// 상세 표시용 열(출처 링크·주소·비고 등)은 첫 화면을 그린 뒤에 따로 받아 합친다.
// 검색·통계는 핵심 열만으로 이미 동작하므로 기다리지 않는다.
// 13만 건 전체에 상세 열을 붙이면 3초 가까이 멈춘다(속성 추가가 그만큼 비싸다).
// 그래서 받아만 두고, 실제로 화면에 나오는 기록에만 그때그때 채운다.
let DETAIL = null, DETAIL_DONE = null;
function mergeDetail(d) {
  DETAIL = d;
  DETAIL_DONE = new Uint8Array(R.length);      // 옛 자료를 붙여도 자리가 모자라지 않게
  if (typeof perfMark === "function") perfMark("상세 자료 받기");
  if (typeof render === "function") render();                  // 받아온 내용으로 다시 그린다
  if (typeof perfMark === "function") perfMark("상세 반영 후 재그리기");
}
// 2020~2022년 상세는 뒤이어 따로 온다 — 행 번호가 offset만큼 밀려 있다
let DETAIL_OLD = null;
const detRow = i => (i < (DETAIL_OLD ? DETAIL_OLD.offset : Infinity))
  ? (DETAIL ? DETAIL.rows[i] : null)
  : (DETAIL_OLD.rows[i - DETAIL_OLD.offset] || null);
function fillDetail(recs) {                                    // 보이는 기록만 채운다
  if (!DETAIL || !recs || !recs.length) return recs;
  const cols = DETAIL.cols, dict = DETAIL.dict || {}, pre = DETAIL.urlPrefix || "";
  for (const o of recs) {
    const i = o && o._i;
    if (i == null || DETAIL_DONE[i]) continue;
    DETAIL_DONE[i] = 1;
    const row = detRow(i);
    if (!row) continue;
    for (let c = 0; c < cols.length; c++) {
      const k = cols[c];
      let v = row[c];
      if (dict[k] && typeof v === "number") v = dict[k][v];
      else if (k === "url" && typeof v === "string" && v[0] === "~") v = pre + v.slice(1);
      if (k === "content" && v == null && o.ctpl) continue;   // 조립해 둔 문구를 덮지 않는다
      o[k] = v;
    }
  }
  return recs;
}
// 검색은 13만 건을 훑으므로 속성을 채우지 않고 상세 자료에서 바로 읽는다
const _detIdx = k => DETAIL ? DETAIL.cols.indexOf(k) : -1;
function detailVal(i, k) {
  if (!DETAIL) return "";
  const c = _detIdx(k);
  if (c < 0) return "";
  const r0 = detRow(i);
  const v = r0 ? r0[c] : null;
  const dict = DETAIL.dict || {};
  return (dict[k] && typeof v === "number") ? dict[k][v] : (v == null ? "" : v);
}
const contentOf = r => r.content != null ? r.content : detailVal(r._i, "content");
(function loadDetail() {
  const s = document.createElement("script");
  s.src = "/data_detail.js?b=20260912g";
  s.onload = () => { if (typeof DB_DETAIL !== "undefined") mergeDetail(DB_DETAIL); };
  document.body.appendChild(s);
})();
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const count = (arr, key) => { const m = new Map(); for (const x of arr) { const k = key(x); if (!k) continue; m.set(k, (m.get(k)||0)+1); } return [...m.entries()].sort((a,b)=>b[1]-a[1]); };
const uniq = arr => [...new Set(arr)];

// ---- 인덱스 ----
const schools = uniq(R.map(r => r.school)).sort();
// 학교를 셀 때 쓰는 열쇠 — 학교코드가 있으면 그것으로, 없으면 이름으로.
// 이름으로만 세면 같은 이름을 쓰는 다른 학교가 한 곳으로 합쳐져 적게 나온다
// (2026-09-12: 같은 조건에서 이름 6,902곳 대 코드 7,316곳).
const skey = r => r.schoolCode || "n:" + r.school;
const tags = count(R.flatMap(r => r.tags.map(t => [t])), x => x[0]);
const schoolCountByTag = t => uniq(R.filter(r => r.tags.includes(t)).map(skey)).length;
// 공급 기업 — 계약 상대자를 그대로 모은다(업체로 제품을 추정하지 않는다).
// 한 회사가 여러 제품을 팔아도 '이 회사가 어디에 무엇을 팔았나'는 그 자체로 볼 만하다.
// 계약서에 적힌 회사 이름은 표기가 제각각이다.
//   (주)지란지교컴즈 · (주)지란지교컴즈(쿨메신저) · (주)지란지교컴 …
// 법인 형태와 괄호 안 덧말을 떼어 같은 이름으로 모은다. 다른 회사를 억지로 합치지는 않는다.
// 해외 구독은 결제 표기가 업체명 칸에 그대로 들어와 회사명과 제품명이 붙어 있다
//   openAIchatGPT(챗지피티) · OPENAI *CHATGPT SUBSCR · CHATGPT SUBSCRIPTION → 회사는 OpenAI 하나다
// 이런 표기는 회사 이름으로 되돌려 한곳에 모은다(제품 태그는 따로 붙는다).
const VENDOR_CANON = [
  [/open ?ai|chat ?gpt|챗지피티|오픈에이아이/i, "OpenAI"],
  [/anthropic|claude/i, "Anthropic"],
  [/padlet|패들렛/i, "Padlet"],
  [/kahoot|카훗/i, "Kahoot!"],
  [/^\s*canva|canva ?(?:pro|for|inc)/i, "Canva"],
  [/^\s*notion|notion ?labs/i, "Notion Labs"],
  [/quizlet|퀴즐렛/i, "Quizlet"],
  [/^\s*suno(?:\s|,|$)|suno ?ai/i, "Suno"],
  [/perplexity/i, "Perplexity AI"],
  [/adobe|어도비/i, "Adobe"],        // 'KCP-결제-Adobe'처럼 결제 대행이 앞에 붙기도 한다
];
const canonOf = raw => { for (const [re, nm] of VENDOR_CANON) if (re.test(raw || "")) return nm; return null; };

const vnorm = n => (canonOf(n) ? canonOf(n) : (n || "")
  .replace(/\(주\)|주식회사|㈜|\(유\)|유한회사|\(재\)|재단법인|\(사\)|사단법인|유한책임회사/g, "")
  .replace(/[（(][^)）]*[)）]/g, "")          // 괄호 안 덧말 — 제품명·지점명이 붙어 나온다
  // 사이에 낀 기호와 대소문자 차이로 갈라지던 것을 모은다
  //   S2B / s2b · Padlet / PADLET · 지마켓옥션 / 지마켓-옥션 / 지마켓&옥션
  .replace(/[\s.,·\-_*/&'"]+/g, "")).toLowerCase().trim();
const VENDORS = new Map();                    // 정규화 이름 → {name, n, forms}
for (const r of R) {
  const v = vnorm(r.vendor);
  if (!v) continue;
  let e = VENDORS.get(v);
  if (!e) VENDORS.set(v, e = {key: v, n: 0, forms: new Map()});
  e.n++;
  e.forms.set(r.vendor, (e.forms.get(r.vendor) || 0) + 1);
}
for (const e of VENDORS.values()) {           // 가장 많이 쓰인 표기를 대표 이름으로
  const raw = [...e.forms.entries()].sort((a, b) => b[1] - a[1])[0][0];
  e.name = canonOf(raw) || raw;              // 결제 표기는 회사 이름으로 되돌린다
}
// 끝 글자가 한둘 잘린 표기는 훨씬 많이 쓰인 쪽에 합친다 (지란지교컴 4건 → 지란지교컴즈 763건).
// 다른 회사가 잘못 묶이지 않도록 '앞부분이 같고 · 차이 2글자 이내 · 10배 이상 많을 때'만 합친다.
const VMERGE = new Map();
{
  const list = [...VENDORS.values()].sort((a, b) => b.n - a.n);
  // 앞부분이 같은 회사가 둘 이상이면 어디에 붙일지 알 수 없다 —
  // '아이스크림'은 아이스크림에듀·아이스크림미디어 둘 다일 수 있고,
  // '지란지교'는 지란지교컴즈·지란지교테크 둘 다일 수 있다. 이런 것은 합치지 않는다.
  // 9천 곳을 서로 견주면 8천만 번이라 1초가 넘게 걸린다 — 앞부분을 미리 세어 둔다.
  const prefN = new Map(), prefOne = new Map();
  for (const v of list) {
    for (let i = 4; i < v.key.length; i++) {
      const p = v.key.slice(0, i);
      const c = (prefN.get(p) || 0) + 1;
      prefN.set(p, c);
      if (c === 1) prefOne.set(p, v);
    }
  }
  for (const small of list) {
    if (small.key.length < 4) continue;
    if (prefN.get(small.key) !== 1) continue;
    const big = prefOne.get(small.key);
    if (big && big.n >= small.n * 10 && big.key.length - small.key.length <= 2)
      VMERGE.set(small.key, big.key);
  }
  // 한 글자만 어긋난 오타 표기도 합친다 ('다이얼커퓨티케이션즈' → '다이얼커뮤니케이션즈').
  // 앞 두 글자는 회사를 가르는 자리라 거기서 어긋나면 합치지 않는다 —
  // '이레·이안·이현·한솔정보통신'은 '이솔정보통신'의 오타가 아니라 저마다 다른 회사다.
  // 그래서 앞 두 글자가 같은 것끼리만 묶어 견준다(전부 견주면 또 8천만 번이다).
  const diffAt = (a, b) => {
    if (Math.abs(a.length - b.length) > 1) return -1;
    if (a.length === b.length) {
      let at = -1;
      for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) { if (at >= 0) return -1; at = i; }
      return at;
    }
    const [s1, s2] = a.length < b.length ? [a, b] : [b, a];
    let i = 0, j = 0, at = -1;
    while (i < s1.length && j < s2.length) {
      if (s1[i] === s2[j]) { i++; j++; } else { if (at >= 0) return -1; at = j; j++; }
    }
    return at >= 0 ? at : s2.length - 1;
  };
  const bucket = new Map();
  for (const v of list) {
    if (v.key.length < 6) continue;
    const h = v.key.slice(0, 2);
    (bucket.get(h) || bucket.set(h, []).get(h)).push(v);
  }
  for (const group of bucket.values()) {
    for (const small of group) {
      if (VMERGE.has(small.key)) continue;
      const big = group.find(b => b !== small && !VMERGE.has(b.key)
        && b.n >= small.n * 10 && diffAt(small.key, b.key) >= 2);
      if (big) VMERGE.set(small.key, big.key);
    }
  }
  for (const [from, to] of VMERGE) {
    const a = VENDORS.get(from), b = VENDORS.get(to);
    if (!a || !b) continue;
    b.n += a.n;
    for (const [f, c] of a.forms) b.forms.set(f, (b.forms.get(f) || 0) + c);
    VENDORS.delete(from);
  }
}
const vkey = n => { const k = vnorm(n); return VMERGE.get(k) || k; };
const vendorRecs = key => R.filter(r => vkey(r.vendor) === key);
// 온라인몰·조달 대행·대형 제조사는 '에듀테크 공급사'가 아니라 사는 창구다 — 꼬리표를 달아 구분한다
// '이웃닷컴'은 온라인몰이 아니라 e알리미를 만드는 회사다(에듀집: e알리미 = 주식회사 이웃닷컴).
// 이름이 닷컴으로 끝난다고 창구로 보면 만든 회사가 공급 기업에서 통째로 빠진다.
const CHANNEL = /지마켓|쿠팡|11번가|인터파크|위메프|티몬|네이버|카카오|이베이|옥션|스마트스토어|우체국|조달청|학교장터|다나와|하이마트/;
const MAKER = /삼성전자|엘지전자|LG전자|애플|레노버|한국HP|에이수스|델테크/;
const vendorKind = k => CHANNEL.test(k) ? "구매 창구" : MAKER.test(k) ? "제조사" : "공급 기업";

const IDX = DB.schoolIndex || [];
const idxByCode = new Map(IDX.map(s => [s.c, s]));
const recordCodes = new Set(R.map(r => r.schoolCode).filter(Boolean));

// ---- 차트 부품 ----
const BAR_FROM = [43, 89, 216], BAR_TO = [79, 197, 150];
function barColor(i, n) {
  const t = n <= 1 ? 0 : i / (n - 1);
  const c = BAR_FROM.map((f, j) => Math.round(f + (BAR_TO[j] - f) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
function barChart(pairs, {linkFn, max: mx, drillFn, labelFn = esc} = {}) {
  const max = mx || Math.max(...pairs.map(p => p[1]), 1);
  const n = pairs.length;
  return `<div class="bars">` + pairs.map(([k, v], i) => `
    <div class="brow${drillFn ? " rowlink" : ""}"${drillFn ? ` onclick="go('${drillFn(k)}')" role="link" tabindex="0" title="누르면 해당 학교 목록을 보여줍니다"` : ""}>
      <span class="lbl" title="${esc(tagName(k))}">${linkFn ? `<a href="${linkFn(k)}">${labelFn(k)}</a>` : labelFn(k)}</span>
      <span class="track"><span class="fill" style="width:${(v/max*100).toFixed(1)}%;background:${barColor(i, n)}"></span><span class="val">${v}</span></span>
    </div>`).join("") + `</div>`;
}
const PAGE_SIZE = 20;
let PAGE = 1;
let LISTQ = "";
let SORTK = "new";
window.setPage = p => { PAGE = p; render(); };
window.setSort = v => { SORTK = v; PAGE = 1; render(); };
function sortRecs(recs) {
  const t = r => {
    const m = r.period && r.period.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return +(m[1] + m[2] + m[3]);
    return r.ym ? r.ym * 100 + 15 : (r.year ? r.year * 10000 + 615 : 0);
  };
  const arr = [...recs];
  if (SORTK === "new") arr.sort((a, b) => t(b) - t(a));
  else if (SORTK === "old") arr.sort((a, b) => t(a) - t(b));
  else if (SORTK === "school") arr.sort((a, b) => a.school.localeCompare(b.school, "ko"));
  else if (SORTK === "product") arr.sort((a, b) => ((a.tags[0] || "힣").localeCompare(b.tags[0] || "힣", "ko")) || (t(b) - t(a)));
  else if (SORTK === "amt") arr.sort((a, b) => (b.amt || -1) - (a.amt || -1));
  return arr;
}
window.applyListQ = v => {
  LISTQ = v; PAGE = 1; render();
  const el = document.getElementById("lq");
  if (el) { el.focus(); const n = el.value.length; el.setSelectionRange(n, n); }
};
// 결과 내 검색 — 목록과 지도가 같은 기준으로 거른다
function listQFilter(recs) {
  if (!LISTQ) return recs;
  const terms = queryTerms(LISTQ.toLowerCase());
  return recs.filter(r => terms.some(t => (r.school + r.product + contentOf(r)).toLowerCase().includes(t)));
}
// 목록 위 도구줄 — 왼쪽에 '목록 | 지도', 오른쪽에 정렬·결과 내 검색
function listToolbar(total, showFilter, tool) {
  const sortSel = `<select class="sortsel" onchange="setSort(this.value)" aria-label="정렬">
      ${[["new","최신순"],["old","오래된순"],["school","학교명순"],["product","제품군순"],["amt","금액 높은순"]].map(([k,l]) => `<option value="${k}"${SORTK===k?" selected":""}>${l}</option>`).join("")}
    </select>`;
  const filterHtml = showFilter ? `${LISTQ ? `<span class="listq-n"><b>${total.toLocaleString()}건</b></span>` : ""}
    <input id="lq" class="listq" type="search" placeholder="결과 내 검색" value="${esc(LISTQ)}"
      oninput="if(this.value==='')applyListQ('')" onkeyup="if(event.key==='Enter')applyListQ(this.value)">` : "";
  return `<div class="listtool">${tool ? tool + '<span class="lt-grow"></span>' : ""}${sortSel}${filterHtml}</div>`;
}
function pagedTable(recs, opts) {
  const origTotal = recs.length;
  const showFilter = origTotal > PAGE_SIZE || LISTQ;
  recs = sortRecs(listQFilter(recs));
  const total = recs.length;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.min(PAGE, pages);
  const slice = fillDetail(recs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE));
  const tool = opts && opts.tool;
  const topbar = tool || pages > 1 || showFilter || SORTK !== "new" ? listToolbar(total, showFilter, tool) : "";
  let bottom = "";
  if (pages > 1) {
    const nums = [];
    for (let i = 1; i <= pages; i++) {
      if (i === 1 || i === pages || Math.abs(i - page) <= 2) nums.push(i);
      else if (nums[nums.length - 1] !== "…") nums.push("…");
    }
    bottom = `<div class="pager">
      <button ${page === 1 ? "disabled" : ""} onclick="setPage(${page - 1})">‹ 이전</button>
      ${nums.map(n => n === "…" ? `<span class="pgdots">…</span>` : `<button class="${n === page ? "cur" : ""}" onclick="setPage(${n})">${n}</button>`).join("")}
      <button ${page === pages ? "disabled" : ""} onclick="setPage(${page + 1})">다음 ›</button>
    </div>
    <div class="pginfo">전체 ${total.toLocaleString()}건 중 ${((page - 1) * PAGE_SIZE + 1).toLocaleString()}–${Math.min(page * PAGE_SIZE, total).toLocaleString()}건 표시</div>`;
  }
  return topbar + recordTable(slice, opts) + bottom;
}
function recordTable(recs, {showSchool = true} = {}) {
  if (!recs.length) return `<div class="empty">해당 기록이 없습니다</div>`;
  return `<div class="tablewrap"><table${showSchool ? "" : ' class="noschool"'}><thead><tr>${showSchool ? "<th>학교</th>" : ""}<th>제품/서비스</th><th>시기</th><th>내용</th><th>출처</th></tr></thead><tbody>` +
    recs.map(r => `<tr>
      ${showSchool ? `<td><a href="${r.schoolCode ? `/code/${encodeURIComponent(r.schoolCode)}` : `/school/${encodeURIComponent(r.school)}`}">${esc(r.school)}</a><div class="conf">${esc(r.type)} · ${esc(r.region)}${r.origSchool ? ` · 계약 당시 ${esc(r.origSchool)}` : ""}</div></td>` : ""}
      <td>${esc(r.product)}<div>${r.tags.map(t => `<a class="chip${GENERIC_TAGS.has(t) ? " gen" : ""}" href="/tag/${encodeURIComponent(t)}">${tagLabel(t)}</a>`).join("")}</div></td>
      <td style="white-space:nowrap">${esc(r.period)}</td>
      <td style="max-width:320px">${esc(r.content)}${r.vendor && vendorKind(vkey(r.vendor)) === "공급 기업" ? `<div class="conf"><a href="/vendor/${encodeURIComponent(vkey(r.vendor))}">${esc(r.vendor)}의 다른 납품 보기 ›</a></div>` : ""}${confNote(r)}${noteLine(r)}</td>
      <td>${r.url && !/S2B|나라장터/i.test(r.sourceType) ? `<a href="${esc(r.url)}" target="_blank" rel="noopener" title="${r.sourceType === "학교 전용 플랫폼" ? `학교 전용 주소: ${esc(r.url.replace(/^https?:\/\//, "").split("/")[0])} — 전용 페이지 존재가 도입의 근거입니다` : esc(r.url)}">${esc(r.sourceType)}</a>` : esc(r.sourceType)}</td>
    </tr>`).join("") + `</tbody></table></div>`;
}

// ---- 기간 필터 ----
// 자료는 2020년까지 있지만 기본으로는 2023년부터 본다.
// 2020~2022년은 계약명에 제품 이름이 잘 안 적히던 시기라(제품군만 붙는 비율 76%)
// 기본에 섞으면 지금 그림이 희석된다. 넓혀 보고 싶은 사람만 당겨 오게 한다.
// 첫 화면은 올해(2026년)만 보여 준다. 자료는 2020년까지 닿지만 그 앞을 늘 받아 오면
// 첫 화면이 그만큼 늦다 — 기간을 넓힐 때 따로 받는다(withOld).
const BASE_FROM = "2026-01";
let PF = BASE_FROM, PT = "";  // "YYYY-MM"
let PF_TOUCHED = false;   // 기간을 손으로 고른 적이 있는가
window.setPF = v => { PF = v; PF_TOUCHED = true; render(); };
window.setPT = v => { PT = v; PF_TOUCHED = true; render(); };
window.clearPeriod = () => { PF = BASE_FROM; PT = ""; PF_TOUCHED = true; render(); };
const ymInt = s => s ? parseInt(s.replace("-", ""), 10) : null;
// 고를 수 있는 마지막 달은 빌드가 알려 준다 — 손으로 적어 두면 월 갱신 뒤에도 옛 달에 멈춘다.
// 자료가 닿는 마지막 달(ymMax)이 아니라 '온전히 다 받은 달'(ymLabel)까지만 연다 —
// 이번 달치는 아직 며칠분뿐이라(2026-09-12 기준 9월 357건) 고르면 텅 빈 결과처럼 보인다.
const YM_MIN = 202001, YM_MAX = +((DB_RAW.meta && (DB_RAW.meta.ymLabel || DB_RAW.meta.ymMax)) || 202608);
const YM_TO = `${String(YM_MAX).slice(0, 4)}-${String(YM_MAX).slice(4)}`;
let pkS = null, pkE = null, pkBase = 2025;
// 기본(2026년~)과 다르게 잡혀 있으면 조건이 걸린 것이다
const periodOn = () => (PF !== BASE_FROM) || !!PT;
const ymStr = ym => `${Math.floor(ym / 100)}-${String(ym % 100).padStart(2, "0")}`;
const ymKo = ym => `${Math.floor(ym / 100)}.${String(ym % 100).padStart(2, "0")}`;
window.openPicker = () => {
  // 늘 빈 상태로 연다. 지금 기간을 물려받으면 달력은 2020년을 펴 놓고 위에는
  // '2026.01 ~ 종료 월 선택'이라고 적혀 서로 어긋나 보인다.
  pkS = pkE = null;
  // 넓히려고 여는 것이므로 옛 해가 먼저 보여야 한다
  pkBase = 2020;
  drawPicker();
};
window.closePicker = () => { document.getElementById("pickerRoot").innerHTML = ""; };
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && document.getElementById("pickerRoot").innerHTML) closePicker();
});
let pkSliding = false;
window.pkShift = d => {
  const b = Math.min(2025, Math.max(2020, pkBase + d));
  if (b === pkBase || pkSliding) return;          // 넘기는 중에 또 넘기면 겹쳐 보인다
  // 옛 달력을 그대로 복사해 두었다가, 새 것이 들어오는 동안 반대쪽으로 내보낸다.
  // 복사해 두지 않고 새 것만 밀어 넣으면 빈 자리가 비쳐 방정맞아 보인다.
  const old = document.querySelector(".pk-viewport .pk-years");
  const ghost = old ? old.cloneNode(true) : null;
  pkBase = b;
  drawPicker();
  const vp = document.querySelector(".pk-viewport");
  if (!ghost || !vp) return;
  const cur = vp.querySelector(".pk-years");
  const way = d > 0 ? "next" : "prev";
  ghost.classList.add("ghost", "out-" + way);
  cur.classList.add("in-" + way);
  vp.appendChild(ghost);
  pkSliding = true;
  const done = () => {
    ghost.remove();
    cur.classList.remove("in-" + way);
    pkSliding = false;
  };
  // 움직임을 끈 설정(prefers-reduced-motion)에서는 animationend가 오지 않는다
  if (getComputedStyle(ghost).animationName === "none") { done(); return; }
  ghost.addEventListener("animationend", done, {once: true});
  setTimeout(done, 700);            // 애니메이션이 씹혔을 때를 위한 뒷문
};
// 달력을 옆으로 밀거나 휠을 굴려도 해가 넘어간다. drawPicker가 안쪽을 통째로 다시 그리므로
// 판마다 붙이지 않고 바깥 상자에 한 번만 걸어 둔다.
(function pkSwipe() {
  const root = document.getElementById("pickerRoot");
  if (!root) return;
  const inYears = e => e.target.closest && e.target.closest(".pk-years");
  let wheelAt = 0;
  root.addEventListener("wheel", e => {
    if (!inYears(e)) return;
    const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (Math.abs(d) < 8) return;
    const now = performance.now();
    if (now - wheelAt < 260) return;             // 한 번 굴릴 때 한 해씩만 넘긴다
    wheelAt = now;
    e.preventDefault();
    pkShift(d > 0 ? 1 : -1);
  }, {passive: false});
  let x0 = null, el = null;
  root.addEventListener("pointerdown", e => {
    el = inYears(e);
    if (!el) return;
    x0 = e.clientX;
    el.classList.add("drag");
  });
  const end = e => {
    if (x0 === null) return;
    const dx = e.clientX - x0;
    if (el) el.classList.remove("drag");
    x0 = null; el = null;
    if (Math.abs(dx) >= 60) pkShift(dx < 0 ? 1 : -1);   // 왼쪽으로 밀면 다음 해
  };
  root.addEventListener("pointerup", end);
  root.addEventListener("pointercancel", () => { if (el) el.classList.remove("drag"); x0 = null; el = null; });
})();
window.pkPick = ym => {
  if (pkS !== null && pkE === null && ym >= pkS) pkE = ym;
  else { pkS = ym; pkE = null; }
  drawPicker();
};
// 기본 기간(2026년~) 앞의 기록은 첫 화면에 필요 없어 따로 두었다 — data.js가 그만큼 가볍다.
// 기간을 그 앞으로 넓힐 때 한 번만 받아 붙인다.
let OLD_STATE = "none";                       // none → loading → done
// 기본 기간보다 앞으로 넓히면 따로 둔 옛 기록이 필요하다 (data.js는 기본 기간만 싣는다)
function needOld(from) { return from === "" || from < BASE_FROM; }
function withOld(from, then) {
  if (!needOld(from) || OLD_STATE === "done") return then();
  if (OLD_STATE === "loading") return;
  OLD_STATE = "loading";
  const view = $("#view");
  if (view) view.insertAdjacentHTML("afterbegin",
    `<div class="notice" id="oldload"><b>지난 기록을 불러오는 중입니다…</b></div>`);
  const add = () => {
    if (typeof DB_OLD !== "undefined") {
      const more = decodeRows(DB_OLD.rows, DB_OLD.sparse, DB_OLD.offset);
      for (const r of more) R.push(r);
      _brKey = null;                          // 걸러 둔 것을 버린다
      NAME_POOL = null;
    }
    OLD_STATE = "done";
    const s2 = document.createElement("script");
    s2.src = "/data_detail_old.js?b=20260912g";
    s2.onload = () => {
      if (typeof DB_DETAIL_OLD !== "undefined") {
        DETAIL_OLD = DB_DETAIL_OLD;
        DETAIL_DONE = new Uint8Array(R.length);
        render();
      }
    };
    document.body.appendChild(s2);
    then();
  };
  const s = document.createElement("script");
  s.src = "/data_old.js?b=20260912g";
  s.onload = add;
  s.onerror = () => { OLD_STATE = "none"; const e = $("#oldload"); if (e) e.remove(); };
  document.body.appendChild(s);
}
window.pkApply = () => {
  if (pkS === null) return;
  const from = ymStr(pkS), to = ymStr(pkE !== null ? pkE : pkS);
  closePicker();
  withOld(from, () => { PF = from; PT = to; PF_TOUCHED = true; render(); });
};
// ---- 학교 계열 필터 (부모 6칸 + 세부 잎사귀) ----
const LEAVES = [
  {k: "elem", label: "초등학교", parent: "elem"},
  {k: "mid", label: "중학교", parent: "mid"},
  {k: "gen", label: "일반고", parent: "gen"},
  {k: "voc_v", label: "특성화고", parent: "voc"},
  {k: "voc_m", label: "마이스터고", parent: "voc"},
  {k: "spc_sci", label: "과학고·영재학교", parent: "spc"},
  {k: "spc_lang", label: "외국어고·국제고", parent: "spc"},
  {k: "spc_art", label: "예술고·체육고", parent: "spc"},
  {k: "aut", label: "자율고", parent: "aut"},
  {k: "spe", label: "특수학교", parent: "etc"},
  // '기타학교'를 한 덩어리로 두면 성격이 아주 다른 학교가 섞인다 — 다섯으로 나눈다.
  {k: "alt_v", label: "각종학교", parent: "etc"},
  {k: "alt_l", label: "평생학교", parent: "etc"},
  {k: "alt_b", label: "방송통신 중·고", parent: "etc"},
  {k: "alt_t", label: "고등기술·고등공민학교", parent: "etc"},
];
const PARENTS = [
  {k: "elem", label: "초등학교"}, {k: "mid", label: "중학교"}, {k: "gen", label: "일반고"},
  {k: "voc", label: "특성화고·마이스터고"}, {k: "spc", label: "특목고"}, {k: "aut", label: "자율고"},
  {k: "etc", label: "특수·기타학교"},
];
const leafLabel = {}, parentOf = {}, parentLabel = {};
LEAVES.forEach(l => { leafLabel[l.k] = l.label; parentOf[l.k] = l.parent; });
PARENTS.forEach(p => parentLabel[p.k] = p.label);
const leavesOf = p => LEAVES.filter(l => l.parent === p).map(l => l.k);
// 기록이 어느 학교급인지 — 초·중·고·특수기타 (고교 유형은 한 층 아래다)
function levelLabelOf(r) {
  const g = recLeaf(r);
  if (g) { const lv = LEVELS.find(x => x.leaves.includes(g)); if (lv) return lv.label; }
  // 고교 유형을 모를 뿐 학교급은 교명이 말해 준다 — '○○고등학교'를 기타로 두지 않는다
  const t = r.type || "", s = r.school || "";
  if (/고등학교|고$/.test(t) || /고등학교$/.test(s)) return "고등학교";
  if (/중학교/.test(t) || /중학교$/.test(s)) return "중학교";
  if (/초등학교/.test(t) || /초등학교$/.test(s)) return "초등학교";
  return "기타·미분류";     // 남는 것은 '전 학교급'·'다수 학교' 같은 집합 항목뿐이다
}

function spcLeaf(name, detail) {
  const d = detail || "";
  if (d.includes("과학")) return "spc_sci";
  if (d.includes("외국어") || d.includes("국제")) return "spc_lang";
  if (d.includes("예술") || d.includes("체육")) return "spc_art";
  if (/영재|과학고/.test(name)) return "spc_sci";
  if (/외국어고|국제고/.test(name)) return "spc_lang";
  if (/예술고|예고|체육고|국악고/.test(name)) return "spc_art";
  return "spc_sci";
}
const ETC_LV = /방송통신|각종학교|평생학교|고등기술|고등공민/;
// NEIS는 '학교 종류'(법적 지위)와 '고등학교 구분'(교육과정)을 다른 칸에 적는다. 각종학교·평생학교처럼
// 정규 학교가 아닌 종류에 '특성화고'가 나란히 붙으면 두 값이 같은 층의 분류로 읽혀 무엇이 맞는지
// 헷갈린다(예: 꿈타래학교 = 각종학교(고) + 특성화고). 그때만 구분을 '과정'으로 적어 층을 드러낸다.
const HS_COURSE = {"특성화고": "특성화 과정", "일반고": "일반 과정", "자율고": "자율 과정",
  "특목고": "특수목적 과정", "마이스터고": "마이스터 과정"};
const hsPhrase = (level, hs) => !hs ? "" : ETC_LV.test(level || "") ? (HS_COURSE[hs] || hs) : hs;
// NEIS 학교유형 값을 다섯 갈래로 가른다 ('각종학교(고)'·'평생학교(초)-4년12학기' 같은 꼴)
const etcLeaf = lv => /방송통신/.test(lv) ? "alt_b" : /각종학교/.test(lv) ? "alt_v"
  : /평생학교/.test(lv) ? "alt_l" : /고등기술|고등공민/.test(lv) ? "alt_t" : null;
const idxGroup = s => s.l === "초등학교" ? "elem" : s.l === "중학교" ? "mid"
  : s.l === "특수학교" ? "spe" : ETC_LV.test(s.l || "") ? etcLeaf(s.l)
  : s.m ? "voc_m" : s.h === "특성화고" ? "voc_v"
  : s.h === "특목고" ? spcLeaf(s.n, s.d) : s.h === "자율고" ? "aut" : "gen";
function recLeaf(r) {
  const t = r.type;
  if (t === "초등학교") return "elem";
  if (t === "중학교") return "mid";
  if (t === "특수학교") return "spe";
  if (ETC_LV.test(t || "")) return etcLeaf(t);
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
const IDX_GROUP_COUNT = {};
IDX.forEach(s => { const g = idxGroup(s); IDX_GROUP_COUNT[g] = (IDX_GROUP_COUNT[g] || 0) + 1; });
let SF = new Set();  // 선택된 잎사귀 키들
// 설립 구분(국·공·사립)은 계열과 겹치지 않는 축이다. 초등학교·중학교처럼 법령상 유형이 없는 급에도
// 적용되고, 사립은 예산·조달 경로가 달라 도입 양상이 다르다.
let ES = new Set();  // 선택된 설립 구분
const FOUNDINGS = ["공립", "사립", "국립"];
const foundingOf = r => { const s = r.schoolCode ? idxByCode.get(r.schoolCode) : null; return s ? s.f : ""; };
const esMatch = r => !ES.size || ES.has(foundingOf(r));
const esLabel = () => ES.size ? [...ES].join("·") : "전체";
const sfMatch = r => { if (!SF.size) return true; const g = recLeaf(r); return g !== null && SF.has(g); };
// 첫 화면 '검색 가능 학교' 칸과 '학교 전체 보기' 목록이 같은 판정식을 쓴다 — 숫자가 어긋나지 않게
const idxPass = s => (!SF.size || SF.has(idxGroup(s))) && (!RG.size || RG.has(s.s))
  && (!ES.size || ES.has(s.f));
const sfIdxCount = () => IDX.filter(idxPass).length;
const IDX_FOUND_COUNT = {};
IDX.forEach(s => { IDX_FOUND_COUNT[s.f] = (IDX_FOUND_COUNT[s.f] || 0) + 1; });
function setParts(set) {
  const parts = [];
  for (const p of PARENTS) {
    const ls = leavesOf(p.k), sel = ls.filter(k => set.has(k));
    if (!sel.length) continue;
    if (sel.length === ls.length) parts.push(p.label);
    else parts.push(...sel.map(k => leafLabel[k]));
  }
  return parts;
}
const sfLabel = () => {
  if (!SF.size) return "전국";
  const parts = setParts(SF);
  return parts.length <= 2 ? parts.join("·") : `${parts[0]} 외 ${parts.length - 1}`;
};
// ---- 지역(시도) 필터 ----
const SIDOS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
               "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"];
const IDX_SIDO_COUNT = {};
IDX.forEach(s => { IDX_SIDO_COUNT[s.s] = (IDX_SIDO_COUNT[s.s] || 0) + 1; });
let RG = new Set();
const rgMatch = r => !RG.size || RG.has(r.sido);
const rgLabel = () => {
  if (!RG.size) return "전국";
  // 합쳐진 시도를 다 골랐으면 통합 이름 한 칸으로 적는다
  const left = new Set(SIDOS.filter(s => RG.has(s)));
  const names = [];
  for (const [k, ms] of Object.entries(MERGED)) {
    if (ms.every(x => left.has(x))) {
      names.push(k);
      ms.forEach(x => left.delete(x));
    }
  }
  names.push(...SIDOS.filter(s => left.has(s)));
  return names.length <= 3 ? names.join("·") : `${names[0]} 외 ${names.length - 1}개 지역`;
};
// 2026년 7월 1일 광주광역시와 전라남도가 '전남광주통합특별시'로 합쳐졌고 교육청도
// 함께 통합됐다(전남광주통합특별시교육청). 다만 계약 공개 시스템은 2028년까지 따로 돌아
// 자료는 여전히 '광주'·'전남'으로 들어온다. 그래서 기록의 딱지는 그대로 두고 —
// 2023년에 광주에서 산 것을 '광주'로 찾을 수 있어야 한다 — 고르개에서만 한 칸으로 묶는다.
const MERGED = {"전남광주": ["광주", "전남"]};
const mergedOf = s => Object.keys(MERGED).find(k => MERGED[k].includes(s));
let rgSel = null;
window.openRegionPicker = () => { rgSel = new Set(RG); drawRegionPicker(); };
window.rgToggle = s => {
  // 통합된 시도는 함께 켜고 함께 끈다
  const group = MERGED[s] || [s];
  const on = group.every(x => rgSel.has(x));
  group.forEach(x => on ? rgSel.delete(x) : rgSel.add(x));
  drawRegionPicker();
};
window.rgAll = () => { RG = new Set(); closePicker(); render(); };
window.rgApply = () => { RG = rgSel.size === SIDOS.length ? new Set() : new Set(rgSel); closePicker(); render(); };
// 고르개에 보여 줄 칸 — 합쳐진 시도는 한 칸으로 묶는다
const RG_CELLS = (() => {
  const out = [], seen = new Set();
  for (const s of SIDOS) {
    const g = mergedOf(s);
    if (!g) { out.push({k: s, label: s, members: [s]}); continue; }
    if (seen.has(g)) continue;
    seen.add(g);
    out.push({k: g, label: g, members: MERGED[g]});
  }
  return out;
})();
function drawRegionPicker() {
  const cells = RG_CELLS.map(c => {
    const n = c.members.reduce((a, x) => a + (IDX_SIDO_COUNT[x] || 0), 0);
    const on = c.members.every(x => rgSel.has(x));
    const part = !on && c.members.some(x => rgSel.has(x));
    return `<button class="pk-cell sc-cell${on ? " end" : part ? " part" : ""}" onclick="rgToggle('${c.k}')">
      <span>${c.label}</span><span class="sc-n">${n.toLocaleString()}개교</span>
    </button>`;
  }).join("");
  const picked = RG_CELLS.filter(c => c.members.every(x => rgSel.has(x))).map(c => c.label).join(" · ");
  document.getElementById("pickerRoot").innerHTML = `
    <div class="pk-overlay">
      <div class="pk-panel" role="dialog" aria-label="지역 선택">
        <button class="pk-x" onclick="closePicker()" aria-label="닫기">✕</button>
        <div class="pk-top"><span></span>
          <div style="text-align:center"><div class="pk-title">지역 선택</div><div class="pk-range">${picked || "전국 (17개 시도 전체)"}</div></div>
        <span></span></div>
        <div class="pk-grid rg-grid">${cells}</div>
        <div class="pk-foot">
          <span class="pk-hint">시도교육청 단위 · 여러 지역을 함께 선택할 수 있습니다<br>
            전남광주는 2026년 7월 1일 통합되었습니다. 다만 정보시스템은 당분간 별도로 운영되어,
            세부검색 결과는 통합 전 지역(광주·전남)이 제공됩니다</span>
          <span style="display:flex;gap:8px">
            <button class="pk-btn" onclick="rgAll()">전국</button>
            <button class="pk-btn" onclick="closePicker()">취소</button>
            <button class="pk-btn primary" onclick="rgApply()" ${rgSel.size ? "" : "disabled"}>적용</button>
          </span>
        </div>
      </div>
    </div>`;
}

let scSel = null, esSel = null;
window.openSchoolPicker = () => { scSel = new Set(SF); esSel = new Set(ES); drawSchoolPicker(); };
window.esToggle = k => { esSel.has(k) ? esSel.delete(k) : esSel.add(k); drawSchoolPicker(); };
window.scToggle = k => {
  scSel.has(k) ? scSel.delete(k) : scSel.add(k);
  if (scSel.size && !esSel.size) FOUNDINGS.forEach(f => esSel.add(f));
  if (!scSel.size) esSel.clear();
  drawSchoolPicker();
};
window.scParent = p => {
  const ls = leavesOf(p);
  const all = ls.every(k => scSel.has(k));
  ls.forEach(k => all ? scSel.delete(k) : scSel.add(k));
  if (scSel.size && !esSel.size) FOUNDINGS.forEach(f => esSel.add(f));
  if (!scSel.size) esSel.clear();
  drawSchoolPicker();
};
window.scAll = () => { SF = new Set(); ES = new Set(); closePicker(); render(); };
window.scApply = () => {
  SF = scSel.size === LEAVES.length ? new Set() : scSel;
  ES = esSel.size === FOUNDINGS.length ? new Set() : esSel;
  closePicker(); render();
};
// 고르는 순서를 학교급 → (고등학교면) 유형 → 설립으로 바꿨다.
// 처음에 일곱 칸을 늘어놓으면 초·중처럼 유형이 없는 급까지 같은 무게로 보여 복잡했다.
const LEVELS = [
  {k: "elem", label: "초등학교", leaves: ["elem"]},
  {k: "mid", label: "중학교", leaves: ["mid"]},
  {k: "high", label: "고등학교", leaves: ["gen", "voc_v", "voc_m", "spc_sci", "spc_lang", "spc_art", "aut"]},
  {k: "etc", label: "특수·기타학교", leaves: ["spe", "alt_v", "alt_l", "alt_b", "alt_t"]},
];
const HIGH_PARENTS = ["gen", "voc", "spc", "aut"];          // 고등학교 안의 유형
window.scLevel = k => {
  const ls = LEVELS.find(x => x.k === k).leaves;
  const all = ls.every(x => scSel.has(x));
  ls.forEach(x => all ? scSel.delete(x) : scSel.add(x));
  // 학교급을 고르면 설립은 '전부 포함'이 기본이다 — 빈 칩으로 두면 아무것도 안 고른 것처럼 보인다
  if (scSel.size && !esSel.size) FOUNDINGS.forEach(f => esSel.add(f));
  if (!scSel.size) esSel.clear();
  drawSchoolPicker();
};
function drawSchoolPicker() {
  const cells = LEVELS.map(lv => {
    const sel = lv.leaves.filter(k => scSel.has(k)).length;
    const cls = sel === lv.leaves.length ? " end" : sel ? " part" : "";
    const cnt = lv.leaves.reduce((a, k) => a + (IDX_GROUP_COUNT[k] || 0), 0);
    return `<button class="pk-cell sc-cell${cls}" onclick="scLevel('${lv.k}')">
      <span>${lv.label}</span><span class="sc-n">${cnt.toLocaleString()}개교</span></button>`;
  }).join("");

  // 고등학교를 골랐을 때만 유형 줄을 보여 준다
  const highOn = LEVELS[2].leaves.some(k => scSel.has(k));
  const typeRow = highOn ? `<div class="sc-subrow"><span class="sc-sublabel">고등학교 유형</span>` +
    HIGH_PARENTS.map(pk => {
      const p = PARENTS.find(x => x.k === pk), ls = leavesOf(pk);
      const sel = ls.filter(k => scSel.has(k)).length;
      const cnt = ls.reduce((a, k) => a + (IDX_GROUP_COUNT[k] || 0), 0);
      return `<button class="sc-chip${sel === ls.length ? " on" : sel ? " part" : ""}" onclick="scParent('${pk}')">${p.label} <span>${cnt.toLocaleString()}</span></button>`;
    }).join("") + `</div>` : "";
  // 특성화고·마이스터고, 특목고는 한 단계 더 나눌 수 있다
  // 고등학교를 통째로 고른 상태에서는 세부 줄까지 펼치면 어수선하다.
  // 유형을 좁힌 뒤에만 세부를 보여 준다.
  const allHigh = LEVELS[2].leaves.every(k => scSel.has(k));
  const subRows = highOn && !allHigh ? PARENTS.filter(p => HIGH_PARENTS.includes(p.k) && leavesOf(p.k).length > 1
      && leavesOf(p.k).some(k => scSel.has(k)))
    .map(p => `<div class="sc-subrow"><span class="sc-sublabel">${p.label} 세부</span>` +
      LEAVES.filter(l => l.parent === p.k).map(l =>
        `<button class="sc-chip${scSel.has(l.k) ? " on" : ""}" onclick="scToggle('${l.k}')">${l.label} <span>${(IDX_GROUP_COUNT[l.k] || 0).toLocaleString()}</span></button>`).join("") +
      `</div>`).join("") : "";

  // 특수·기타학교도 고등학교처럼 유형 줄을 보여 준다 — 성격이 아주 다른 학교가 한 덩어리에
  // 묶여 있어(특수학교·각종학교·평생학교·방송통신·고등기술) 나눠 보지 않으면 읽기 어렵다.
  const etcOn = LEVELS[3].leaves.some(k => scSel.has(k));
  const etcRow = etcOn ? `<div class="sc-subrow"><span class="sc-sublabel">특수·기타학교 유형</span>` +
    LEVELS[3].leaves.map(k =>
      `<button class="sc-chip${scSel.has(k) ? " on" : ""}" onclick="scToggle('${k}')">${leafLabel[k]} <span>${(IDX_GROUP_COUNT[k] || 0).toLocaleString()}</span></button>`).join("") +
    `</div>` : "";

  // 설립 숫자는 지금 고른 학교급 기준으로 센다 (예: 중학교만 골랐으면 중학교의 공·사·국립)
  const inSel = s => !scSel.size || scSel.has(idxGroup(s));
  const fCount = {};
  IDX.forEach(s => { if (inSel(s)) fCount[s.f] = (fCount[s.f] || 0) + 1; });
  const esRow = `<div class="sc-subrow"><span class="sc-sublabel">설립 주체</span>` +
    FOUNDINGS.map(f => `<button class="sc-chip${esSel.has(f) ? " on" : ""}" onclick="esToggle('${f}')">${f} <span>${(fCount[f] || 0).toLocaleString()}</span></button>`).join("") +
    `</div>`;

  const lvNames = LEVELS.filter(lv => lv.leaves.some(k => scSel.has(k)))
    .map(lv => lv.k === "high" && !lv.leaves.every(k => scSel.has(k))
      ? setParts(scSel).join("·") : lv.label);
  const esAll = esSel.size === FOUNDINGS.length;
  const picked = [lvNames.join(" · "), esSel.size && !esAll ? [...esSel].join("·") : ""]
    .filter(Boolean).join(" / ");
  document.getElementById("pickerRoot").innerHTML = `
    <div class="pk-overlay">
      <div class="pk-panel sc-panel" role="dialog" aria-label="학교 선택">
        <button class="pk-x" onclick="closePicker()" aria-label="닫기">✕</button>
        <div class="pk-top"><span></span>
          <div style="text-align:center"><div class="pk-title">학교 선택</div><div class="pk-range">${picked || "전체 (전국 모든 학교)"}</div></div>
        <span></span></div>
        <div class="sc-body">
          <div class="pk-grid sc-grid">${cells}</div>
          ${typeRow}${subRows}${etcRow}${esRow}
        </div>
        <div class="pk-foot">
          <span class="pk-hint">학교급을 누르면 그 안에서 설립 주체(국·공·사립)를 선택할 수 있습니다.
            <br>* 분류 기준: NEIS 학교유형·설립 구분</span>
          <span style="display:flex;gap:8px">
            <button class="pk-btn" onclick="scAll()">전체 학교</button>
            <button class="pk-btn" onclick="closePicker()">취소</button>
            <button class="pk-btn primary" onclick="scApply()" ${scSel.size || esSel.size ? "" : "disabled"}>적용</button>
          </span>
        </div>
      </div>
    </div>`;
}

function pkYearHTML(y) {
  let cells = "";
  for (let m = 1; m <= 12; m++) {
    const ym = y * 100 + m;
    const off = ym < YM_MIN || ym > YM_MAX;
    const isEnd = ym === pkS || ym === pkE;
    const inR = pkS !== null && pkE !== null && ym > pkS && ym < pkE;
    cells += `<button class="pk-cell${isEnd ? " end" : inR ? " inrange" : ""}" ${off ? "disabled" : `onclick="pkPick(${ym})"`}>${m}월</button>`;
  }
  return `<div class="pk-y"><div class="pk-yh">${y}년</div><div class="pk-grid">${cells}</div></div>`;
}
function drawPicker() {
  const rangeTxt = pkS === null ? "시작 월을 선택하세요"
    : pkE === null ? `${ymKo(pkS)} ~ <span style="color:var(--muted)">종료 월 선택</span>`
    : `${ymKo(pkS)} ~ ${ymKo(pkE)}`;
  document.getElementById("pickerRoot").innerHTML = `
    <div class="pk-overlay">
      <div class="pk-panel" role="dialog" aria-label="조사 기간 선택">
        <button class="pk-x" onclick="closePicker()" aria-label="닫기">✕</button>
        <div class="pk-top">
          <div style="text-align:center;width:100%"><div class="pk-title">조사 기간 선택</div><div class="pk-range">${rangeTxt}</div></div>
        </div>
        <!-- 화살표를 달력 양옆에 둔다. 머리말 줄에 두면 닫기(✕)와 겹친다.
             해가 넘어갈 때 달력 전체가 옆에서 밀려 들어와야 '넘어갔다'고 느낀다. -->
        <div class="pk-carousel">
          <button class="pk-nav" onclick="pkShift(-1)" ${pkBase <= 2020 ? "disabled" : ""} aria-label="이전 해">‹</button>
          <div class="pk-viewport"><div class="pk-years">${pkYearHTML(pkBase)}${pkYearHTML(pkBase + 1)}</div></div>
          <button class="pk-nav" onclick="pkShift(1)" ${pkBase >= 2025 ? "disabled" : ""} aria-label="다음 해">›</button>
        </div>
        <div class="pk-foot">
          <span class="pk-hint">시작 월과 종료 월을 차례로 선택하세요. 선택 가능 기간: ${Math.floor(YM_MIN / 100)}년 ${YM_MIN % 100}월 ~ ${Math.floor(YM_MAX / 100)}년 ${YM_MAX % 100}월</span>
          <span style="display:flex;gap:8px">
            <button class="pk-btn" onclick="closePicker()">취소</button>
            <button class="pk-btn primary" onclick="pkApply()" ${pkS === null ? "disabled" : ""}>적용</button>
          </span>
        </div>
      </div>
    </div>`;
}
function inPeriod(r) {
  const f = ymInt(PF), t = ymInt(PT);
  if (!f && !t) return true;
  if (r.ym) return (!f || r.ym >= f) && (!t || r.ym <= t);
  if (r.year) return (!f || r.year >= Math.floor(f / 100)) && (!t || r.year <= Math.floor(t / 100));
  return false;
}

// ---- 뷰 ----
// 제품군 태그 — 계약명에 제품이 안 적혀 '무엇인지 모른다'는 뜻이다.
// 이들이 제품과 같은 순위표에 섞이면 도입 1위처럼 보여 오해를 부른다.
const GENERIC_TAGS = new Set(["기기(PC·태블릿·전자칠판 등)", "SW·플랫폼(제품명 미상)", "SW·플랫폼",
  "인프라(교실·설비)", "로봇·교구·키트", "코스웨어(기타)", "코스웨어", "VR/XR 장비", "드론",
  "3D 프린팅/CAD", "운영 부대구매(제품 미상)", "운영 부대구매", "AI 면접시스템"]);
// 이름 표기 통일 — '(제품명 미상)·(기타)'는 '제품군' 딱지가 대신하므로 뺀다.
// 괄호는 예시를 들 때만 쓴다: 기기(PC·태블릿·전자칠판 등) · 인프라(교실·설비)
// data.js를 새로 만들면 정본(build_data.py) 이름이 이미 짧아져 이 표는 빈손으로 지나간다.
const TAG_RENAME = {"SW·플랫폼(제품명 미상)": "SW·플랫폼", "코스웨어(기타)": "코스웨어",
  "운영 부대구매(제품 미상)": "운영 부대구매"};
const tagName = t => TAG_RENAME[t] || t;
const hasProduct = r => r.tags.some(t => !GENERIC_TAGS.has(t));
// 제품군은 '제품군' 딱지를 앞에 붙이고 글자를 한 단계 흐리게 — 제품과 한눈에 구분된다
const tagLabel = t => GENERIC_TAGS.has(t)
  ? `<span class="gbadge" title="계약명에 제품 이름이 없어 제품군으로만 분류된 기록입니다">제품군</span><span class="gtag">${esc(tagName(t))}</span>`
  : esc(t);
let SCOPE = "product";                       // product = 제품 확인 기록만, all = 전체
function toggleTip(e) {
  e.preventDefault();
  const t = document.getElementById("inclTip");
  t.hidden = !t.hidden;
  if (!t.hidden) {
    const close = ev => {
      if (!ev.target.closest(".inclwrap")) { t.hidden = true; document.removeEventListener("click", close); }
    };
    setTimeout(() => document.addEventListener("click", close), 0);
  }
}

function setScope(v) {
  SCOPE = v;
  const box = document.getElementById("inclUnknown");
  if (box) box.checked = (v === "all");
  const y = window.scrollY;                  // 다시 그리면 맨 위로 튀므로 보던 자리를 지킨다
  render();
  window.scrollTo(0, y);
}

// 조사 기간·지역·계열 조건은 홈뿐 아니라 전체 목록 화면에서도 그대로 이어져야 한다
// 기록에 2020~2022년이 들어온 뒤로는 기본 기간도 실제로 걸러야 한다.
// 전에는 자료가 2023년부터라 '손대지 않았으면 R을 그대로' 돌려줘도 결과가 같았는데,
// 이제 그러면 기본 화면에 2020~2022년이 소리 없이 섞인다.
// 다만 첫 화면마다 28만 건을 훑으면 느려지므로 마지막 결과를 조건째로 기억해 둔다.
let _brKey = null, _brVal = null;
function baseRecs() {
  const key = `${PF}|${PT}|${[...SF].join(",")}|${[...RG].join(",")}|${[...ES].join(",")}`;
  if (key === _brKey) return _brVal;
  // PF가 빈 값이면 '2020년까지 통째로'라는 뜻이라 아래 기간 조건이 없다
  const anyF = PF !== "" || PT || SF.size || RG.size || ES.size;
  _brKey = key;
  _brVal = anyF ? R.filter(r => inPeriod(r) && sfMatch(r) && rgMatch(r) && esMatch(r)) : R;
  return _brVal;
}
function filterNote() {
  // 조사 기간은 조건이 없어도 늘 적는다 — 기본이 2026년부터라, 모르고 보면 그 학교·제품의
  // 전체 기록으로 읽힌다(2026-09-12).
  const ym = v => v.replace("-0", ".").replace("-", ".");     // 2026-01 → 2026.1
  const bits = [`조사 기간 ${ym(PF || "2020-01")} ~ ${ym(PT || YM_TO)}`];
  if (RG.size) bits.push(`지역 ${rgLabel()}`);
  if (SF.size) bits.push(`계열 ${sfLabel()}`);
  if (ES.size) bits.push(`설립 주체 ${esLabel()}`);
  // 기간이 걸려 있으면 넓히는 길을 바로 준다 — 기본이 2026년부터라, 모르고 보면 그 학교의
  // 전체 구매 기록으로 읽힌다(2026-09-12).
  // 기본 기간(2026.1~)일 때도 넓히는 길을 준다 — 조건을 periodOn()으로 걸었더니 정작 기본 화면에서
  // 링크가 안 보였다(2026-09-12). 이미 전 기간이면 다시 권하지 않는다.
  const wide = (PF === "" && !PT) ? ""
    : ` <a href="javascript:void(0)" onclick="showAllPeriod()">전 기간(2020.1~) 보기</a>`;
  return `<span class="fnote">${esc(bits.join(" · "))} <a href="/">홈에서 변경</a>${wide}</span>`;
}
// 전 기간으로 넓힌다 — 2020~2025년 기록은 따로 있어 그때 받아 온다
window.showAllPeriod = () => { PF = ""; PT = ""; PF_TOUCHED = true; withOld("", () => render()); };

function homeView() {
  const active = periodOn();
  const scActive = SF.size > 0 || ES.size > 0;
  const rgActive = RG.size > 0;
  const anyF = active || scActive || rgActive;
  const BASE = baseRecs().filter(r => !r.dup);
  // 전환에 따라 세 차트가 모두 같은 기준으로 움직인다
  const RF = SCOPE === "product" ? BASE.filter(hasProduct) : BASE;
  // 학교 선택 창이 초·중·고로 바뀌었으니 이 막대도 같은 층으로 보인다.
  // 고등학교는 눌러 들어가면 유형(일반고·특성화고·특목고·자율고)으로 나뉜다.
  const byType = count(RF, r => levelLabelOf(r));
  const bySido = count(RF, r => r.sido).slice(0, 12);
  const tagPairs = count(RF.flatMap(r => r.tags.map(t => [t])), x => x[0]);
  const tagNames = tagPairs.map(([t]) => t)
    .filter(t => SCOPE !== "product" || !GENERIC_TAGS.has(t));
  const topTags = tagNames.slice(0, 12)
    .map(t => [t, uniq(RF.filter(r => r.tags.includes(t)).map(skey)).length])
    .sort((a, b) => b[1] - a[1]);
  return `
    <div class="tiles">
      <div class="tile clickable" onclick="openRegionPicker()" role="button" aria-label="지역 선택">
        <div class="v">${rgLabel()}</div>
        <div class="l" style="margin-top:6px">지역 (시도교육청) <span class="hint">변경 ▾</span></div>
      </div>
      <div class="tile clickable" onclick="openSchoolPicker()" role="button" aria-label="학교 계열 선택">
        <div class="v" id="cntSchools" data-target="${sfIdxCount()}">${sfIdxCount().toLocaleString()}</div>
        <div class="l">검색 가능 학교 (${ES.size ? `${sfLabel()}·${esLabel()}` : sfLabel()}) <span class="hint">변경 ▾</span></div>
        <a class="tile-link" href="/schools" onclick="event.stopPropagation();event.preventDefault();go('/schools')">전체 보기 ›</a>
      </div>
      <div class="tile clickable" onclick="openPicker()" role="button" aria-label="조사 기간 변경">
        <!-- 칸에 적는 것은 지금 보고 있는 기간이다. 자료는 2020년까지 닿지만 기본은 2023년부터
             보여 주므로, 손대지 않았을 때 전체 범위를 적으면 없는 것을 보고 있다고 착각하게 된다. -->
        <div class="v">${active ? `${PF || "2020-01"} ~ ${PT || YM_TO}`.replaceAll("-", ".")
          : (DB.meta.basePeriod || DB.meta.coveragePeriod)}</div>
        <div class="l" style="margin-top:6px">조사 기간 <span class="hint">변경 ▾</span></div>
      </div>
    </div>
    ${anyF ? `<div class="fnote">
      <span>선택 조건 사례 ${RF.length.toLocaleString()}건${active ? " · 월 미상 기록은 연 단위로 포함" : ""}${SF.size ? ` · 계열: ${sfLabel()}` : ""}${ES.size ? ` · 설립 주체: ${esLabel()}` : ""}${rgActive ? ` · 지역: ${rgLabel()}` : ""}</span>
      ${active ? `<button onclick="clearPeriod()">기본 기간(2026년~)</button>` : ""}
      ${scActive ? `<button onclick="scAll()">전체 학교</button>` : ""}
      ${rgActive ? `<button onclick="rgAll()">전국</button>` : ""}
    </div>` : ""}
    <div class="section-div">통계 결과</div>
    <div class="grid2">
      <div class="card"><h2><a class="h2link" href="/products">${SCOPE === "product" ? "제품별" : "제품·제품군별"} 도입 학교 수</a><span class="note">막대를 눌러 학교 목록 보기</span></h2>${barChart(topTags, {drillFn: t => `/drill/tag/${encodeURIComponent(t)}`, labelFn: tagLabel})}</div>
      <div class="card"><h2>계열별 사례 수<span class="note">막대를 눌러 목록 보기</span></h2>${barChart(byType, {drillFn: t => `/drill/level/${encodeURIComponent(t)}`})}</div>
    </div>
    <div class="card"><h2><a class="h2link" href="/regions">지역별 사례 수</a><span class="note">막대를 눌러 목록 보기</span></h2>${barChart(bySido, {drillFn: t => `/drill/sido/${encodeURIComponent(t)}`})}</div>`;
}
// 학교 화면의 칩은 그 학교 기록을 걸러 준다 — 누를 때마다 켜고 끈다
// (전국 제품 화면으로 넘어가면 지금 보던 학교를 잃는다)
let SCHOOL_TAG = "";
window.setSchoolTag = t => { SCHOOL_TAG = (SCHOOL_TAG === t ? "" : t); PAGE = 1; const y = window.scrollY; render(); window.scrollTo(0, y); };

// 못 찾은 화면은 막다른 길이 된다 — 비슷한 이름을 권하고 돌아갈 길을 함께 준다
function notFound(what, name, cands, hrefOf) {
  const near = (cands || [])
    .map(c => [c, sim(String(name), String(c))])
    .filter(([, v]) => v >= 0.34)
    .sort((a, b) => b[1] - a[1]).slice(0, 6).map(([c]) => c);
  return `<div class="pagehead"><h2>${esc(what)}${eulReul(what)} 찾지 못했습니다</h2>
      <div class="meta">“${esc(name)}”에 해당하는 기록이 없습니다.
        철자가 다르거나, 조달 기록에 아직 없는 것일 수 있습니다.</div></div>
    ${near.length ? `<div class="card"><h2>혹시 이것을 찾으셨나요</h2>
      <div class="plist">${near.map(c => `<a href="${hrefOf(c)}">${esc(tagName(c))}</a>`).join("")}</div></div>` : ""}
    <div class="page"><p>검색창에 학교명이나 제품명을 넣어 보시거나,
      <a href="/products">제품 전체 보기</a> ·
      <a href="/vendors">공급 기업</a> ·
      <a href="/regions">지역별</a>에서 찾아보실 수 있습니다.</p>
      <p>있어야 할 기록이 없다면 <a href="/contact">정정 요청</a>으로 알려 주세요.</p></div>`;
}
// 받침이 있으면 '으로', 없거나 ㄹ이면 '로' (아이포트폴리오로 / 클래스카드로)
function euRo(w) {
  const c = (w || "").trim().slice(-1).charCodeAt(0);
  if (isNaN(c) || c < 0xac00 || c > 0xd7a3) return "로";
  const t = (c - 0xac00) % 28;
  return (t === 0 || t === 8) ? "로" : "으로";
}
// 받침이 있으면 '을', 없으면 '를' (학교를 / 제품을)
function eulReul(w) {
  const c = (w || "").trim().slice(-1).charCodeAt(0);
  if (isNaN(c) || c < 0xac00 || c > 0xd7a3) return "을";
  return (c - 0xac00) % 28 ? "을" : "를";
}
// 두 이름이 얼마나 겹치는지 — 글자 두 개씩 잘라 견준다(오타·띄어쓰기에 강하다)
function sim(a, b) {
  const bi = x => { const s = new Set(); const t = x.toLowerCase().replace(/\s/g, "");
    for (let i = 0; i < t.length - 1; i++) s.add(t.slice(i, i + 2)); return s; };
  const A = bi(a), B = bi(b);
  if (!A.size || !B.size) return 0;
  let n = 0; for (const x of A) if (B.has(x)) n++;
  return 2 * n / (A.size + B.size);
}

// 같은 이름의 학교가 전국에 여럿이다(2026-09-12: 665개 교명·1,509곳에 기록이 있다).
// 이름으로만 고르면 서울 동북초와 전북 동북초의 기록이 한 화면에 섞여 '기록 94건'이 된다.
// 학교코드를 알면 코드로 고르고, 모르면 어느 학교인지 먼저 고르게 한다.
function schoolView(name, code) {
  let all = code ? R.filter(r => r.schoolCode === code) : R.filter(r => r.school === name);
  if (!all.length) {
    // 옛 이름으로 들어온 경우 — 지금 교명의 화면을 보여 준다
    const old = R.find(r => r.origSchool === name);
    if (old) return schoolView(old.school);
    return notFound("학교", name, schools, c => `/school/${encodeURIComponent(c)}`);
  }
  if (!code) {
    const codes = uniq(all.filter(r => r.schoolCode).map(r => r.schoolCode));
    if (codes.length > 1) return sameNameView(name, codes);
  }
  const info = fillDetail([all[0]])[0];
  // 기록에 나온 순서대로 두면 기준이 없다 — 제품을 앞에, 제품군을 뒤에 두고
  // 그 안에서는 이 학교의 기록이 많은 것부터 보인다.
  const tagN = new Map();
  for (const r of all) for (const t of r.tags) tagN.set(t, (tagN.get(t) || 0) + 1);
  const schoolTags = [...tagN.keys()].sort((a, b) => {
    const ga = GENERIC_TAGS.has(a) ? 1 : 0, gb = GENERIC_TAGS.has(b) ? 1 : 0;
    return ga - gb || tagN.get(b) - tagN.get(a) || tagName(a).localeCompare(tagName(b), "ko");
  });
  // 개명 전 이름으로 계약된 기록 — 어느 이름으로 몇 건인지 밝힌다
  const oldNames = count(all.filter(r => r.origSchool), r => r.origSchool);
  if (SCHOOL_TAG && !schoolTags.includes(SCHOOL_TAG)) SCHOOL_TAG = "";
  const recs = SCHOOL_TAG ? all.filter(r => r.tags.includes(SCHOOL_TAG)) : all;
  return `
    <div class="crumb"><a href="/">홈</a> › 학교 상세</div>
    <div class="pagehead"><h2>${esc(name)}${info.schoolName && info.schoolName !== name ? ` <span style="font-size:14px;font-weight:400;color:var(--muted)">현재 교명: ${esc(info.schoolName)}</span>` : ""}</h2>
      <div class="meta">${esc(info.type)} · ${esc(info.region)} · 기록 ${all.length}건
        ${OLD_STATE === "done" ? "" : `<div class="conf"><a href="javascript:void(0)" onclick="showAllPeriod()">전 기간(2020.1~) 보기</a></div>`}
        ${info.schoolCode ? `<div class="conf">${[hsPhrase(info.type, info.hsType), info.founding, info.neisAddress].filter(Boolean).map(esc).join(" · ")}</div>` : `<div class="conf">학교 기본정보를 찾지 못했습니다 — 집합 항목이거나 교명 확인이 필요합니다</div>`}
        ${oldNames.length ? `<div class="conf">옛 이름 ${oldNames.map(([o, n]) => `${esc(o)}(${n}건)`).join(" · ")}으로 계약된 기록이 함께 있습니다</div>` : ""}
        <div>${schoolTags.map(t => `<button type="button" class="chip${GENERIC_TAGS.has(t) ? " gen" : ""}${SCHOOL_TAG === t ? " on" : ""}"
          onclick="setSchoolTag('${t.replace(/'/g, "\\'")}')"
          title="${SCHOOL_TAG === t ? "누르면 전체 기록으로 돌아갑니다" : "이 학교의 해당 기록만 봅니다"}">${tagLabel(t)}</button>`).join("")}</div>
      </div></div>
    ${SCHOOL_TAG ? `<div class="fnote"><span>${esc(tagName(SCHOOL_TAG))} 기록 ${recs.length}건만 보는 중</span>
      <a href="javascript:void(0)" onclick="setSchoolTag('${SCHOOL_TAG.replace(/'/g, "\\'")}')">전체 ${all.length}건 보기</a>
      <a href="/tag/${encodeURIComponent(SCHOOL_TAG)}">다른 학교의 도입 현황 ›</a></div>` : ""}
    <div class="card">${pagedTable(recs.slice().sort((a,b)=>(b.year||0)-(a.year||0)), {showSchool: false})}</div>`;
}
// 이름이 같은 학교가 여럿일 때 — 합치면 다른 학교 기록이 섞인다. 어느 학교인지 고르게 한다.
function sameNameView(name, codes) {
  const rows = codes.map(c => ({c, s: idxByCode.get(c),
    n: R.filter(r => r.schoolCode === c && !r.dup).length})).sort((x, y) => y.n - x.n);
  return `
    <div class="crumb"><a href="/">홈</a> › 학교 상세</div>
    <div class="pagehead"><h2>${esc(name)}</h2>
      <div class="sub2">이름이 같은 학교가 ${rows.length}곳입니다 — 어느 학교인지 고르세요</div></div>
    <div class="card"><div class="plist">${rows.map(({c, s, n}) =>
      `<a href="/code/${encodeURIComponent(c)}">${esc(name)}<span class="n">${
        esc(s ? [s.s, s.h || s.l, s.a].filter(Boolean).join(" · ") : "학교 정보 없음")} · ${n.toLocaleString()}건</span></a>`).join("")}</div></div>`;
}
// 교육청 등이 무상 보급하는 플랫폼 — 조달 기록에 나타나지 않아 공식 발표로 보완
const PLATFORM_NOTES = {
  "하이러닝": {
    body: "하이러닝(Hi-Learning)은 경기도교육청이 개발해 무상 운영하는 AI 교수학습 플랫폼입니다. 교육청 발표 기준 운영 1년 만에 관내 학교의 97%가 활용하고 있습니다(2024).",
    caveat: "무상 보급 플랫폼은 학교별 구매 기록이 없어 조달 기반인 본 서비스에는 활용 규모가 나타나지 않습니다. 아래 목록은 조달·공개자료에 잡힌 관련 계약과 사례만 보여줍니다.",
  },
  "바당": {
    body: "바당(BADANG)은 제주특별자치도교육청이 개발해 무상 운영하는 제주형 AI 교수학습 플랫폼입니다. 2026년 도내 전 학교로 수업·과제·평가 통합 플랫폼 활용을 확대하고 있습니다.",
    caveat: "무상 보급 플랫폼은 학교별 구매 기록이 없어 조달 기반인 본 서비스에는 활용 규모가 나타나지 않습니다. 아래 목록은 조달·공개자료에 잡힌 관련 계약과 사례만 보여줍니다.",
  },
  "교보문고 전자도서관": {
    body: "대구시교육청은 관내 학생·교직원·학부모가 쓰는 대구학생전자도서관(교보문고 소장형·구독형)을 운영합니다. "
      + "대구교육포털(에듀나비) 계정으로 로그인해 전자책을 빌려 볼 수 있습니다.",
    caveat: "교육청이 관내 전체에 제공하는 서비스라 학교별 구매 기록이 남지 않습니다. 아래 목록은 학교가 스스로 계약한 기록만 보여 줍니다.",
  },
  "KAIST 공동 AP": {
    body: "KAIST 공동 AP(대학과목선이수제) 학사관리시스템(apscience)은 과학기술특성화대 5개교와 과학고 20개교가 맺은 협약을 기반으로 공동 운영됩니다. 영재학교 8개교도 공동 AP 수강·성적을 온라인으로 관리합니다.",
    caveat: "협약 기반 공동 운영이라 학교별 구매 기록이 남지 않습니다. 따라서 아래 목록에는 개별 학교가 아니라 공동 운영 기록만 나타납니다. 실제 이용 학교는 협약에 참여한 과학고·영재학교 전체입니다.",
    schoolList: "spc_sci",
    schoolNote: "본 서비스가 과학계열 특목고·영재학교로 분류한 학교입니다. 협약 참여 명단은 각 학교·주관기관 공지를 확인하세요.",
  },
};

// 배너에 대상 학교 명단을 덧붙인다 (공동 운영이라 개별 기록이 없는 경우)
function noteSchoolList(note) {
  if (!note.schoolList) return "";
  const list = (DB.schoolIndex || []).filter(s => idxGroup(s) === note.schoolList)
    .map(s => s.n).sort((a, b) => a.localeCompare(b, "ko"));
  if (!list.length) return "";
  return `<details class="nlist"><summary>대상 학교 ${list.length}개교 보기</summary>
    <div class="nlist-in">${list.map(n =>
      `<a href="/school/${encodeURIComponent(n)}">${esc(n)}</a>`).join("")}</div>
    <p class="cv">${esc(note.schoolNote || "")}</p></details>`;
}
function tagView(tag) {
  // 제품 화면도 조사 기간·지역·계열·설립 조건을 따른다 — 첫 화면 숫자와 어긋나면 안 된다(2026-09-12).
  // 없는 제품인지 조건에 걸려 0건인지는 갈라 말한다.
  const everything = R.filter(r => r.tags.includes(tag));
  if (!everything.length) return notFound("제품", tagName(tag), tags.map(([t]) => t), c => `/tag/${encodeURIComponent(c)}`);
  const recs = baseRecs().filter(r => r.tags.includes(tag));
  const note = PLATFORM_NOTES[tag];
  const bySchoolType = count(recs, r => r.type);
  const bySido = count(recs, r => r.sido);
  return `
    <div class="crumb"><a href="/">홈</a> › ${GENERIC_TAGS.has(tag) ? "제품군" : "제품"} 상세</div>
    <div class="pagehead"><h2>${tagLabel(tag)}${originOf(tag) ? ` <span class="obadge">${originOf(tag)}</span>` : ""}</h2>
      <div class="meta">${note ? "조달 기록상 " : "도입 학교 "}${uniq(recs.filter(r=>!r.dup).map(skey)).length}개교 · 기록 ${recs.filter(r=>!r.dup).length}건</div>${filterNote()}</div>
    ${recs.length ? "" : `<div class="fnote"><span>지금 조건에 맞는 기록이 없습니다 — 전 기간에는 ${everything.filter(r=>!r.dup).length.toLocaleString()}건 있습니다</span>
      <a href="javascript:void(0)" onclick="openPicker()">조사 기간 넓히기</a></div>`}
    ${note ? `<div class="notice"><b>공식 보급 플랫폼 안내</b><p>${note.body}</p><p class="cv">${note.caveat}</p>${noteSchoolList(note)}</div>` : ""}
    <div class="grid2">
      <div class="card"><h2>계열별<span class="note">막대를 눌러 목록 보기</span></h2>${barChart(bySchoolType, {drillFn: t => `/drill2/tt/${encodeURIComponent(tag)}/${encodeURIComponent(t)}`})}</div>
      <div class="card"><h2>지역별<span class="note">막대를 눌러 목록 보기</span></h2>${barChart(bySido.slice(0,10), {drillFn: t => `/drill2/ts/${encodeURIComponent(tag)}/${encodeURIComponent(t)}`})}</div>
    </div>
    ${officeBuyCard(tag)}
    ${vendorsOfTag(recs)}
    <div class="card"><h2>도입 학교 ${VMODE === "map" ? "지도" : "목록"}</h2>${recsBlock(recs)}</div>`;
}

// 이 제품을 학교에 넣은 회사 — 계약 상대자를 그대로 세어 보여 준다(추론이 아니다).
// 온라인몰·조달 대행은 만든 곳이 아니므로 따로 적는다.
// 시도교육청이 직접 구매한 기록 — 학교 계약이 아니라 시도 단위다.
// AI 디지털 교육자료·다채움처럼 시도 전체에 한꺼번에 보급하는 제품은 학교에 계약이
// 남지 않아 이 서비스에서 통째로 안 보인다. 어느 학교가 쓰는지는 알 수 없으므로
// 학교 수·막대에 섞지 않고 따로 놓는다.
const OFFICE_BUY = DB.officeBuy || {};
function officeBuyCard(tag) {
  const rows = OFFICE_BUY[tag];
  if (!rows || !rows.length) return "";
  const sidos = uniq(rows.map(r => r.sido).filter(Boolean));
  const won = a => { const n = +a; return !n ? "" : n >= 1e8
    ? `${(n / 1e8).toFixed(1)}억원` : n >= 1e4 ? `${Math.round(n / 1e4).toLocaleString()}만원` : `${n.toLocaleString()}원`; };
  return `<div class="card"><h2>시도교육청이 직접 구매한 기록
      <span class="note">학교 계약이 아니라 시도 단위입니다 — 위 학교 수에는 들어 있지 않습니다</span></h2>
    <p class="cv" style="margin:0 0 10px">교육청이 관내 학교에 한꺼번에 보급한 것으로 보이는 계약입니다.
      계약명에 학교 이름이 없어 어느 학교가 쓰는지는 알 수 없습니다 ·
      ${rows.length.toLocaleString()}건${sidos.length ? ` · ${sidos.length}개 시도(${sidos.slice(0, 6).map(esc).join(" · ")}${sidos.length > 6 ? " 외" : ""})` : ""}</p>
    <div class="tablewrap"><table><thead><tr>
        <th>시도</th><th>계약명</th><th>시기</th><th>금액</th><th>업체</th>
      </tr></thead><tbody>
      ${rows.slice(0, 12).map(r => `<tr>
        <td style="white-space:nowrap">${esc(r.sido || "—")}</td>
        <td>${esc(r.n)}</td>
        <td class="conf" style="white-space:nowrap">${esc((r.d || "").replace("-", "."))}</td>
        <td class="conf" style="white-space:nowrap">${esc(won(r.amt))}</td>
        <td class="conf">${esc(r.by || "")}</td>
      </tr>`).join("")}
      </tbody></table></div>
    ${rows.length > 12 ? `<p class="cv" style="margin:10px 0 0">가장 최근 12건만 보여 줍니다 (전체 ${rows.length.toLocaleString()}건)</p>` : ""}
  </div>`;
}

function vendorsOfTag(recs) {
  const cnt = new Map();
  for (const r of recs.filter(x => !x.dup)) {
    const v = vkey(r.vendor);
    if (!v) continue;
    const e = cnt.get(v) || {n: 0, sch: new Set()};
    e.n++; e.sch.add(r.school); cnt.set(v, e);
  }
  if (!cnt.size) return "";
  const rows = [...cnt.entries()].map(([k, e]) => ({k, n: e.n, sch: e.sch.size, kind: vendorKind(k)}))
    .sort((a, b) => b.n - a.n);
  const sup = rows.filter(v => v.kind === "공급 기업").slice(0, 10);
  const etc = rows.filter(v => v.kind !== "공급 기업").slice(0, 5);
  const nameOf = k => (VENDORS.get(k) || {}).name || k;
  if (!sup.length && !etc.length) return "";
  return `<div class="card"><h2>납품한 회사<span class="note">계약에 적힌 상대자 기준</span></h2>
    ${sup.length ? `<div class="plist">${sup.map(v =>
      `<a href="/vendor/${encodeURIComponent(v.k)}">${esc(nameOf(v.k))}
        <span class="n">${v.n.toLocaleString()}건 · ${v.sch.toLocaleString()}개교</span></a>`).join("")}</div>` : ""}
    ${etc.length ? `<p class="sub2" style="margin-top:10px">구매 창구·제조사로 잡힌 곳:
      ${etc.map(v => `${esc(nameOf(v.k))} ${v.n.toLocaleString()}건`).join(" · ")}
      <br>이 업체가 만든 제품이라는 뜻은 아닙니다 — 학교가 그곳을 통해 샀다는 기록입니다</p>` : ""}
  </div>`;
}
function vendorView(key) {
  const e = VENDORS.get(key);
  const recs = vendorRecs(key);
  if (!recs.length) return notFound("공급 기업", key, [...VENDORS.values()].filter(v => v.n >= 5).map(v => v.name),
                                    c => `/vendor/${encodeURIComponent(vkey(c))}`);
  const nd = recs.filter(r => !r.dup);
  const kind = vendorKind(key);
  // 온라인몰·조달 대행·대형 제조사는 공급 기업이 아니다 — 화면을 만들지 않는다
  if (kind !== "공급 기업") return `
    <div class="crumb"><a href="/">홈</a> › <a href="/vendors">공급 기업</a></div>
    <div class="pagehead"><h2>${esc(e ? e.name : key)}</h2>
      <div class="meta">${kind}입니다 — 공급 기업으로 다루지 않습니다</div></div>
    <div class="page"><p class="lead">${kind === "구매 창구"
      ? "온라인몰·조달 대행처럼 여러 회사의 물건을 파는 창구입니다. 학교가 무엇을 샀는지는 기록에 남지만, 그 물건을 이 업체가 만든 것은 아니어서 공급 기업 통계에서 뺐습니다."
      : "여러 종류의 기기를 만드는 제조사입니다. 계약명에 제품이 적혀 있으면 그 제품으로 집계되므로, 제조사 단위로 묶어 보여 주지 않습니다."}</p>
      <p>기록은 <a href="/products">제품별</a>이나 학교 화면에서 그대로 보실 수 있습니다.</p></div>`;
  const byTag = count(nd.flatMap(r => r.tags.map(t => [t])), x => x[0]).slice(0, 12);
  const bySido = count(nd, r => r.sido).slice(0, 10);
  const byType = count(nd, r => { const g = recLeaf(r); return g ? parentLabel[parentOf[g]] : "기타·미분류"; });
  const won = a => a >= 100000000 ? `${(a / 100000000).toFixed(1)}억원` : `${Math.round(a / 10000).toLocaleString()}만원`;
  const amt = nd.reduce((a, r) => a + (r.amt || 0), 0);
  return `
    <div class="crumb"><a href="/">홈</a> › 공급 기업</div>
    <div class="pagehead"><h2>${esc(e ? e.name : key)}</h2>
      <div class="meta">${kind} · 거래 학교 ${uniq(nd.map(skey)).length.toLocaleString()}개교 ·
        기록 ${nd.length.toLocaleString()}건${amt ? ` · 계약금액 합계 ${won(amt)}` : ""}</div>
      ${kind !== "공급 기업" ? `<span class="fnote">여러 회사의 물건을 파는 창구입니다 —
        여기 묶인 기록이 이 업체가 만든 제품이라는 뜻은 아닙니다</span>` : ""}
    </div>
    <div class="grid2">
      <div class="card"><h2>계약에 나온 제품<span class="note">막대를 눌러 그 기록 보기</span></h2>
        <div class="conf" style="margin:-6px 0 10px">이 회사와 맺은 계약에 적힌 제품입니다 —
          한 계약에 여러 제품이 함께 적히기도 해서, 이 회사가 만든 제품이라는 뜻은 아닙니다</div>
        ${barChart(byTag, {drillFn: t => `/drill2/vt/${encodeURIComponent(key)}/${encodeURIComponent(t)}`, labelFn: tagLabel})}</div>
      <div class="card"><h2>계열별<span class="note">이 업체와 거래한 학교</span></h2>
        ${barChart(byType, {drillFn: t => `/drill2/vy/${encodeURIComponent(key)}/${encodeURIComponent(t)}`})}</div>
    </div>
    <div class="card"><h2>지역별<span class="note">막대를 눌러 목록 보기</span></h2>
      ${barChart(bySido, {drillFn: t => `/drill2/vs/${encodeURIComponent(key)}/${encodeURIComponent(t)}`})}</div>
    <div class="card"><h2>거래 ${VMODE === "map" ? "학교 지도" : "기록"}</h2>${recsBlock(recs)}</div>`;
}

function vendorsView() {
  // 온라인몰·조달 대행·대형 제조사는 공급사가 아니라 사는 창구라 목록에서 뺀다
  const all = [...VENDORS.values()].filter(v => v.n >= 5).map(v => ({...v, kind: vendorKind(v.key)}));
  const rows = all.filter(v => v.kind === "공급 기업").sort((a, b) => b.n - a.n);
  const dropped = all.length - rows.length;
  const shown = rows;
  return `
    <div class="crumb"><a href="/">홈</a> › 공급 기업 전체</div>
    ${allSwitch("/vendors")}
    <div class="pagehead"><h2>공급 기업</h2>
      <div class="sub2">계약 상대자로 5건 이상 나온 ${rows.length.toLocaleString()}곳 ·
        이름을 누르면 그 회사가 어느 학교에 무엇을 팔았는지 볼 수 있습니다<br>
        온라인몰·조달 대행·대형 제조사 ${dropped.toLocaleString()}곳은 제품을 만든 곳이 아니라
        사는 창구여서 뺐습니다</div></div>

    <div class="plist">
      ${shown.slice(0, 400).map(v => `<a href="/vendor/${encodeURIComponent(v.key)}">${esc(v.name)}
        <span class="n">${v.n.toLocaleString()}건</span></a>`).join("")}
    </div>
    ${shown.length > 400 ? `<p class="sub2" style="margin-top:12px">기록이 많은 400곳만 보여 줍니다 — 나머지는 검색으로 찾을 수 있습니다</p>` : ""}`;
}

function drillTagView(kind, tag, value) {
  // 회사 화면의 막대 — 그 회사가 그 제품(지역·계열)으로 판 기록만 보여 준다.
  // 제품 화면으로 보내면 전국 것이 다 나와 '이 회사가 무엇을 팔았나'를 잃는다.
  if (kind === "vt" || kind === "vs" || kind === "vy") {
    const e = VENDORS.get(tag);
    const nm = e ? e.name : tag;
    const recs = vendorRecs(tag).filter(r =>
      kind === "vt" ? r.tags.includes(value)
      : kind === "vs" ? r.sido === value
      : (r => { const g = recLeaf(r); return (g ? parentLabel[parentOf[g]] : "기타·미분류") === value; })(r));
    if (!recs.length) return `<div class="empty">해당 기록이 없습니다</div>`;
    const nd = recs.filter(r => !r.dup);
    return `
      <div class="crumb"><a href="/">홈</a> › <a href="/vendors">공급 기업</a> ›
        <a href="/vendor/${encodeURIComponent(tag)}">${esc(nm)}</a> ›
        ${kind === "vt" ? "제품" : kind === "vs" ? "지역" : "계열"} 상세</div>
      <div class="pagehead"><h2>${esc(nm)} · ${kind === "vt" ? tagLabel(value) : esc(value)}</h2>
        <div class="meta">이 회사가 납품한 기록만 봅니다 ·
          학교 ${uniq(nd.map(skey)).length.toLocaleString()}개교 · 기록 ${nd.length.toLocaleString()}건
          ${kind === "vt" ? `<div class="conf"><a href="/tag/${encodeURIComponent(value)}">${esc(tagName(value))} 전체 보기(다른 회사 포함) ›</a></div>` : ""}
        </div></div>
      <div class="card">${recsBlock(recs)}</div>`;
  }
  const recs = baseRecs().filter(r => r.tags.includes(tag) && (kind === "tt" ? r.type === value : r.sido === value));
  if (!recs.length) return `<div class="empty">해당 기록이 없습니다</div>`;
  const nSchools = uniq(recs.filter(r => !r.dup).map(skey)).length;
  return `
    <div class="crumb"><a href="/">홈</a> › <a href="/tag/${encodeURIComponent(tag)}">${esc(tagName(tag))}</a> › ${kind === "tt" ? "계열" : "지역"} 상세</div>
    <div class="pagehead"><h2>${tagLabel(tag)} · ${esc(value)}</h2>
      <div class="meta">학교 ${nSchools}개교 · 기록 ${recs.length}건</div></div>
    ${kind === "level" && value === "고등학교" ? `<div class="card"><h2>고등학교 유형별<span class="note">막대를 눌러 목록 보기</span></h2>
      ${barChart(count(recs, r => { const g = recLeaf(r); return g ? parentLabel[parentOf[g]] : "기타·미분류"; }),
                 {drillFn: t => `/drill/group/${encodeURIComponent(t)}`})}</div>` : ""}
    <div class="card">${recsBlock(recs)}</div>`;
}
function codeView(code) {
  const s = idxByCode.get(code);
  if (!s) return notFound("학교", code, schools, c => `/school/${encodeURIComponent(c)}`);
  const recs = R.filter(r => r.schoolCode === code);
  if (recs.length) {
    const names = uniq(recs.map(r => r.school));
    return schoolView(names[0], code);
  }
  return `
    <div class="crumb"><a href="/">홈</a> › 학교 상세</div>
    <div class="pagehead"><h2>${esc(s.n)}</h2>
      <div class="meta">${esc(s.l)}${hsPhrase(s.l, s.h) ? " · " + esc(hsPhrase(s.l, s.h)) : ""} · ${esc(s.s)}
        <div class="conf">NEIS ${[s.f, s.a, "학교코드 " + s.c].filter(Boolean).map(esc).join(" · ")}</div>
      </div></div>
    <div class="card"><div class="empty">아직 수집된 에듀테크 활용 기록이 없습니다.<br>
      <span style="font-size:12.5px">본 서비스는 공개 조달 기록 기반의 <b>하한 추정치</b>입니다 — 기록이 없다는 것이 에듀테크를 사용하지 않는다는 뜻은 아닙니다.</span></div></div>`;
}
function drillView(kind, value) {
  // 막대에서 들어온 화면이므로 막대와 같은 기준(미확인 제품 포함 여부)을 써야 숫자가 어긋나지 않는다
  const base = SCOPE === "product" ? baseRecs().filter(hasProduct) : baseRecs();
  let recs, what;
  if (kind === "tag") { recs = base.filter(r => r.tags.includes(value)); what = tagLabel(value); }
  else if (kind === "group") { recs = base.filter(r => { const g = recLeaf(r); return (g ? parentLabel[parentOf[g]] : "기타·미분류") === value; }); what = `${esc(value)} 계열`; }
  else if (kind === "level") { recs = base.filter(r => levelLabelOf(r) === value); what = `${esc(value)}`; }
  else if (kind === "sido") { recs = base.filter(r => r.sido === value); what = `${esc(value)} 지역`; }
  else return `<div class="empty">알 수 없는 조건입니다</div>`;
  const nd = recs.filter(r => !r.dup);
  const nSchools = uniq(nd.map(skey)).length;
  const conds = [];
  if (periodOn()) conds.push(`기간 ${(PF || "2020-01").replace("-", ".")} ~ ${(PT || YM_TO).replace("-", ".")}`);
  if (SF.size) conds.push(`계열 ${sfLabel()}`);
  if (ES.size) conds.push(`설립 주체 ${esLabel()}`);
  if (RG.size) conds.push(`지역 ${rgLabel()}`);
  return `
    <div class="crumb"><a href="/">홈</a> › 통계 상세</div>
    <div class="pagehead"><h2>${what}</h2>
      <div class="meta">${conds.length ? "적용 조건: " + esc(conds.join(" · ")) + " · " : ""}학교 ${nSchools}개교 · 기록 ${nd.length.toLocaleString()}건</div></div>
    <div class="card">${recsBlock(recs)}</div>`;
}
// 한·영 표기 동의어 그룹 — 검색어를 모든 표기로 확장
const ALIAS_GROUPS = [
  ["chatgpt", "챗gpt", "챗지피티", "쳇gpt"],
  ["adobe", "어도비"], ["photoshop", "포토샵"], ["illustrator", "일러스트레이터"],
  ["claude", "클로드"], ["gemini", "제미나이", "제미니"], ["copilot", "코파일럿"],
  ["microsoft", "마이크로소프트"], ["office", "오피스"], ["zoom", "줌"],
  ["notion", "노션"], ["padlet", "패들렛"], ["canva", "캔바"],
  ["goorm", "구름"], ["replit", "리플릿"], ["copykiller", "카피킬러"],
  ["google", "구글"], ["classroom", "클래스룸"], ["workspace", "워크스페이스"],
  ["suno", "수노"], ["aidt", "디지털교과서", "디지털 교육자료"],
  ["google ai pro", "구글 ai pro", "구글ai pro", "gemini advanced", "제미나이 어드밴스드"],
  ["하이러닝", "hi-learning", "hilearning"], ["니어팟", "nearpod"], ["젭", "zep"],
  ["아이스크림", "i-scream", "iscream"], ["커서", "cursor"], ["엘리스", "elice"], ["클래스팅", "classting"],
];
function queryTerms(q) {
  const terms = new Set([q]);
  for (const g of ALIAS_GROUPS) {
    for (const m of g) {
      if (q.includes(m)) g.forEach(o => { if (o !== m) terms.add(q.replace(m, o)); });
    }
  }
  return [...terms];
}
// 비고 표시 — 자동수집 상투 문구는 감추고 사람이 남긴 설명만 보여준다
const NOTE_BOILER = /^(파일럿 자동수집분|S2B 자동수집분|교육청 계약정보공개 자동수집분|결제 수수료)/;
// 신뢰도는 줄마다 '중'이라고만 적혀 아무것도 가르지 못했다(99.7%가 중). 조달 기록
// 그대로라는 뜻인데 그건 출처 칸이 이미 말한다. 조심해서 볼 것만 적는다 —
// '하'는 학교를 특정하지 못한 기록이다(전국 다수·커뮤니티 위키 출처).
function confNote(r) {
  const bits = [];
  if (r.confidence === "하") bits.push("학교를 특정하지 못한 기록");
  if (r.dup) bits.push("조달 기록과 동일 건(1건 집계)");
  if (r.feeOnly) bits.push("결제 수수료(제품 구매액 아님)");
  return bits.length ? `<div class="conf">${bits.map(esc).join(" · ")}</div>` : "";
}

function noteLine(r) {
  if (!r.note) return "";
  const parts = r.note.split(" · ").filter(s => s && !NOTE_BOILER.test(s.trim()));
  return parts.length ? `<div class="conf note-x">${esc(parts.join(" · "))}</div>` : "";
}

// 훑을 곳 — 계약명·내용·제품 태그에 업체명까지 넣는다.
// (업체명이 빠져 있어 '퓨너스'처럼 회사 이름으로는 계약을 찾을 수 없었다)
// 칸 사이를 띄워 붙여 놓는다 — 붙이면 없던 낱말이 생긴다
const hayOf = r => [r.product, contentOf(r), r.tags.join(" "), r.vendor || ""].join(" ").toLowerCase();

// 한글 검색어가 다른 한글에 붙어 있으면 다른 낱말이다.
// ('러닝스파크'로 찾을 때 'AI로봇러닝스파크 교구'가 걸리던 것 — 수업 이름이 우연히 겹쳤을 뿐이다)
const WORD_RE = new Map();
function hasWord(hay, term) {
  if (!/^[가-힣]{3,}$/.test(term)) return hay.includes(term);
  let re = WORD_RE.get(term);
  if (!re) {
    re = new RegExp("(?<![가-힣])" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    WORD_RE.set(term, re);
  }
  return re.test(hay);
}

// 검색어를 통째로 먼저 찾고, 한 건도 없으면 낱말로 나눠 '모두 든' 기록을 찾는다.
// ('퓨너스 챗gpt'는 회사가 업체명 칸에, 제품이 태그에 있어 한 덩어리로는 영영 안 걸린다)
function searchHits(q) {
  // 제품명으로 검색한 경우에는 학교명에만 걸린 기록을 뺀다.
  // ('레고'로 검색하면 한겨'레고'등학교가 딸려 나오던 문제 — 학교명은 부분 일치로 훑기 때문)
  const allTags = new Set();
  for (const r of R) for (const t of r.tags) allTags.add(t.toLowerCase());
  const isProductTerm = t => [...allTags].some(g => g.includes(t));
  const match = (r, group) => {
    const body = hayOf(r);
    // 개명 전 이름으로 찾아도 걸리게 한다 (계약서에 적힌 이름은 옛 이름이다)
    const school = (r.school + " " + (r.origSchool || "")).toLowerCase();
    return group.some(t => hasWord(body, t) || (hasWord(school, t) && !isProductTerm(t)));
  };
  const terms = queryTerms(q);
  let hit = R.filter(r => match(r, terms));
  const words = q.split(/\s+/).filter(Boolean);
  if (!hit.length && words.length > 1) {
    const groups = words.map(queryTerms);
    hit = R.filter(r => groups.every(g => match(r, g)));
    if (hit.length) return {hit, terms, words, fixed: null};
  }
  if (hit.length) return {hit, terms, words: null, fixed: null};
  // 오타로 한 건도 못 찾았으면 가장 가까운 이름으로 고쳐서 다시 찾는다 (권하고 끝내지 않는다)
  // 어지간히 닮지 않으면 고치지 않는다 — '러닝스파크'를 '젠스파크'로 고쳐 놓으면
  // 없는 기록을 있는 것처럼 보여 주게 된다. 그런 것은 아래에서 후보로만 권한다.
  const cand = nearNames(q, 0.62)[0];
  if (cand) {
    const fixedTerms = queryTerms(cand[3].toLowerCase());
    const again = R.filter(r => match(r, fixedTerms));
    if (again.length) return {hit: again, terms, words: null, fixed: cand};
  }
  return {hit, terms, words: null, fixed: null};
}

// 오타로 한 건도 못 찾았을 때 기댈 이름 목록 — 제품·회사·학교
// ('아이포트톨리오'처럼 한 글자만 어긋나도 빈 화면만 보이던 것)
let NAME_POOL = null;
function namePool() {
  if (NAME_POOL) return NAME_POOL;
  NAME_POOL = [];
  // 네 번째 칸은 견주고 다시 찾을 때 쓰는 이름 — 회사는 법인 표기를 뺀 알맹이로 견준다
  // ('주식회사 아이포트폴리오'를 통째로 견주면 '아이포트톨리오'와 덜 닮아 보인다)
  const core = n => (n || "").replace(/\(주\)|주식회사|㈜|\(유\)|유한회사|유한책임회사|\(재\)|재단법인|\(사\)|사단법인/g, "").trim();
  for (const [t] of tags) NAME_POOL.push([tagName(t), `/tag/${encodeURIComponent(t)}`, "제품", tagName(t)]);
  for (const v of VENDORS.values()) if (v.n >= 3 && vendorKind(v.key) === "공급 기업")
    NAME_POOL.push([v.name, `/vendor/${encodeURIComponent(v.key)}`, "회사", core(v.name) || v.name]);
  for (const s of schools) NAME_POOL.push([s, `/school/${encodeURIComponent(s)}`, "학교", s]);
  // 기록이 없는 학교도 후보에 넣는다 — 이름을 정확히 넣어도 못 찾았다(2026-09-12 꿈타래학교).
  // 조달 기록이 없을 뿐 명단에는 있는 학교이므로, 학교 정보 화면으로 보낸다.
  const named = new Set(schools);
  for (const x of IDX) if (x.c && !named.has(x.n)) NAME_POOL.push([x.n, `/code/${x.c}`, "학교 · 기록 없음", x.n]);
  return NAME_POOL;
}
const nearNames = (q, min) => namePool().map(p => [p, sim(q, p[3])])
  .filter(([, v]) => v >= min).sort((a, b) => b[1] - a[1]).map(([p]) => p);

function nearMisses(q) {
  // 이름이 그대로 있는데 기록만 없을 때는, 비슷한 이름을 늘어놓지 않고 그 학교 하나만 보여 준다
  // (2026-09-12 꿈타래학교: 정확히 넣었는데 엉뚱한 학교들만 제안됐다).
  const norm = x => (x || "").replace(/\s+/g, "").toLowerCase();
  const exact = namePool().filter(([nm]) => norm(nm) === norm(q));
  if (exact.length) {
    return `<div class="card"><h2>찾으시는 ${exact[0][2].startsWith("학교") ? "학교" : "이름"}</h2>
      <div class="plist">${exact.slice(0, 4).map(([nm, href, kind]) =>
        `<a href="${href}">${esc(nm)}<span class="n">${esc(kind)}</span></a>`).join("")}</div>
      <p class="cv">${exact.some(([, , kind]) => kind.includes("기록 없음"))
        ? "명단에는 있지만 조달 기록이 아직 없습니다 — 무상 보급이거나 아직 계약이 공개되지 않았을 수 있습니다."
        : "이 이름으로는 지금 조건에 맞는 기록이 없습니다."}</p></div>`;
  }
  const near = nearNames(q, 0.4).slice(0, 6);
  if (!near.length) return "";
  return `<div class="card"><h2>혹시 이것을 찾으셨나요</h2>
    <div class="plist">${near.map(([nm, href, kind]) =>
      `<a href="${href}">${esc(nm)}<span class="n">${kind}</span></a>`).join("")}</div></div>`;
}

// 회사 이름으로 찾아도 회사 화면이 나와야 한다. 회사 화면은 진작 있었는데 검색이
// 그리로 보내 주지 않았다 — 오타로 못 찾았을 때만 '혹시 이것을' 목록에 끼워 넣고 있었다.
// 계약 상대자에 회사명이 적혀 있어 기록 자체는 걸리지만, 그 기록의 태그가 제품군뿐이면
// '제품 확인 기록만' 범위에서 통째로 걸러져 0건으로 보인다(전자칠판 납품이 그렇다).
const vcore = x => (x || "").replace(/\(주\)|주식회사|㈜|\(유\)|유한회사|유한책임회사|\(재\)|재단법인|\(사\)|사단법인/g, "")
  .replace(/\s+/g, "").toLowerCase();
function vendorHits(q) {
  const k = vcore(q);
  if (k.length < 2) return [];
  const out = [];
  for (const v of VENDORS.values()) {
    const n = vcore(v.name);
    // 찾는 말이 회사 이름 안에 들어 있을 때만 본다. 거꾸로도 보면 'ChatGPT'에 회사 'GPT'가
    // 딸려 나온다 — 이름이 짧을수록 아무 데나 걸린다.
    if (n === k || (k.length >= 3 && n.includes(k))) out.push(v);
  }
  return out.sort((a, b) => b.n - a.n).slice(0, 8);
}
function vendorHitCard(q) {
  const vs = vendorHits(q);
  if (!vs.length) return "";
  return `<div class="card"><h2>이 이름의 공급 기업<span class="note">누르면 그 회사의 납품 기록을 볼 수 있습니다</span></h2>
    <div class="plist">${vs.map(v => `<a href="/vendor/${encodeURIComponent(v.key)}">${esc(v.name)}<span class="n">${vendorKind(v.key)} · 기록 ${v.n.toLocaleString()}건</span></a>`).join("")}</div></div>`;
}

function searchView(q) {
  const {hit, terms, words, fixed} = searchHits(q.toLowerCase());
  const recs = SCOPE === "product" ? hit.filter(hasProduct) : hit;
  const hidden = hit.length - recs.length;
  // 무상 보급·공동 운영 플랫폼은 검색으로 들어와도 한계 고지가 보여야 한다
  const noteKey = Object.keys(PLATFORM_NOTES).find(k =>
    terms.some(t => k.toLowerCase().includes(t) || t.includes(k.toLowerCase())));
  const note = noteKey ? PLATFORM_NOTES[noteKey] : null;
  return `
    <div class="crumb"><a href="/">홈</a> › 검색 결과</div>
    <div class="pagehead"><h2>“${esc(q)}” 검색 결과</h2><div class="meta">${recs.length.toLocaleString()}건${
      OLD_STATE === "done" ? ` · <span class="conf">전 기간(${esc((DB_RAW.meta.coveragePeriod || "").replace(/ /g, ""))})에서 검색한 결과입니다</span>`
      : ` · <span class="conf">지난 기록을 불러오는 중입니다…</span>`}${fixed ? ` · <b>${esc(fixed[0])}</b>${euRo(fixed[0])} 고쳐 찾았습니다 · <a href="${fixed[1]}">${esc(fixed[0])} 페이지 보기 ›</a>` : words ? ` · 낱말을 나눠 찾았습니다 — ${words.map(esc).join(" · ")}를 모두 담은 기록` : terms.length > 1 ? ` · 유사 표기 포함: ${terms.filter(t => t !== q.toLowerCase()).map(esc).join(", ")}` : ""}${hidden ? ` · <a href="javascript:void(0)" onclick="document.getElementById('inclUnknown').click()">미확인 제품 ${hidden.toLocaleString()}건 더 보기</a>` : ""}</div></div>
    ${note ? `<div class="notice"><b>공식 보급 플랫폼 안내</b><p>${note.body}</p><p class="cv">${note.caveat}</p>${noteSchoolList(note)}
      <p class="cv"><a href="/tag/${encodeURIComponent(noteKey)}">${esc(tagName(noteKey))} 페이지 보기 ›</a></p></div>` : ""}
    ${vendorHitCard(q)}
    ${hit.length ? "" : nearMisses(q)}
    ${recs.length || !hidden ? `<div class="card">${recsBlock(recs)}</div>`
      : `<div class="card"><div class="empty">제품 이름이 확인된 기록은 없습니다 —
          제품군으로만 분류된 기록이 ${hidden.toLocaleString()}건 있습니다.<br>
          <a href="javascript:void(0)" onclick="document.getElementById('inclUnknown').click()">미확인 제품 포함</a>을 켜면 볼 수 있습니다.</div></div>`}`;
}

// ---- 숫자 카운트업 ----
function animateCount() {
  const el = document.getElementById("cntSchools");
  if (!el) return;
  const target = +el.dataset.target;
  const dur = 1500, t0 = performance.now();
  function tick(t) {
    const p = Math.min((t - t0) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(target * eased).toLocaleString();
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
  // 배경 탭에서는 requestAnimationFrame이 멈춰 숫자가 중간값(예: 1,253)에 붙어 버린다.
  // 애니메이션 시간이 지나면 최종값을 못 박는다.
  setTimeout(() => { el.textContent = target.toLocaleString(); }, dur + 200);
}

// ---- 라우팅 ----
function aboutView() {
  const m = DB.meta || {};
  // 숫자는 빌드가 센 값(meta)에서만 가져온다 — 손으로 적으면 자료가 바뀌어도 옛 값으로 남는다
  const n = (v, d) => (v == null ? d : v).toLocaleString();
  const exc = m.excluded || {"재외한국학교": 79, "외국인·국제학교": 33, "공동실습소": 9, "학교급 미기재": 2};
  const excSum = Object.values(exc).reduce((a, b) => a + b, 0);
  const mix = m.levelMix || {"초·중·고": 12078, "특수학교": 202, "각종학교": 116, "평생학교": 73,
                             "방송통신 중·고": 66, "고등기술·고등공민학교": 8};
  const mixText = ["특수학교", "각종학교", "평생학교", "방송통신 중·고", "고등기술·고등공민학교"]
    .filter(k => mix[k]).map(k => `${k} ${mix[k].toLocaleString()}개교`).join(", ");
  return `
    <div class="crumb"><a href="/">홈</a> › 데이터 안내</div>
    <div class="page">
      <div class="page-intro">
        <div>
          <h2>데이터 안내</h2>
          <p>이 서비스는 수집된 공개 조달 기록을 바탕으로 전국 초·중·고등학교의 에듀테크 도입 현황을 제공합니다.
          학교의 계약여부는 공개 정보이지만 여러 곳에 흩어져 있어 찾기 어렵기 때문에, 한곳에서 검색할 수 있게 정리했습니다.</p>
        </div>
        <img src="/hero_person_m.png?v=2" width="239" height="186" alt="">
      </div>

      <h3>어디에서 수집했나</h3>
      <div class="srcgrid">
        <div class="srccard"><b>나라장터</b><span>조달청 계약정보 공개 API — 학교가 맺은 물품·용역 계약</span></div>
        <div class="srccard"><b>S2B 학교장터</b><span>한국교직원공제회 운영 학교 조달 사이트 — 수의계약 전수 (입찰분 미포함) · 계약대상자(공급 업체)도 공개됩니다 — 우리 자료에는 아직 담기지 않아 다시 받고 있습니다</span></div>
        <div class="srccard"><b>시도교육청 계약공개</b><span>학교 수의계약 내역 — 소액 구매까지 포함 (${n(m.officeCount, 16)}개 시도교육청 · 전북은 아직 수집 전)</span></div>
        <div class="srccard"><b>나이스 교육정보 개방 포털</b><span>교육부 — 전국 학교 명단·소재지 · 등재 ${n(m.neisTotal, 12666)}개교 중 ${excSum.toLocaleString()}개교(재외한국학교·외국인/국제학교·공동실습소·학교급 미기재)를 빼고 ${n(m.idxCount, 12543)}개교를 싣습니다</span></div>
        <div class="srccard"><b>학교 위치(지도)</b><span>한국교육시설안전원 초중등학교 위치(2026.3 기준) 및 OpenStreetMap·주소 검색, OpenFreeMap 지도 활용</span></div>
        <div class="srccard"><b>언론 보도·공식 자료</b><span>학교 홈페이지, 교육청 발표, 보도자료 — ${n(m.mediaCount, 44)}건(${m.mediaPct == null ? "0.01" : m.mediaPct}%)</span></div>
      </div>

      <h3>어떻게 판단하나</h3>
      <p>계약명 원문에서 제품명을 찾아 태그를 붙입니다.</p>
      <ul>
        <li>회사가 단일 제품을 공급하거나 회사명이 제품명인 경우에는 계약명에 제품이 없어도 그 제품으로 판단하였습니다.</li>
        <li>한 회사가 여러 제품을 공급하는 경우, 계약명에 제품이 표시되지 않으면 <b>제품군</b>(코스웨어·기기·인프라·SW·플랫폼 등)으로만 남습니다. 이런 계약은 <b>회사명으로 검색</b>하면 함께 찾아볼 수 있습니다.</li>
        <li>교육·연수 운영, 행사·캠프, 차량 임차처럼 제품 도입이 아닌 계약은 집계에서 제외하였습니다.</li>
        <li>학교가 이름을 바꾼 경우 옛 이름으로 맺은 계약도 현재 학교명으로 표시됩니다. 계약명 원문은 그대로 보존됩니다.</li>
      </ul>

      <div class="example">
        <p class="ex-q"><b>예)</b> OO초등학교 · <span>“챗GPT 플러스 (ChatGPT Plus) 챗지피티4 3개월 구독 <b>외 3종</b>”</span></p>
        <ul>
          <li>이 계약에는 <b>ChatGPT</b> 태그 하나만 붙습니다.</li>
          <li>같은 제품이라도 표기가 서로 다른 경우가 있습니다(챗GPT · ChatGPT · 챗지피티). 어느 쪽으로 적혀 있든 <b>ChatGPT</b>로 태그를 설정하고, 한글로 검색하든 영문으로 검색하든 동일한 결과를 제공합니다.</li>
          <li><b>“외 3종”은 기록하지 않습니다.</b> 무엇을 함께 샀는지 계약명에 없어 확인할 수 없습니다.</li>
        </ul>
      </div>

      <h3>무엇이 빠지나</h3>
      <p>여기 실린 숫자는 <b>최소값</b>으로 보시는 것이 타당합니다. 기록이 없다는 것이 그 학교가 에듀테크를 쓰지 않는다는 뜻은 아닙니다.</p>
      <ul>
        <li>교육청이 무상으로 보급하는 플랫폼(하이러닝·바당 등)은 학교별 구매 기록이 남지 않습니다.</li>
        <li>해외 서비스 직접 결제, 교사 개인 결제, 소액 현장 구매는 조달 기록에 포함되지 않습니다. 다만 시도교육청 계약공개 자료를 수집한 지역에서는 일부 확인됩니다.</li>
        <li><b>“외 3종”처럼 묶어 적은 계약</b>은 함께 산 제품을 알 수 없습니다. 전체 계약의 <b>약 ${n(m.bundledPct, 10)}%</b>가 이런 형태이고, 그 안에 <b>${n(m.buriedProducts, 90653)}개</b>의 제품이 이름 없이 묶여 있어 확인되지 못하고 있습니다.</li>
        <li>시도교육청이 관내 학교에 <b>한꺼번에 보급한 제품</b>(AI 디지털교과서 등)은 계약명에 학교 이름이 없어 어느 학교가 쓰는지 알 수 없습니다. 제품 화면에 <b>시도교육청이 직접 구매한 기록</b>으로 따로 실었습니다.</li>
      </ul>

      <h3>수록 범위</h3>
      <ul>
        <li>조사 기간: <b>${esc(m.coveragePeriod || "2020.1 ~ 2026.7")}</b>
          ${m.basePeriod ? `— 첫 화면은 <b>${esc(m.basePeriod)}</b>만 제공됩니다.
          <b>조사 기간</b>에서 2020년 1월부터 선택할 수 있습니다.` : ""}</li>
        <li>수록 기록: <b>${(m.total || 0).toLocaleString()}건</b> · 기록 보유 학교: <b>${(m.schools || 0).toLocaleString()}개교</b> <span class="cv">(전 기간 기준 — 첫 화면 숫자는 조사 기간에 따라 달라집니다)</span></li>
        <li>검색 가능 학교: <b>${n(m.idxCount, 12543)}개교</b> — 국내 공교육 전체</li>
        <li>학교 명단은 교육부 NEIS 개방 포털 기준입니다. 초·중·고 ${n(mix["초·중·고"], 12078)}개교에 더해
          ${mixText}를 포함합니다.
          등재된 ${n(m.neisTotal, 12666)}개교 중 <b>재외한국학교 ${n(exc["재외한국학교"], 79)}개교, 외국인·국제학교 ${n(exc["외국인·국제학교"], 33)}개교</b>는 국내 공교육이 아니어서,
          <b>공동실습소 ${n(exc["공동실습소"], 9)}곳</b>은 학교가 아니어서, <b>학교급이 비어 있는 ${n(exc["학교급 미기재"], 2)}개교</b>는 분류할 수 없어 제외하였습니다.</li>
      </ul>

      <h3>기타</h3>
      <ul>
        <li><b>갱신 주기</b> — 매월 10일 새벽 3시에 자동으로 갱신됩니다.</li>
        <li><b>전남광주 통합</b> — 2026년 7월 1일 광주광역시와 전라남도가 「전남광주통합특별시」로 통합되면서 교육청도 같은 날
        <b>전남광주통합특별시교육청</b>으로 변경됐습니다
        (근거: <a href="https://www.law.go.kr/lsInfoP.do?lsiSeq=284111" target="_blank" rel="noopener">전남광주통합특별시 설치를 위한 특별법</a>,
        2026.3.5. 공포 · 2026.7.1. 시행).
          <span style="display:block; margin-top:6px">나이스(NEIS)와 학교 회계·계약을 다루는 <b>K-에듀파인</b> 등 주요 시스템은 2028년 완전 통합을 목표로
        단계적으로 개편되므로
        (<a href="https://www.newspim.com/news/view/20260630000332" target="_blank" rel="noopener">뉴스핌 2026.6.30.</a>),
        정보시스템은 당분간 전남과 광주 체계를 그대로 유지합니다.</span></li>
        <li><b>정정 요청</b> — 정보수집 작업의 특성상 실제 발생한 모든 계약을 싣지 못할 수 있습니다.
        시스템에서 누락되거나 기타 이유 등으로 수록되지 못할 수 있으니
        <b>추가·삭제·정정</b> 등 모든 요청을 주시면 본 서비스의 품질을 더 높일 수 있습니다.
        <a href="/contact">정정 요청</a>으로 알려 주세요.</li>
      </ul>
    </div>`;
}

let VLIST_KIND = "";                    // 공급 기업 목록에서 고른 갈래
// 제품 국적 — build_data.py가 product_origin.csv를 실어 보낸다 (근거는 그 파일에 남아 있다)
const ORIGIN = DB_RAW.origin || {};
const originOf = t => ORIGIN[t] || "";
let PORIGIN = "";                       // "" 전체 · 국내 · 해외
window.setPOrigin = v => { PORIGIN = v; const y = window.scrollY; render(); window.scrollTo(0, y); };
let SSORT = "count", SLIST_G = "", SPAGE = 1;   // 학교 전체 보기: 정렬·첫 글자·쪽
let PSORT = "count";                    // count = 도입 학교 순(순위표), name = 가나다순
function setPSort(v) { PSORT = v; const y = window.scrollY; render(); window.scrollTo(0, y); }

// 학교 전체 보기 — 첫 화면 '검색 가능 학교' 칸의 숫자를 그대로 펼친 목록.
// 기록 수는 지금 고른 기간·지역·계열을 따른다(다른 화면과 같게).
// 1만 곳이 넘으므로 한 번에 300곳씩 보여 준다.
const SCH_PAGE = 300;
function choGroup(name) {
  const c0 = name[0] || "", code = name.charCodeAt(0);
  if (/[A-Za-z]/.test(c0)) return "A–Z";
  if (/[0-9]/.test(c0)) return "0–9";
  if (code < 0xac00 || code > 0xd7a3) return "기타";
  const c = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"][Math.floor((code - 0xac00) / 588)];
  return { "ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ" }[c] || c;
}
function schoolsView() {
  const list = IDX.filter(idxPass);
  const src = SCOPE === "product" ? baseRecs().filter(hasProduct) : baseRecs();
  const cnt = {};
  for (const r of src) if (r.schoolCode) cnt[r.schoolCode] = (cnt[r.schoolCode] || 0) + 1;
  const n = x => cnt[x.c] || 0;
  const withRec = list.filter(x => n(x) > 0).length;
  const sorted = list.slice().sort(SSORT === "count"
    ? (a, b) => n(b) - n(a) || a.n.localeCompare(b.n, "ko")
    : (a, b) => a.n.localeCompare(b.n, "ko"));
  const groups = {};
  for (const x of sorted) (groups[choGroup(x.n)] = groups[choGroup(x.n)] || []).push(x);
  const order = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ","A–Z","0–9","기타"].filter(g => groups[g]);
  const sel = SLIST_G && groups[SLIST_G] ? SLIST_G : "전체";
  const show = sel === "전체" ? sorted : groups[sel];
  const pages = Math.max(1, Math.ceil(show.length / SCH_PAGE));
  const page = Math.min(Math.max(1, SPAGE), pages);
  const slice = show.slice((page - 1) * SCH_PAGE, page * SCH_PAGE);
  const item = x => {
    const k = n(x);
    // 기록이 있는 학교는 기록 화면으로, 없는 학교는 학교 정보 화면으로
    // 학교코드가 곧 그 학교다 — 이름으로 보내면 동명 학교의 기록이 섞인다
    const href = x.c ? `/code/${encodeURIComponent(x.c)}` : `/school/${encodeURIComponent(x.n)}`;
    return `<a href="${href}"${k ? "" : ' class="dim"'}>${esc(x.n)}<span class="n">${esc(x.s)} · ${esc(x.h || x.l || "")} · ${k ? k.toLocaleString() + "건" : "기록 없음"}</span></a>`;
  };
  const pager = pages > 1 ? `<div class="alpha pager">
      <button ${page <= 1 ? "disabled" : ""} onclick="SPAGE=${page - 1};render()">‹ 이전</button>
      <span class="alab">${page} / ${pages}쪽 · ${((page - 1) * SCH_PAGE + 1).toLocaleString()}–${Math.min(page * SCH_PAGE, show.length).toLocaleString()}번째</span>
      <button ${page >= pages ? "disabled" : ""} onclick="SPAGE=${page + 1};render()">다음 ›</button>
    </div>` : "";
  return `
    <div class="crumb"><a href="/">홈</a> › 학교 전체 보기</div>
    ${allSwitch("/schools")}
    <div class="pagehead"><h2>학교 전체 보기</h2>
      <div class="sub2">학교 ${list.length.toLocaleString()}곳 · 그중 기록이 있는 곳 ${withRec.toLocaleString()}곳 ·
        이름을 누르면 그 학교의 기록을 볼 수 있습니다</div>${filterNote()}</div>
    ${VMODE === "map" ? `<div class="alpha">${modeToggle()}</div>` + mapBox({items: list.map(x => ({s: x, k: n(x)})), lost: 0, unit: "idx", recs: src}) : `
    <div class="alpha">${modeToggle()}<span class="alpha-gap"></span>
      <span class="alab">정렬</span>
      <button class="${SSORT === "count" ? "on" : ""}" onclick="SSORT='count';SPAGE=1;render()">기록 많은 순</button>
      <button class="${SSORT === "name" ? "on" : ""}" onclick="SSORT='name';SPAGE=1;render()">가나다순</button>
      <span class="alpha-gap"></span>
      <span class="alab">첫 글자</span>
      <button class="${sel === "전체" ? "on" : ""}" onclick="SLIST_G='';SPAGE=1;render()">전체</button>
      ${order.map(g => `<button class="${sel === g ? "on" : ""}" onclick="SLIST_G='${g}';SPAGE=1;render()">${g}</button>`).join("")}
    </div>
    <div class="plist">${slice.map(item).join("")}</div>
    ${pager}`}`;
}

// 전체 목록 네 가지를 화면 안에서 오간다 — 메뉴를 열고 고르는 대신 바로 들어가 옮겨 다닌다.
// 지역별은 첫 화면에 이미 있고 화면도 비슷해 여기 두지 않는다.
const ALL_LISTS = [["/records", "기록"], ["/schools", "학교"], ["/products", "제품"], ["/vendors", "공급 기업"]];
function allSwitch(cur) {
  return `<div class="allsw">${ALL_LISTS.map(([href, label]) =>
    `<a href="${href}"${href === cur ? ' class="on" aria-current="page"' : ""}>${label} 전체 보기</a>`).join("")}</div>`;
}
// 가진 기록을 한 화면에서 훑는다 — 제품·학교를 거치지 않고 바로 본다.
// 조사 기간·지역·계열 조건을 그대로 따르므로 첫 화면 숫자와 이어진다.
function recordsView() {
  const recs = SCOPE === "product" ? baseRecs().filter(hasProduct) : baseRecs();
  const nd = recs.filter(r => !r.dup);
  // 기록에 나온 학교를 센다. 그중에는 전국 학교 명단에 없는 곳도 있다 — 옛 이름으로 계약했거나
  // 학교코드가 없는 기록, 집합 항목 등이다. 학교 전체 보기(명단 기준)와 숫자가 다른 이유라 밝혀 둔다.
  const sKeys = uniq(nd.map(skey));
  const outside = sKeys.filter(k => !idxByCode.has(k)).length;
  return `
    <div class="crumb"><a href="/">홈</a> › 기록 전체 보기</div>
    ${allSwitch("/records")}
    <div class="pagehead"><h2>기록 전체 보기</h2>
      <div class="sub2">${SCOPE === "product" ? "제품이 확인된 기록" : "전체 기록"} ${nd.length.toLocaleString()}건 ·
        학교 ${sKeys.length.toLocaleString()}개교${outside ? `(전국 학교 명단에 없는 ${outside.toLocaleString()}곳 포함)` : ""} ·
        조사 기간과 지역·계열 조건을 그대로 따릅니다</div>${filterNote()}</div>
    <div class="card">${recsBlock(recs)}</div>`;
}
function productsView() {
  const cnt = {}, sch = {};
  const src = SCOPE === "product" ? baseRecs().filter(hasProduct) : baseRecs();
  for (const r of src) for (const t of r.tags) {
    if (SCOPE === "product" && GENERIC_TAGS.has(t)) continue;
    cnt[t] = (cnt[t] || 0) + 1;
    (sch[t] = sch[t] || new Set()).add(skey(r));
  }
  if (PORIGIN) for (const k of Object.keys(cnt)) if (originOf(k) !== PORIGIN) { delete cnt[k]; delete sch[k]; }
  const names = Object.keys(cnt).sort(PSORT === "count"
    ? (a, b) => sch[b].size - sch[a].size || a.localeCompare(b, "ko")
    : (a, b) => a.localeCompare(b, "ko"));
  const initial = s => {
    const c = s[0];
    if (/[A-Za-z]/.test(c)) return "A–Z";
    if (/[0-9]/.test(c)) return "0–9";
    const code = c.charCodeAt(0);
    if (code < 0xac00 || code > 0xd7a3) return "기타";
    return "가나다라마바사아자차카타파하"[Math.floor((code - 0xac00) / 588 * 19 / 19)] ||
      ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"][Math.floor((code - 0xac00) / 588)];
  };
  const CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"];
  const groupOf = s => {
    const code = s.charCodeAt(0);
    if (/[A-Za-z]/.test(s[0])) return "A–Z";
    if (/[0-9]/.test(s[0])) return "0–9";
    if (code < 0xac00 || code > 0xd7a3) return "기타";
    const c = CHO[Math.floor((code - 0xac00) / 588)];
    return { "ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ" }[c] || c;
  };
  const groups = {};
  for (const n of names) (groups[groupOf(n)] = groups[groupOf(n)] || []).push(n);
  const order = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ","A–Z","0–9","기타"].filter(g => groups[g]);
  const sel = PLIST_G && groups[PLIST_G] ? PLIST_G : "전체";
  const show = sel === "전체" ? names : groups[sel];
  return `
    <div class="crumb"><a href="/">홈</a> › 제품 전체 보기</div>
    ${allSwitch("/products")}
    <div class="pagehead"><h2>제품 전체 보기</h2>
      <div class="sub2">조달 기록에서 확인된 ${SCOPE === "product" ? "제품" : "제품·제품군"} ${names.length}종 ·
        이름을 누르면 도입 학교를 볼 수 있습니다</div>${filterNote()}</div>
    <div class="alpha">
      <span class="alab">정렬</span>
      <button class="${PSORT === "count" ? "on" : ""}" onclick="setPSort('count')">도입 학교 순</button>
      <button class="${PSORT === "name" ? "on" : ""}" onclick="setPSort('name')">가나다순</button>
      <span class="alpha-gap"></span>
      <span class="alab">국적</span>
      <button class="${PORIGIN === "" ? "on" : ""}" onclick="setPOrigin('')">전체</button>
      <button class="${PORIGIN === "국내" ? "on" : ""}" onclick="setPOrigin('국내')">국내</button>
      <button class="${PORIGIN === "해외" ? "on" : ""}" onclick="setPOrigin('해외')">해외</button>
      <span class="alpha-gap"></span>
      <span class="alab">첫 글자</span>
      <button class="${sel === "전체" ? "on" : ""}" onclick="PLIST_G='';render()">전체</button>
      ${order.map(g => `<button class="${sel === g ? "on" : ""}" onclick="PLIST_G='${g}';render()">${g}</button>`).join("")}
    </div>
    <div class="plist">
      ${show.map(n => `<a href="/tag/${encodeURIComponent(n)}">${tagLabel(n)}<span class="n">${sch[n].size.toLocaleString()}개교</span></a>`).join("")}
    </div>`;
}

function regionsView() {
  const src = SCOPE === "product" ? baseRecs().filter(hasProduct) : baseRecs();
  const all = count(src.filter(r => !r.dup), r => r.sido);
  // '미상'·'전국(공동)'·'비공개'처럼 시도가 아닌 항목은 목록 아래에 따로 적는다
  const isSido = s => SIDOS.includes(s);
  const rows = all.filter(([s]) => isSido(s));
  const etc = all.filter(([s]) => !isSido(s));
  const sch = {};
  for (const r of src) (sch[r.sido] = sch[r.sido] || new Set()).add(skey(r));
  return `
    <div class="crumb"><a href="/">홈</a> › 지역별 전체</div>
    <div class="pagehead"><h2>지역별 사례 수</h2>
      <div class="sub2">전국 ${rows.length}개 시도 ·
        ${SCOPE === "product" ? "제품이 확인된 기록" : "전체 기록"} 기준 · 막대를 눌러 목록을 볼 수 있습니다</div>${filterNote()}</div>
    <div class="card">${barChart(rows, {drillFn: t => `/drill/sido/${encodeURIComponent(t)}`})}</div>
    <div class="plist" style="margin-top:14px">
      ${rows.map(([s, n]) => `<a href="/drill/sido/${encodeURIComponent(s)}">${esc(s)}
        <span class="n">${n.toLocaleString()}건 · ${(sch[s] ? sch[s].size : 0).toLocaleString()}개교</span></a>`).join("")}
    </div>
    ${etc.length ? `<p class="sub2" style="margin-top:14px">시도를 특정하지 못한 기록:
      ${etc.map(([s, n]) => `<a href="/drill/sido/${encodeURIComponent(s)}">${esc(s)} ${n.toLocaleString()}건</a>`).join(" · ")}</p>` : ""}`;
}

function contactView() {
  const subj = encodeURIComponent("[공교육 에듀테크 활용 현황] 정정 요청");
  const body = encodeURIComponent(
    "아래 항목을 채워 보내주시면 확인 후 반영하겠습니다.\n\n" +
    "1. 학교명:\n2. 해당 기록(제품명 또는 계약명):\n3. 어떤 점이 잘못되었나요:\n4. 올바른 내용:\n5. 근거 자료(있으면):\n6. 회신받을 연락처:\n");
  // 기업은 물어볼 것이 다르다 — 회사·제품이 먼저 오고, 아예 빠진 기록도 함께 받는다
  const subjCo = encodeURIComponent("[공교육 에듀테크 활용 현황] 정정 요청 (공급 기업)");
  const bodyCo = encodeURIComponent(
    "아래 항목을 채워 보내주시면 계약 원문과 대조해 반영하겠습니다.\n\n" +
    "1. 회사명:\n2. 제품명(표기해야 할 이름):\n" +
    "3. 어떤 점이 잘못되었나요:\n" +
    "   (예: 다른 회사 제품으로 표시됨 / 제품군으로만 남아 있음 / 납품 기록이 목록에 없음 / 제품명 표기 오류)\n" +
    "4. 해당 기록(학교명·계약명·계약일) — 목록에 없다면 '없음'이라고 적어 주세요:\n" +
    "5. 올바른 내용:\n6. 근거 자료(계약서·납품 확인서·조달 공고 번호 등):\n7. 회신받을 담당자·연락처:\n");
  return `
    <div class="crumb"><a href="/">홈</a> › 정정 요청</div>
    <div class="page">
      <h2>정정 요청 · 문의</h2>
      <p class="lead">정보수집 작업의 특성상 실제 발생한 모든 계약을 싣지 못할 수 있습니다.
      시스템에서 누락되거나 기타 이유 등으로 수록되지 못할 수 있으니
      <b>추가·삭제·정정</b> 등 모든 요청을 주시면 본 서비스의 품질을 더 높일 수 있습니다.</p>

      <h3>이런 경우 알려 주세요</h3>
      <p class="who">학교·교육청</p>
      <ul>
        <li>우리 학교 기록이 아닌데 실려 있는 경우</li>
        <li>제품명이 실제와 다르게 표시된 경우</li>
        <li>학교 이름·지역·계열이 잘못된 경우 (개명·이전 등)</li>
        <li>이미 종료한 계약이 사용 중인 것처럼 보이는 경우</li>
      </ul>
      <p class="who">제품을 공급하는 기업</p>
      <ul>
        <li>우리 제품인데 <b>다른 회사 제품으로</b> 표시된 경우</li>
        <li>제품명·회사명 표기가 실제와 다른 경우 (브랜드명 변경·통합 포함)</li>
        <li>계약명에 제품 이름이 없어 <b>제품군으로만 남아 있는</b> 기록이 우리 제품인 경우</li>
        <li>납품한 학교가 목록에 <b>빠져 있는</b> 경우</li>
      </ul>

      <h3>처리 방식</h3>
      <ul>
        <li>보내주신 내용은 원본 조달 기록과 대조해 확인합니다.</li>
        <li>확인되면 해당 기록을 수정하거나 내리고, 다음 갱신에 반영합니다.</li>
        <li>계약 원문 자체가 잘못된 경우에는 원문을 바꿀 수 없어, 참고 설명을 덧붙이는 방식으로 처리합니다.</li>
        <li>이 목록은 <b>공개된 조달 기록</b>만을 근거로 삼습니다. 기록에 없는 납품을 새로 넣거나
          계약명에 없는 제품명을 채우려면 계약서·납품 확인서 같은 근거가 필요합니다.
          홍보 목적의 등재 요청은 받지 않습니다.</li>
      </ul>

      <h3>보내실 곳</h3>
      <div class="cta-row">
        <div>
          <p>아래 버튼을 누르면 보내는 분에 맞는 서식이 채워진 메일 창이 열립니다.
          메일 앱이 없으시면 <b>gklim001@gmail.com</b> 으로 직접 보내주셔도 됩니다.</p>
          <div class="btnrow">
            <a class="mailbtn" href="mailto:gklim001@gmail.com?subject=${subj}&body=${body}">학교·개인 정정 요청</a>
            <a class="mailbtn alt" href="mailto:gklim001@gmail.com?subject=${subjCo}&body=${bodyCo}">공급 기업 정정 요청</a>
          </div>
        </div>
        <img src="/contact_person.png?v=1" width="137" height="186" alt="">
      </div>
      <p style="margin-top:18px">데이터를 어떻게 모으고 판정하는지는 <a href="/about">데이터 안내</a>에서 보실 수 있습니다.</p>
    </div>`;
}

let PLIST_G = "";
// ---- 지도 ----
// 학교가 나오는 목록 화면마다 '목록 | 지도'를 고른다. 지도는 그 화면의 목록과 같은 기록·학교를 그대로
// 올린다(기간·계열·지역·설립 조건을 따로 셈하지 않는다). 좌표는 make_coords.py가 한국교육시설안전원
// 학교위치에 주소로 맞춰 붙이고, 못 맞춘 곳만 OSM·주소 변환으로 찾는다.
// 지도 부품(MapLibre)과 좌표 파일(school_geo.js)은 지도를 처음 열 때만 받는다.
// 고른 방식은 주소(?view=map)에 남긴다 — 지도 화면을 그대로 링크로 나눌 수 있고, 화면을 옮겨도 유지된다
let VMODE = new URLSearchParams(location.search).get("view") === "map" ? "map" : "list";
let MAP_SPEC = null, MAP = null, MAP_KIT = null;
window.setVMode = m => {
  const y = window.scrollY, q = new URLSearchParams(location.search);
  if (m === "map") q.set("view", "map"); else q.delete("view");
  history.replaceState(null, "", location.pathname + (q.toString() ? "?" + q : ""));
  VMODE = m; render(); window.scrollTo(0, y);
};
const IDX_POS = new Map(IDX.map((s, i) => [s, i]));
const MAP_LIB = "https://cdn.jsdelivr.net/npm/maplibre-gl@5.6.0/dist/maplibre-gl";
function loadMapKit() {
  if (MAP_KIT) return MAP_KIT;
  const tag = document.querySelector('script[src^="/data.js"]');
  const b = tag ? (tag.getAttribute("src").split("?")[1] || "") : "";
  const add = el => new Promise((ok, no) => {
    el.onload = ok; el.onerror = no; (el.tagName === "LINK" ? document.head : document.body).appendChild(el);
  });
  MAP_KIT = Promise.all([
    add(Object.assign(document.createElement("link"), {rel: "stylesheet", href: MAP_LIB + ".css"})),
    add(Object.assign(document.createElement("script"), {src: MAP_LIB + ".js"})),
    add(Object.assign(document.createElement("script"), {src: "/school_geo.js" + (b ? "?" + b : "")})),
  ]).catch(e => { MAP_KIT = null; throw e; });
  return MAP_KIT;
}
// 목록 도구줄 맨 왼쪽의 '목록 | 지도'
function modeToggle() {
  return `<span class="vmode" role="group" aria-label="보기 방식">` +
    `<button type="button" class="${VMODE === "list" ? "on" : ""}" aria-pressed="${VMODE === "list"}" onclick="setVMode('list')">목록</button>` +
    `<button type="button" class="${VMODE === "map" ? "on" : ""}" aria-pressed="${VMODE === "map"}" onclick="setVMode('map')">지도</button></span>`;
}
// 기록 목록 → 학교별 건수. 학교코드가 없는 기록(집합 항목·학교 미상)은 지도에 올릴 수 없어 따로 센다.
function mapFromRecs(recs) {
  const by = new Map(); let lost = 0;
  for (const r of recs) {
    if (r.dup) continue;
    const s = r.schoolCode && idxByCode.get(r.schoolCode);
    if (!s) { lost++; continue; }
    const e = by.get(s) || {k: 0, name: r.school};
    e.k++; by.set(s, e);
  }
  return {items: [...by].map(([s, e]) => ({s, k: e.k, name: e.name})), lost, unit: "recs"};
}
function recsBlock(recs, opts = {}) {
  const tool = modeToggle();
  if (VMODE !== "map") return pagedTable(recs, {...opts, tool});
  const rs = listQFilter(recs);
  const spec = mapFromRecs(rs);
  spec.nrec = rs.filter(r => !r.dup).length;
  spec.recs = rs;                                  // 학교를 누르면 지도 아래에 보일 기록
  return listToolbar(rs.length, recs.length > PAGE_SIZE || !!LISTQ, tool) + mapBox(spec);
}
function mapBox(spec) {
  MAP_SPEC = spec;
  return `<div class="mapsum" id="mapsum">&nbsp;</div>
    <div id="map" class="map" aria-label="학교 지도"><div class="maploading">지도를 불러오는 중입니다…</div></div>
    <div id="mapsel" aria-live="polite"></div>`;
}
// 지도에서 누른 학교의 기록 — 화면을 옮기지 않고 지도 바로 아래에 보인다.
// 목록 화면의 지도면 그 목록에 든 기록만, 학교 전체 보기면 그 학교의 기록 전부.
// 같은 자리에 선 학교들은 초·중·고 차례로 세운다 — 학교급이 오르는 순서가 눈에 익다.
const LV_RANK = p => { const v = p.lv || p.l || "";
  return /초등|\(초\)/.test(v) ? 0 : /중학|\(중\)/.test(v) ? 1
    : /고등|\(고\)|고$/.test(v) ? 2 : /특수/.test(v) ? 3 : 4; };
const byLevel = (x, y) => LV_RANK(x) - LV_RANK(y) || x.n.localeCompare(y.n, "ko");
function showMapSel(spec, rows) {
  const box = document.getElementById("mapsel");
  if (!box) return;
  const all = spec.recs || [], MAX = 30;
  box.innerHTML = rows.slice(0, 8).map(p => {
    const rs = sortRecs(all.filter(r => r.schoolCode === p.c));
    const nd = rs.filter(r => !r.dup).length;
    return `<div class="mapsel"><div class="mapsel-h"><b>${esc(p.n)}</b>
        <span>${esc(p.s)} · ${esc(p.l)} · ${nd ? `기록 ${nd.toLocaleString()}건` : "기록 없음"}</span>
        <a href="${esc(p.href)}">${nd ? "학교 화면에서 보기 ›" : "학교 정보 ›"}</a></div>
      ${rs.length ? recordTable(fillDetail(rs.slice(0, MAX)), {showSchool: false}) : ""}
      ${rs.length > MAX ? `<p class="cv">최근 ${MAX}건만 보여 줍니다 — 전체는 학교 화면에서 볼 수 있습니다</p>` : ""}</div>`;
  }).join("") + (rows.length > 8 ? `<p class="cv">이 자리의 다른 ${rows.length - 8}곳은 더 확대해 눌러 보세요</p>` : "");
}
window.clearMapSel = () => {
  const box = document.getElementById("mapsel");
  if (box) box.innerHTML = "";
  if (MAP && MAP._setSel) MAP._setSel([]);
};
// ⌘(맥)·Ctrl을 누른 채 끌면 좌우로 방향을 돌리고 위아래로 기울인다 — 기울이면 건물이 입체로 선다.
// MapLibre 기본은 Ctrl·오른쪽 버튼뿐이라 맥에서 흔히 쓰는 ⌘로도 되게 한다.
let MAP_ROT = null;
window.addEventListener("mousemove", e => {
  if (!MAP_ROT || !MAP) return;
  MAP.jumpTo({bearing: MAP_ROT.b + (e.clientX - MAP_ROT.x) * 0.4,
              pitch: Math.max(0, Math.min(70, MAP_ROT.p - (e.clientY - MAP_ROT.y) * 0.3))});
});
window.addEventListener("mouseup", () => { MAP_ROT = null; });
function mountMap() {
  const el = document.getElementById("map"), spec = MAP_SPEC;
  if (MAP) { MAP.remove(); MAP = null; }
  if (!el || !spec) return;
  loadMapKit().then(() => {
    if (!el.isConnected || MAP_SPEC !== spec) return;           // 받는 사이 화면이 바뀌었다
    const feats = []; let noXY = 0, withRec = 0, withRecOnMap = 0;
    for (const {s, k, name} of spec.items) {
      if (k) withRec++;                                  // 지도에 못 올린 학교도 함께 센다 — 머리글과 같은 기준
      const g = SCHOOL_GEO[IDX_POS.get(s)];
      if (!g) { noXY++; continue; }
      if (k) withRecOnMap++;
      feats.push({type: "Feature", geometry: {type: "Point", coordinates: [g[1], g[0]]},
        properties: {n: s.n, l: s.h || s.l || "", lv: s.l || "", s: s.s, k, c: s.c,
          href: s.c ? `/code/${encodeURIComponent(s.c)}` : `/school/${encodeURIComponent(name || s.n)}`}});
    }
    const N = v => v.toLocaleString();
    const sum = document.getElementById("mapsum");
    if (sum) sum.textContent = `지도 표시 ${N(feats.length)}개교 · 위치 미확인 ${N(noXY)}개교`
      + (spec.unit === "idx" ? ` · 기록 있는 곳 ${N(withRec)}개교(지도 위 ${N(withRecOnMap)}개교)` : "")
      + (spec.lost ? ` · 학교 미특정 기록 ${N(spec.lost)}건` : "")
      + (spec.nrec != null ? ` · 결과 ${N(spec.nrec)}건` : "");
    el.innerHTML = "";
    const map = MAP = new maplibregl.Map({container: el, center: [127.8, 36.2], zoom: 5.6, minZoom: 5, maxZoom: 18, maxPitch: 70,
      style: "https://tiles.openfreemap.org/styles/liberty", attributionControl: {compact: true}});
    map.addControl(new maplibregl.NavigationControl({visualizePitch: true}), "top-right");
    // 출처 표기는 빼지 못한다(OpenStreetMap 자료·OpenFreeMap 이용 조건). 대신 처음엔 ⓘ만 두고
    // 누르면 펼쳐지게 한다. 여닫기는 지도 기본 동작에 맡기고 우리는 처음 상태만 접는다 —
    // 접힘을 우리가 따로 관리했더니 누를 때 지도와 서로 상쇄돼 아무 변화가 없었다(2026-09-12).
    // 지도는 출처를 갱신할 때마다 펼침 표시를 다시 붙이므로, 사용자가 한 번 누르기 전까지 걷어 준다.
    let attrTouched = false;
    const collapseAttr = () => {
      if (attrTouched) return;
      const at = el.querySelector(".maplibregl-ctrl-attrib");
      if (at) at.classList.remove("maplibregl-compact-show");
    };
    el.addEventListener("click", e => { if (e.target.closest(".maplibregl-ctrl-attrib")) attrTouched = true; });
    map.on("sourcedata", collapseAttr);
    map.on("idle", collapseAttr);
    collapseAttr();
    el.addEventListener("mousedown", e => {
      if (!(e.metaKey || e.ctrlKey) || e.button !== 0) return;
      e.preventDefault(); e.stopPropagation();                  // 끌기(이동)로 넘기지 않는다
      MAP_ROT = {x: e.clientX, y: e.clientY, b: map.getBearing(), p: map.getPitch()};
    }, true);
    if (feats.length) {
      const xs = feats.map(f => f.geometry.coordinates[0]), ys = feats.map(f => f.geometry.coordinates[1]);
      map.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], {padding: 40, maxZoom: 14, duration: 0});
    }
    // 양식만 오면 바로 얹는다 — "load"는 바탕 타일까지 기다려 학교가 늦게 떴다
    // 양식만 오면 바로 얹는다 — "load"는 바탕 타일까지 기다려 학교가 늦게 떴다
    map.once("style.load", () => {
      for (const ly of map.getStyle().layers) {
        // 바탕 지도의 가게·시설 이름은 걷는다 — 학교 이름표와 겹쳐 어지럽다
        if (ly.id.startsWith("poi")) { map.setLayoutProperty(ly.id, "visibility", "none"); continue; }
        if (ly.type !== "symbol") continue;
        // 지명은 한글로 — 기본 양식은 로마자와 현지 표기를 겹쳐 쓴다
        const tf = map.getLayoutProperty(ly.id, "text-field");
        if (tf && JSON.stringify(tf).includes("name")) map.setLayoutProperty(ly.id, "text-field", ["coalesce", ["get", "name:ko"], ["get", "name"]]);
      }
      // 묶음은 우리가 직접 짓는다 — 지도 타일이 그려져야만 알 수 있는 방식(querySourceFeatures)은
      // 창이 가려지거나 그리기가 늦으면 아무것도 못 내놓는다(2026-09-12). 화면 좌표 44px 칸에 모아 센다.
      const mk = [];
      let selK = [], expandKey = null;
      // 펼친 묶음은 화면을 옮겨도 같은 묶음임을 알아야 한다 — 속한 학교코드로 이름표를 만든다
      const ckey = c => c.items.map(f => f.properties.c || f.properties.n).sort().join("|");
      // 같은 자리에 선 학교들은 아무리 확대해도 칸이 나뉘지 않아, 누르기 전에는 묶음으로만 보였다.
      // 충분히 확대하면 누르지 않아도 저절로 편다 — 다만 너무 많으면 화면을 덮으므로 여덟 곳까지만.
      const autoSplit = c => {
        if (map.getZoom() < 16.2 || c.items.length > 8) return false;
        const xs = c.items.map(f => f.geometry.coordinates[0]), ys = c.items.map(f => f.geometry.coordinates[1]);
        return Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) < 0.0004;
      };
      // 선택은 학교코드로 가린다 — 주소(/school/이름)로 가렸더니 이름이 같은 다른 학교까지
      // 함께 물들었다(2026-09-12 "동북초": 서울 도봉구와 전북 부안이 같이 초록이 됐다).
      const paintSel = () => { for (const m of mk) m._el.classList.toggle("on", selK.includes(m._key)); };
      // 묶는 칸은 멀리서 볼수록 크게 — 44px로 묶었더니 전국 화면에 딱지가 40개 넘게 깔려
      // 어지러웠다(2026-09-12). 칸 크기는 시안이 쓰는 값(180/140/88)을 그대로 쓴다.
      const cellOf = z => z < 11.5 ? 180 : z < 13 ? 140 : 88;
      const MAX = 400;
      // 딱지가 차지할 가로폭(글자 수로 어림) — 한글은 넓고 숫자·영문은 좁다
      const pinW = t => 30 + [...t].reduce((a, ch) => a + (/[가-힣]/.test(ch) ? 13 : 7.5), 0);
      const draw = () => {
        const b = map.getBounds(), pad = 0.15, CELL = cellOf(map.getZoom());
        const cells = new Map();
        for (const f of feats) {
          const [lng, lat] = f.geometry.coordinates;
          if (lng < b.getWest() - pad || lng > b.getEast() + pad || lat < b.getSouth() - pad || lat > b.getNorth() + pad) continue;
          const pt = map.project([lng, lat]);
          const key = Math.round(pt.x / CELL) + "," + Math.round(pt.y / CELL);
          const c = cells.get(key) || {items: []};
          c.items.push(f);
          cells.set(key, c);
        }
        // 딱지로 화면이 뒤덮이지 않게 — 묶음과 기록 많은 학교부터
        // 큰 묶음부터 자리를 잡고, 이미 놓인 딱지와 겹치면 놓지 않는다 — 겹쳐 쌓이면 읽을 수 없다
        const sorted = [...cells.values()].sort((x, y) => y.items.length - x.items.length
          || (y.items[0].properties.k || 0) - (x.items[0].properties.k || 0));
        const list = [], boxes = [];
        for (const c of sorted) {
          if (list.length >= MAX) break;
          const many = c.items.length > 1;
          const txt = many ? `${c.items.length.toLocaleString()}개교` : c.items[0].properties.n;
          // 겹침은 '실제로 놓을 자리'로 재야 한다 — 묶음은 속한 학교들의 가운데에 놓는다
          c.at = many ? [c.items.reduce((a, f) => a + f.geometry.coordinates[0], 0) / c.items.length,
                         c.items.reduce((a, f) => a + f.geometry.coordinates[1], 0) / c.items.length]
                      : c.items[0].geometry.coordinates;
          const pt = map.project(c.at);
          const w = pinW(txt), box = [pt.x - w / 2, pt.y - 18, pt.x + w / 2, pt.y + 18];
          if (boxes.some(o => box[0] < o[2] + 4 && box[2] > o[0] - 4 && box[1] < o[3] + 4 && box[3] > o[1] - 4)) continue;
          boxes.push(box); list.push(c);
        }
        for (const m of mk) m.remove();
        mk.length = 0;
        for (const c of list) {
          const many = c.items.length > 1;
          if (many && (ckey(c) === expandKey || autoSplit(c))) {
            // 펼친 묶음 — 초·중·고 차례로 위에서 아래로 세운다. 각각이 따로 눌리고 따로 물든다.
            const its = c.items.map(f => f.properties).sort(byLevel);
            its.forEach((q, i) => {
              const b2 = document.createElement("button");
              b2.type = "button";
              b2.className = "mpin" + (q.k > 0 ? "" : " dim");
              b2.textContent = q.n;
              b2.title = `${q.s} · ${q.l} · ${q.k ? q.k.toLocaleString() + "건" : "기록 없음"}`;
              b2.onclick = ev2 => { ev2.stopPropagation(); selK = [q.c || q.href]; showMapSel(spec, [q]); paintSel(); };
              const m2 = new maplibregl.Marker({element: b2, offset: [0, (i - (its.length - 1) / 2) * 36]})
                .setLngLat(c.at).addTo(map);
              m2._el = b2; m2._key = q.c || q.href;
              mk.push(m2);
            });
            continue;
          }
          const p = c.items[0].properties;
          const lngs = c.items.map(f => f.geometry.coordinates[0]), lats = c.items.map(f => f.geometry.coordinates[1]);
          const at = c.at;
          const el = document.createElement("button");
          el.type = "button";
          el.className = "mpin" + (many ? " mcluster" : p.k > 0 ? "" : " dim");
          el.textContent = many ? `${c.items.length.toLocaleString()}개교` : p.n;
          el.title = many ? "누르면 확대합니다" : `${p.s} · ${p.l} · ${p.k ? p.k.toLocaleString() + "건" : "기록 없음"}`;
          el.onclick = ev => {
            ev.stopPropagation();
            if (many) {
              // 같은 주소를 쓰는 학교들은 좌표가 같아 확대해도 영영 나뉘지 않는다 — 그때는 목록을 편다
              const spanX = Math.max(...lngs) - Math.min(...lngs), spanY = Math.max(...lats) - Math.min(...lats);
              if (Math.max(spanX, spanY) < 0.0004 || map.getZoom() >= 16.5) {
                // 좌표가 같아 확대해도 영영 나뉘지 않는다 — 딱지를 학교별로 펴서 하나씩 고르게 한다
                expandKey = ckey(c);
                selK = [];
                showMapSel(spec, c.items.map(f => f.properties).sort(byLevel));
                draw();
                return;
              }
              map.fitBounds([[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
                            {padding: 60, maxZoom: Math.min(17, map.getZoom() + 3), duration: 400});
            } else {
              selK = [p.c || p.href];
              showMapSel(spec, [p]);
              paintSel();
            }
          };
          const m = new maplibregl.Marker({element: el}).setLngLat(at).addTo(map);
          m._el = el; m._key = many ? "" : (p.c || p.href);
          mk.push(m);
        }
        paintSel();
      };
      map._setSel = keys => { selK = keys; paintSel(); };
      map.on("click", () => { if (selK.length || expandKey) { expandKey = null; clearMapSel(); draw(); } });   // 빈 곳을 누르면 선택이 풀린다
      map.on("moveend", draw);
      map.on("zoomend", draw);
      draw();
    });
  }).catch(() => { el.innerHTML = `<div class="maploading">지도를 불러오지 못했습니다 — 목록으로 보세요</div>`; });
}

function render() {
  const seg = (location.pathname || "/").split("/");
  const kind = seg[1];
  const arg = seg.length > 2 ? decodeURIComponent(seg.slice(2).join("/")) : undefined;
  const view = $("#view");
  if (kind === "school") view.innerHTML = schoolView(arg);
  else if (kind === "code") view.innerHTML = codeView(arg);
  else if (kind === "tag") view.innerHTML = tagView(arg);
  else if (kind === "drill") view.innerHTML = drillView(seg[2], decodeURIComponent(seg.slice(3).join("/")));
  else if (kind === "drill2") view.innerHTML = drillTagView(seg[2], decodeURIComponent(seg[3] || ""), decodeURIComponent(seg[4] || ""));
  else if (kind === "search") {
    // 검색은 늘 전 기간을 본다. 통계는 최근만 봐도 뜻이 통하지만, 검색은 기간에 걸려
    // 0건이 나오면 '그런 기록이 없다'는 잘못된 답을 주게 된다(호랑에듀가 그랬다).
    view.innerHTML = searchView(arg);
    if (OLD_STATE !== "done") withOld("", () => render());
  }
  else if (kind === "about") view.innerHTML = aboutView();
  else if (kind === "schools" || kind === "records" || kind === "products" || kind === "vendors") {
    // '전체 보기'는 가진 것을 다 본다는 뜻이다 — 기간도 전 기간으로 연다(검색과 같은 이유).
    // 다만 사용자가 기간을 직접 고른 뒤라면 그 선택을 덮지 않는다.
    if (!PF_TOUCHED && (PF || PT)) { PF = ""; PT = ""; }
    view.innerHTML = kind === "schools" ? schoolsView() : kind === "records" ? recordsView()
      : kind === "products" ? productsView() : vendorsView();
    if (OLD_STATE !== "done") withOld("", () => render());
  }
  else if (kind === "regions") view.innerHTML = regionsView();
  else if (kind === "vendor") view.innerHTML = vendorView(arg);
  else if (kind === "contact") view.innerHTML = contactView();
  else {
    view.innerHTML = homeView();
    animateCount();
  }
  // 현재 화면에 해당하는 상단 메뉴 강조
  document.querySelectorAll(".navlinks a").forEach(a =>
    a.classList.toggle("on", a.getAttribute("href") === `/${kind || ""}`));
  // '전체 보기'는 네 목록 어디에 있어도 켜 둔다
  const allLink = document.querySelector('.navlinks a[href="/records"]');
  if (allLink) allLink.classList.toggle("on", ["records", "schools", "products", "vendors"].includes(kind));
  // 히어로는 첫 화면에서만 크게, 하위 화면에서는 접어 둔다
  document.body.classList.toggle("sub-page", !!kind);
  // 검색창은 현재 화면의 검색 상태만 반영 — 검색 결과 페이지에서만 검색어 유지
  const qEl = document.querySelector("#q");
  if (qEl) qEl.value = kind === "search" ? (arg || "") : "";
  const sEl = document.querySelector("#sugg");
  if (sEl) sEl.hidden = true;
  mountMap();
  window.scrollTo(0, 0);
}
// 화면을 옮길 때 쓰는 하나뿐인 통로. 주소를 진짜 경로로 바꾸고 다시 그린다.
// (전에는 주소 뒤 #에 화면을 적었다 — 논문·공문에 인용하기 나빴다)
function resetView() {
  PAGE = 1; LISTQ = ""; SORTK = "new"; PLIST_G = ""; SCHOOL_TAG = ""; VLIST_KIND = ""; SLIST_G = ""; SPAGE = 1;
  // 목록이냐 지도냐는 늘 주소가 정한다 — 지도를 보다 제품을 누르면 새 화면은 목록으로 열리고
  // (go가 view를 떼어 낸다), ?view=map 링크로 들어오거나 뒤로 가면 그때 화면 그대로 돌아온다.
  VMODE = new URLSearchParams(location.search).get("view") === "map" ? "map" : "list";
  clearMapSel();
}
function go(path) {
  // 같은 화면이면 맨 위로 올린다 — 첫 화면에서 홈을 눌렀을 때 아무 일도 없어 보였다(2026-09-12)
  if (path === location.pathname) { window.scrollTo({top: 0, behavior: "smooth"}); return; }
  const q = new URLSearchParams(location.search);
  q.delete("view");                                  // 옮겨 간 화면은 목록부터 보여 준다
  history.pushState(null, "", path + (q.toString() ? "?" + q : ""));
  resetView(); render();
}
window.go = go;
window.addEventListener("popstate", () => { resetView(); render(); });
// 사이트 안 링크는 페이지를 새로 부르지 않고 그 자리에서 넘긴다.
// 새 탭으로 열기(⌘·Ctrl·가운데 클릭)와 바깥 링크는 브라우저에 맡긴다.
document.addEventListener("click", e => {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = e.target.closest("a");
  if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
  const href = a.getAttribute("href");
  if (!href || !href.startsWith("/") || href.startsWith("//")) return;
  e.preventDefault();
  go(href);
});
perfMark("화면 코드 준비");
render();
perfMark("첫 화면 그리기");
// 요약 파일이 원자료와 어긋나면 첫 화면 수치가 뒤늦게 바뀐다 — ?perf=1일 때 미리 알려 준다
if (PERF && typeof DB_SUM !== "undefined") {
  // 요약과 같은 기준으로 세야 진짜 어긋남만 잡는다 — 전 기간으로 세어 늘 경고가 떴고,
  // 그래서 첫 화면과 자료 화면의 순위가 달라진 것을 잡아 주지 못했다(2026-09-12).
  const BASE = baseRecs().filter(r => !r.dup);
  const RF = BASE.filter(hasProduct);
  const tp = count(RF.flatMap(r => r.tags.map(t => [t])), x => x[0]);
  const names = tp.map(p => p[0]).filter(t => !GENERIC_TAGS.has(t));
  const tags = names.slice(0, 12)
    .map(t => [t, uniq(RF.filter(r => r.tags.includes(t)).map(skey)).length])
    .sort((a, b) => b[1] - a[1]);
  if (JSON.stringify(tags) !== JSON.stringify(DB_SUM.home.product.tags))
    console.warn("[perf] data_summary.js가 원자료와 다릅니다 — node make_summary.js를 다시 돌리세요");
}

// ---- 자동완성 ----
const groupBySchool = {};
R.forEach(r => { if (!(r.school in groupBySchool)) groupBySchool[r.school] = recLeaf(r); });
perfMark("학교 색인");
const suggItems = [
  ...tags.map(([t]) => ({label: tagName(t), kind: GENERIC_TAGS.has(t) ? "제품군" : "제품", href: `/tag/${encodeURIComponent(t)}`})),
  ...schools.map(s => ({label: s, kind: "학교·기록 있음", href: `/school/${encodeURIComponent(s)}`, g: groupBySchool[s], rg: (R.find(r => r.school === s) || {}).sido})),
  ...IDX.filter(s => !recordCodes.has(s.c)).map(s => ({label: s.n, kind: `${s.s} ${s.h || s.l}`, href: `/code/${s.c}`, g: idxGroup(s), rg: s.s})),
  ...[...VENDORS.values()].filter(v => v.n >= 5 && vendorKind(v.key) === "공급 기업")
     .map(v => ({label: v.name, kind: "공급 기업", href: `/vendor/${encodeURIComponent(v.key)}`})),
];
const q = $("#q"), sugg = $("#sugg");
// 요약 화면이 걸어 둔 '불러오는 중' 안내를 걷고, 그 사이에 입력한 글자가 있으면 바로 반영한다
if (q) {
  if (q.dataset.ph) { q.placeholder = q.dataset.ph; delete q.dataset.ph; }
  if (q.value.trim()) setTimeout(() => q.dispatchEvent(new Event("input")), 0);
}
let selIdx = -1, current = [];
q.addEventListener("input", () => {
  const v = q.value.trim().toLowerCase();
  selIdx = -1;
  if (!v) { sugg.hidden = true; return; }
  const vTerms = queryTerms(v);
  current = suggItems.filter(it => vTerms.some(t => it.label.toLowerCase().includes(t))
    && (!SF.size || !it.g || SF.has(it.g))
    && (!RG.size || !it.rg || RG.has(it.rg))).slice(0, 12);
  sugg.innerHTML = current.map((it, i) => `<div data-i="${i}"><span>${esc(it.label)}</span><span class="kind">${it.kind}</span></div>`).join("")
    + `<div data-i="-2"><span>“${esc(q.value.trim())}” 전체 검색</span><span class="kind">↵</span></div>`;
  sugg.hidden = false;
});
sugg.addEventListener("mousedown", e => {
  const el = e.target.closest("[data-i]"); if (!el) return;
  const i = +el.dataset.i;
  go(i >= 0 ? current[i].href : `/search/${encodeURIComponent(q.value.trim())}`);
  sugg.hidden = true; q.blur();
});
q.addEventListener("keydown", e => {
  if (e.isComposing || e.keyCode === 229) return;  // 한글 IME 조합 중 Enter/방향키 무시 (글자 중복 방지)
  if (sugg.hidden) { if (e.key === "Enter" && q.value.trim()) { go(`/search/${encodeURIComponent(q.value.trim())}`); } return; }
  const n = current.length;
  if (e.key === "ArrowDown") { selIdx = (selIdx + 1) % n; }
  else if (e.key === "ArrowUp") { selIdx = (selIdx - 1 + n) % n; }
  else if (e.key === "Enter") {
    go(selIdx >= 0 ? current[selIdx].href : `/search/${encodeURIComponent(q.value.trim())}`);
    sugg.hidden = true; q.blur(); return;
  } else if (e.key === "Escape") { sugg.hidden = true; return; }
  else return;
  e.preventDefault();
  [...sugg.children].forEach((el, i) => el.classList.toggle("sel", i === selIdx));
});
document.addEventListener("click", e => { if (!e.target.closest(".searchwrap")) sugg.hidden = true; });
