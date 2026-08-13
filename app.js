// index.html에서 떼어낸 화면 코드 — 요약으로 첫 화면을 그린 뒤에 원자료와 함께 읽는다.
// (전역 이름과 inline onclick 핸들러가 그대로 동작하도록 일반 스크립트로 둔다)
// data.js는 열 이름을 한 번만 적고 되풀이되는 문자열을 사전으로 치환한 압축 형식이다.
// 화면 코드는 예전과 같은 객체 배열을 기대하므로 여기서 원래 모양으로 되돌린다.
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
           outside: d.outside || {}, noProc: d.noProc || {} };
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
  DETAIL_DONE = new Uint8Array(d.rows.length);
  if (typeof perfMark === "function") perfMark("상세 자료 받기");
  if (typeof render === "function") render();                  // 받아온 내용으로 다시 그린다
  if (typeof perfMark === "function") perfMark("상세 반영 후 재그리기");
}
function fillDetail(recs) {                                    // 보이는 기록만 채운다
  if (!DETAIL || !recs || !recs.length) return recs;
  const cols = DETAIL.cols, dict = DETAIL.dict || {}, pre = DETAIL.urlPrefix || "";
  for (const o of recs) {
    const i = o && o._i;
    if (i == null || DETAIL_DONE[i]) continue;
    DETAIL_DONE[i] = 1;
    const row = DETAIL.rows[i];
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
  const v = DETAIL.rows[i] ? DETAIL.rows[i][c] : null;
  const dict = DETAIL.dict || {};
  return (dict[k] && typeof v === "number") ? dict[k][v] : (v == null ? "" : v);
}
const contentOf = r => r.content != null ? r.content : detailVal(r._i, "content");
(function loadDetail() {
  const s = document.createElement("script");
  s.src = "data_detail.js?b=20260813d";
  s.onload = () => { if (typeof DB_DETAIL !== "undefined") mergeDetail(DB_DETAIL); };
  document.body.appendChild(s);
})();
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const count = (arr, key) => { const m = new Map(); for (const x of arr) { const k = key(x); if (!k) continue; m.set(k, (m.get(k)||0)+1); } return [...m.entries()].sort((a,b)=>b[1]-a[1]); };
const uniq = arr => [...new Set(arr)];

// ---- 인덱스 ----
const schools = uniq(R.map(r => r.school)).sort();
const tags = count(R.flatMap(r => r.tags.map(t => [t])), x => x[0]);
const schoolCountByTag = t => uniq(R.filter(r => r.tags.includes(t)).map(r => r.school)).length;
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
const CHANNEL = /지마켓|쿠팡|11번가|인터파크|위메프|티몬|네이버|카카오|이베이|옥션|스마트스토어|우체국|조달청|학교장터|이웃닷컴|다나와|하이마트/;
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
    <div class="brow${drillFn ? " rowlink" : ""}"${drillFn ? ` onclick="location.hash='${drillFn(k)}'" role="link" tabindex="0" title="누르면 해당 학교 목록을 보여줍니다"` : ""}>
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
function pagedTable(recs, opts) {
  const origTotal = recs.length;
  const showFilter = origTotal > PAGE_SIZE || LISTQ;
  if (LISTQ) {
    const terms = queryTerms(LISTQ.toLowerCase());
    recs = recs.filter(r => terms.some(t => (r.school + r.product + contentOf(r)).toLowerCase().includes(t)));
  }
  recs = sortRecs(recs);
  const total = recs.length;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const page = Math.min(PAGE, pages);
  const slice = fillDetail(recs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE));
  let topbar = "";
  if (pages > 1 || showFilter || SORTK !== "new") {
    const sortSel = `<select class="sortsel" onchange="setSort(this.value)" aria-label="정렬">
        ${[["new","최신순"],["old","오래된순"],["school","학교명순"],["product","제품군순"],["amt","금액 높은순"]].map(([k,l]) => `<option value="${k}"${SORTK===k?" selected":""}>${l}</option>`).join("")}
      </select>`;
    const filterHtml = showFilter ? `${LISTQ ? `<span class="listq-n"><b>${total.toLocaleString()}건</b></span>` : ""}
      <input id="lq" class="listq" type="search" placeholder="결과 내 검색" value="${esc(LISTQ)}"
        oninput="if(this.value==='')applyListQ('')" onkeyup="if(event.key==='Enter')applyListQ(this.value)">` : "";
    topbar = `<div class="listtool">${sortSel}${filterHtml}</div>`;
  }
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
      ${showSchool ? `<td><a href="#/school/${encodeURIComponent(r.school)}">${esc(r.school)}</a><div class="conf">${esc(r.type)} · ${esc(r.region)}${r.origSchool ? ` · 계약 당시 ${esc(r.origSchool)}` : ""}</div></td>` : ""}
      <td>${esc(r.product)}<div>${r.tags.map(t => `<a class="chip${GENERIC_TAGS.has(t) ? " gen" : ""}" href="#/tag/${encodeURIComponent(t)}">${tagLabel(t)}</a>`).join("")}</div></td>
      <td style="white-space:nowrap">${esc(r.period)}</td>
      <td style="max-width:320px">${esc(r.content)}${r.vendor && vendorKind(vkey(r.vendor)) === "공급 기업" ? `<div class="conf"><a href="#/vendor/${encodeURIComponent(vkey(r.vendor))}">${esc(r.vendor)}의 다른 납품 보기 ›</a></div>` : ""}<div class="conf">신뢰도 ${esc(r.confidence)}${r.dup ? " · 조달 기록과 동일 건(1건 집계)" : ""}${r.feeOnly ? " · 결제 수수료(제품 구매액 아님)" : ""}</div>${noteLine(r)}</td>
      <td>${r.url && !/S2B|나라장터/i.test(r.sourceType) ? `<a href="${esc(r.url)}" target="_blank" rel="noopener" title="${r.sourceType === "학교 전용 플랫폼" ? `학교 전용 주소: ${esc(r.url.replace(/^https?:\/\//, "").split("/")[0])} — 전용 페이지 존재가 도입의 근거입니다` : esc(r.url)}">${esc(r.sourceType)}</a>` : esc(r.sourceType)}</td>
    </tr>`).join("") + `</tbody></table></div>`;
}

// ---- 기간 필터 ----
// 자료는 2020년까지 있지만 기본으로는 2023년부터 본다.
// 2020~2022년은 계약명에 제품 이름이 잘 안 적히던 시기라(제품군만 붙는 비율 76%)
// 기본에 섞으면 지금 그림이 희석된다. 넓혀 보고 싶은 사람만 당겨 오게 한다.
const BASE_FROM = "2023-01";
let PF = BASE_FROM, PT = "";  // "YYYY-MM"
window.setPF = v => { PF = v; render(); };
window.setPT = v => { PT = v; render(); };
window.clearPeriod = () => { PF = BASE_FROM; PT = ""; render(); };
const ymInt = s => s ? parseInt(s.replace("-", ""), 10) : null;
const YM_MIN = 202001, YM_MAX = 202607;
let pkS = null, pkE = null, pkBase = 2025;
// 기본(2023년~)과 다르게 잡혀 있으면 조건이 걸린 것이다
const periodOn = () => (PF !== BASE_FROM) || !!PT;
const ymStr = ym => `${Math.floor(ym / 100)}-${String(ym % 100).padStart(2, "0")}`;
const ymKo = ym => `${Math.floor(ym / 100)}.${String(ym % 100).padStart(2, "0")}`;
window.openPicker = () => {
  pkS = ymInt(PF); pkE = ymInt(PT);
  pkBase = pkS ? Math.min(Math.max(Math.floor(pkS / 100), 2020), 2025) : 2025;
  drawPicker();
};
window.closePicker = () => { document.getElementById("pickerRoot").innerHTML = ""; };
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && document.getElementById("pickerRoot").innerHTML) closePicker();
});
window.pkShift = d => { pkBase = Math.min(2025, Math.max(2020, pkBase + d)); drawPicker(); };
window.pkPick = ym => {
  if (pkS !== null && pkE === null && ym >= pkS) pkE = ym;
  else { pkS = ym; pkE = null; }
  drawPicker();
};
window.pkAll = () => { PF = ""; PT = ""; closePicker(); render(); };   // 2020년까지 통째로
window.pkApply = () => {
  if (pkS === null) return;
  PF = ymStr(pkS); PT = ymStr(pkE !== null ? pkE : pkS);
  closePicker(); render();
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
  {k: "alt", label: "방송통신·각종·평생학교", parent: "etc"},
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
const sfIdxCount = () => IDX.filter(s => (!SF.size || SF.has(idxGroup(s))) && (!RG.size || RG.has(s.s))
  && (!ES.size || ES.has(s.f))).length;
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
  const names = SIDOS.filter(s => RG.has(s));
  return names.length <= 3 ? names.join("·") : `${names[0]} 외 ${names.length - 1}개 지역`;
};
let rgSel = null;
window.openRegionPicker = () => { rgSel = new Set(RG); drawRegionPicker(); };
window.rgToggle = s => { rgSel.has(s) ? rgSel.delete(s) : rgSel.add(s); drawRegionPicker(); };
window.rgAll = () => { RG = new Set(); closePicker(); render(); };
window.rgApply = () => { RG = rgSel.size === SIDOS.length ? new Set() : rgSel; closePicker(); render(); };
function drawRegionPicker() {
  const cells = SIDOS.map(s => `
    <button class="pk-cell sc-cell${rgSel.has(s) ? " end" : ""}" onclick="rgToggle('${s}')">
      <span>${s}</span><span class="sc-n">${(IDX_SIDO_COUNT[s] || 0).toLocaleString()}개교</span>
    </button>`).join("");
  const picked = SIDOS.filter(s => rgSel.has(s)).join(" · ");
  document.getElementById("pickerRoot").innerHTML = `
    <div class="pk-overlay">
      <div class="pk-panel" role="dialog" aria-label="지역 선택">
        <button class="pk-x" onclick="closePicker()" aria-label="닫기">✕</button>
        <div class="pk-top"><span></span>
          <div style="text-align:center"><div class="pk-title">지역 선택</div><div class="pk-range">${picked || "전국 (17개 시도 전체)"}</div></div>
        <span></span></div>
        <div class="pk-grid rg-grid">${cells}</div>
        <div class="pk-foot">
          <span class="pk-hint">시도교육청 단위 · 여러 지역을 함께 선택할 수 있습니다</span>
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
  {k: "etc", label: "특수·기타학교", leaves: ["spe", "alt"]},
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
          ${typeRow}${subRows}${esRow}
        </div>
        <div class="pk-foot">
          <span class="pk-hint">학교급을 먼저 고르면 그 안에서 설립 주체(국·공·사립)를 고를 수 있습니다.
            고등학교는 유형까지 나눠 고를 수 있습니다<br>분류 기준: NEIS 학교유형·설립 구분 ·
            마이스터고(산업수요맞춤형고)는 특성화고·마이스터고에 포함</span>
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
          <button class="pk-nav" onclick="pkShift(-1)" ${pkBase <= 2023 ? "disabled" : ""} aria-label="이전 해">‹</button>
          <div style="text-align:center"><div class="pk-title">조사 기간 선택</div><div class="pk-range">${rangeTxt}</div></div>
          <button class="pk-nav" onclick="pkShift(1)" ${pkBase >= 2025 ? "disabled" : ""} aria-label="다음 해">›</button>
        </div>
        <div class="pk-years">${pkYearHTML(pkBase)}${pkYearHTML(pkBase + 1)}</div>
        <div class="pk-foot">
          <span class="pk-hint">시작 월과 종료 월을 차례로 누르세요 (2020.01 ~ 2026.07) ·
            2022년 이전은 계약명에 제품 이름이 잘 적히지 않아 제품군으로만 남은 기록이 많습니다</span>
          <span style="display:flex;gap:8px">
            <button class="pk-btn" onclick="pkAll()" title="2020년 1월부터 모두 봅니다">2020년까지 전체</button>
            <button class="pk-btn" onclick="clearPeriod();closePicker()">기본(2023년~)</button>
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
function baseRecs() {
  const anyF = (PF && PF !== BASE_FROM) || PT || SF.size || RG.size || ES.size || PF === "";
  return anyF ? R.filter(r => inPeriod(r) && sfMatch(r) && rgMatch(r) && esMatch(r)) : R;
}
function filterNote() {
  const bits = [];
  if (periodOn()) bits.push(`조사 기간 ${(PF || "2020-01").replaceAll("-", ".")} ~ ${(PT || "2026-07").replaceAll("-", ".")}`);
  if (RG.size) bits.push(`지역 ${rgLabel()}`);
  if (SF.size) bits.push(`계열 ${sfLabel()}`);
  if (ES.size) bits.push(`설립 주체 ${esLabel()}`);
  return bits.length
    ? `<span class="fnote">${esc(bits.join(" · "))} <a href="#/">홈에서 변경</a></span>` : "";
}

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
    .map(t => [t, uniq(RF.filter(r => r.tags.includes(t)).map(r => r.school)).length])
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
      </div>
      <div class="tile clickable" onclick="openPicker()" role="button" aria-label="조사 기간 변경">
        <div class="v">${active ? `${PF || "2020-01"} ~ ${PT || "2026-07"}`.replaceAll("-", ".") : DB.meta.coveragePeriod}</div>
        <div class="l" style="margin-top:6px">조사 기간 <span class="hint">변경 ▾</span></div>
      </div>
    </div>
    ${anyF ? `<div class="fnote">
      <span>선택 조건 사례 ${RF.length.toLocaleString()}건${active ? " · 월 미상 기록은 연 단위로 포함" : ""}${SF.size ? ` · 계열: ${sfLabel()}` : ""}${ES.size ? ` · 설립 주체: ${esLabel()}` : ""}${rgActive ? ` · 지역: ${rgLabel()}` : ""}</span>
      ${active ? `<button onclick="clearPeriod()">기본 기간(2023년~)</button>` : ""}
      ${scActive ? `<button onclick="scAll()">전체 학교</button>` : ""}
      ${rgActive ? `<button onclick="rgAll()">전국</button>` : ""}
    </div>` : ""}
    <div class="section-div">통계 결과</div>
    <div class="grid2">
      <div class="card"><h2><a class="h2link" href="#/products">${SCOPE === "product" ? "제품별" : "제품·제품군별"} 도입 학교 수</a><span class="note">막대를 눌러 학교 목록 보기</span></h2>${barChart(topTags, {drillFn: t => `/drill/tag/${encodeURIComponent(t)}`, labelFn: tagLabel})}</div>
      <div class="card"><h2>계열별 사례 수<span class="note">막대를 눌러 목록 보기</span></h2>${barChart(byType, {drillFn: t => `/drill/level/${encodeURIComponent(t)}`})}</div>
    </div>
    <div class="card"><h2><a class="h2link" href="#/regions">지역별 사례 수</a><span class="note">막대를 눌러 목록 보기</span></h2>${barChart(bySido, {drillFn: t => `/drill/sido/${encodeURIComponent(t)}`})}</div>`;
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
      <a href="#/products">제품 전체 보기</a> ·
      <a href="#/vendors">공급 기업</a> ·
      <a href="#/regions">지역별</a>에서 찾아보실 수 있습니다.</p>
      <p>있어야 할 기록이 없다면 <a href="#/contact">정정 요청</a>으로 알려 주세요.</p></div>`;
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

function schoolView(name) {
  let all = R.filter(r => r.school === name);
  if (!all.length) {
    // 옛 이름으로 들어온 경우 — 지금 교명의 화면을 보여 준다
    const old = R.find(r => r.origSchool === name);
    if (old) return schoolView(old.school);
    return notFound("학교", name, schools, c => `#/school/${encodeURIComponent(c)}`);
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
    <div class="crumb"><a href="#/">홈</a> › 학교 상세</div>
    <div class="pagehead"><h2>${esc(name)}${info.schoolName && info.schoolName !== name ? ` <span style="font-size:14px;font-weight:400;color:var(--muted)">현재 교명: ${esc(info.schoolName)}</span>` : ""}</h2>
      <div class="meta">${esc(info.type)} · ${esc(info.region)} · 기록 ${all.length}건
        ${info.schoolCode ? `<div class="conf">${[info.hsType, info.founding, info.neisAddress].filter(Boolean).map(esc).join(" · ")}</div>` : `<div class="conf">학교 기본정보를 찾지 못했습니다 — 집합 항목이거나 교명 확인이 필요합니다</div>`}
        ${oldNames.length ? `<div class="conf">옛 이름 ${oldNames.map(([o, n]) => `${esc(o)}(${n}건)`).join(" · ")}으로 계약된 기록이 함께 있습니다</div>` : ""}
        <div>${schoolTags.map(t => `<button type="button" class="chip${GENERIC_TAGS.has(t) ? " gen" : ""}${SCHOOL_TAG === t ? " on" : ""}"
          onclick="setSchoolTag('${t.replace(/'/g, "\\'")}')"
          title="${SCHOOL_TAG === t ? "누르면 전체 기록으로 돌아갑니다" : "이 학교의 해당 기록만 봅니다"}">${tagLabel(t)}</button>`).join("")}</div>
      </div></div>
    ${SCHOOL_TAG ? `<div class="fnote"><span>${esc(tagName(SCHOOL_TAG))} 기록 ${recs.length}건만 보는 중</span>
      <a href="javascript:void(0)" onclick="setSchoolTag('${SCHOOL_TAG.replace(/'/g, "\\'")}')">전체 ${all.length}건 보기</a>
      <a href="#/tag/${encodeURIComponent(SCHOOL_TAG)}">다른 학교의 도입 현황 ›</a></div>` : ""}
    <div class="card">${pagedTable(recs.slice().sort((a,b)=>(b.year||0)-(a.year||0)), {showSchool: false})}</div>`;
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
      `<a href="#/school/${encodeURIComponent(n)}">${esc(n)}</a>`).join("")}</div>
    <p class="cv">${esc(note.schoolNote || "")}</p></details>`;
}
// 조달 기록이 한 건도 없는 제품 — 무료이거나 개인이 사는 것이라 계약이 남지 않는다.
// 빈 화면을 보여 주면 '아무도 안 쓴다'로 읽히므로, 왜 없는지와 학교 밖 쓰임새를 함께 적는다.
function noProcView(tag) {
  const co = (NOPROC[tag] || {}).co || "";
  return `
    <div class="crumb"><a href="#/">홈</a> › <a href="#/no-record">조달 기록이 없는 제품</a> › 제품 상세</div>
    <div class="pagehead"><h2>${esc(tag)}${originOf(tag) ? ` <span class="obadge">${originOf(tag)}</span>` : ""}</h2>
      <div class="meta">조달 기록 <b>0건</b>${co ? ` · ${esc(co)}` : ""}</div></div>
    <div class="notice"><b>학교 예산으로 구매한 기록이 검색되지 않습니다</b>
      <p>무료로 사용하거나 교사·학생이 개인으로 결제하는 제품 등 학교 회계와 무관한 제품은
        조달 기록에 등재되지 않습니다. 교육청이 일괄로 구매하여 보급하는 경우도
        학교별 계약에서 탐색되지 않습니다.</p>
      <p class="cv">에듀테크 정보·체험 플랫폼(에듀집)에 등록된 제품인데, 저희가 수집한 계약건수에
        이름이 나오지 않습니다.
        <b style="display:inline;color:inherit">기록이 검색되지 않는다는 것은 사용하지 않는다는 뜻이 아닙니다.</b>
        본 서비스가 제공하지 않는 활용 현황이 있을 수 있습니다.</p></div>
    ${outsideCard(tag)}
    <div class="page"><p>비슷한 제품을 <a href="#/products">제품 전체 보기</a>에서 찾아보실 수 있습니다.
      조달 기록이 있는데 안 보인다면 <a href="#/contact">정정 요청</a>으로 알려 주세요.</p></div>`;
}

// 조달 기록은 없지만 학교 밖에서 쓰이는 제품 목록
function noProcListView() {
  const rows = Object.keys(NOPROC).map(n => {
    const o = OUTSIDE[n] || {};
    return {n, co: NOPROC[n].co || "", q: (o.q && o.q.n) || 0, inst: (o.app && o.app.inst) || ""};
  }).sort((a, b) => b.q - a.q || (b.inst ? 1 : 0) - (a.inst ? 1 : 0));
  return `
    <div class="crumb"><a href="#/">홈</a> › 조달 기록이 없는 제품</div>
    <div class="pagehead"><h2>조달 기록이 없는 제품</h2>
      <div class="sub2">에듀집에 등록돼 있지만 우리가 모은 계약 ${R.length.toLocaleString()}건에
        이름이 나오지 않는 제품입니다 · ${rows.length.toLocaleString()}종
        (그중 학교 밖 지표가 잡힌 것 ${rows.filter(r => r.q || r.inst).length.toLocaleString()}종)<br>
        무료이거나 교사·학생이 개인으로 결제하는 제품은 학교 회계를 거치지 않아 조달 기록이 없습니다 —
        <b>안 쓴다는 뜻이 아닙니다</b></div></div>
    <div class="card"><div class="tablewrap"><table><thead><tr>
      <th>제품</th><th>회사</th><th>월 검색수</th><th>앱 설치</th></tr></thead><tbody>
      ${rowSlice(rows).map(r => `<tr>
        <td><a href="#/tag/${encodeURIComponent(r.n)}">${esc(r.n)}</a></td>
        <td class="conf">${esc(r.co)}</td>
        <td style="white-space:nowrap">${r.q ? r.q.toLocaleString() : "—"}</td>
        <td style="white-space:nowrap">${esc(r.inst || "—")}</td></tr>`).join("")}
    </tbody></table></div>${rowPager(rows.length)}</div>`;
}

// 순위·목록 표의 페이지 넘김 — 계약 기록 표와 같은 20개씩으로 맞춘다
let ROWPAGE = 1;
window.setRowPage = n => { ROWPAGE = n; const y = window.scrollY; render(); window.scrollTo(0, y); };
function rowPager(total) {
  const pages = Math.ceil(total / PAGE_SIZE);
  if (pages <= 1) return "";
  const cur = Math.min(ROWPAGE, pages);
  const nums = [];
  for (let i = 1; i <= pages; i++)
    if (i === 1 || i === pages || Math.abs(i - cur) <= 2) nums.push(i);
    else if (nums[nums.length - 1] !== "…") nums.push("…");
  return `<div class="pager">
    <button onclick="setRowPage(${cur - 1})" ${cur <= 1 ? "disabled" : ""}>‹</button>
    ${nums.map(i => i === "…" ? `<span class="pgdots">…</span>`
      : `<button class="${i === cur ? "cur" : ""}" onclick="setRowPage(${i})">${i}</button>`).join("")}
    <button onclick="setRowPage(${cur + 1})" ${cur >= pages ? "disabled" : ""}>›</button></div>
    <div class="pginfo">전체 ${total.toLocaleString()}종 중 ${((cur - 1) * PAGE_SIZE + 1).toLocaleString()}–${Math.min(cur * PAGE_SIZE, total).toLocaleString()}종 표시</div>`;
}
const rowSlice = rows => rows.slice((Math.min(ROWPAGE, Math.max(1, Math.ceil(rows.length / PAGE_SIZE))) - 1) * PAGE_SIZE,
                                    Math.min(ROWPAGE, Math.max(1, Math.ceil(rows.length / PAGE_SIZE))) * PAGE_SIZE);

// 제품별 검색수 순위 — 한 제품의 숫자만 보면 많은지 적은지 알 수 없다.
// 조달 기록이 있는 제품과 없는 제품을 한 표에 놓아 견줄 수 있게 한다.
function bySearchView() {
  const schoolsOf = t => uniq(R.filter(r => !r.dup && r.tags.includes(t)).map(r => r.school)).length;
  const rows = Object.keys(OUTSIDE).map(n => {
    const o = OUTSIDE[n];
    return {n, q: (o.q && o.q.n) || 0, inst: (o.app && o.app.inst) || "",
            sch: NOPROC[n] ? -1 : schoolsOf(n), on: (o.q && o.q.on) || (o.app && o.app.on) || ""};
  }).filter(r => r.q > 0).sort((a, b) => b.q - a.q);
  return `
    <div class="crumb"><a href="#/">홈</a> › 제품별 검색수</div>
    <div class="pagehead"><h2>제품별 검색수</h2>
      <div class="sub2">네이버 검색광고 키워드도구의 <b>최근 한 달 검색수</b>(PC+모바일)입니다 · ${rows.length.toLocaleString()}종<br>
        조달 기록과는 다른 잣대라 도입 학교 수와 견주면 안 됩니다.
        이름이 흔한 제품은 다른 검색이 섞입니다${rows[0] && rows[0].on ? ` · ${esc(rows[0].on)} 확인` : ""}</div></div>
    <div class="card"><div class="tablewrap"><table><thead><tr>
      <th>순위</th><th>제품</th><th>월 검색수</th><th>앱 설치</th><th>도입 학교</th></tr></thead><tbody>
      ${rowSlice(rows).map((r, i) => `<tr>
        <td class="conf" style="min-width:44px">${((Math.min(ROWPAGE, Math.ceil(rows.length / PAGE_SIZE)) - 1) * PAGE_SIZE + i + 1).toLocaleString()}위</td>
        <td><a href="#/tag/${encodeURIComponent(r.n)}">${esc(tagName(r.n))}</a></td>
        <td style="white-space:nowrap"><b>${r.q.toLocaleString()}</b></td>
        <td style="white-space:nowrap">${esc(r.inst || "—")}</td>
        <td style="white-space:nowrap">${r.sch < 0
          ? `<span class="conf">조달 기록 없음</span>`
          : r.sch.toLocaleString() + "개교"}</td></tr>`).join("")}
    </tbody></table></div>${rowPager(rows.length)}</div>`;
}

function tagView(tag) {
  const recs = R.filter(r => r.tags.includes(tag));
  if (!recs.length && NOPROC[tag]) return noProcView(tag);
  if (!recs.length) return notFound("제품", tagName(tag), tags.map(([t]) => t), c => `#/tag/${encodeURIComponent(c)}`);
  const note = PLATFORM_NOTES[tag];
  const bySchoolType = count(recs, r => r.type);
  const bySido = count(recs, r => r.sido);
  return `
    <div class="crumb"><a href="#/">홈</a> › ${GENERIC_TAGS.has(tag) ? "제품군" : "제품"} 상세</div>
    <div class="pagehead"><h2>${tagLabel(tag)}${originOf(tag) ? ` <span class="obadge">${originOf(tag)}</span>` : ""}</h2>
      <div class="meta">${note ? "조달 기록상 " : "도입 학교 "}${uniq(recs.filter(r=>!r.dup).map(r=>r.school)).length}개교 · 기록 ${recs.filter(r=>!r.dup).length}건</div></div>
    ${note ? `<div class="notice"><b>공식 보급 플랫폼 안내</b><p>${note.body}</p><p class="cv">${note.caveat}</p>${noteSchoolList(note)}</div>` : ""}
    <div class="grid2">
      <div class="card"><h2>계열별<span class="note">막대를 눌러 목록 보기</span></h2>${barChart(bySchoolType, {drillFn: t => `/drill2/tt/${encodeURIComponent(tag)}/${encodeURIComponent(t)}`})}</div>
      <div class="card"><h2>지역별<span class="note">막대를 눌러 목록 보기</span></h2>${barChart(bySido.slice(0,10), {drillFn: t => `/drill2/ts/${encodeURIComponent(tag)}/${encodeURIComponent(t)}`})}</div>
    </div>
    ${outsideCard(tag)}
    ${vendorsOfTag(recs)}
    <div class="card"><h2>도입 학교 목록</h2>${pagedTable(recs)}</div>`;
}

// 이 제품을 학교에 넣은 회사 — 계약 상대자를 그대로 세어 보여 준다(추론이 아니다).
// 온라인몰·조달 대행은 만든 곳이 아니므로 따로 적는다.
// 조달 밖의 쓰임새 — 앱 설치 수와 검색량. 도입 학교 수와 성격이 다른 숫자라 따로 놓는다.
// '조달에 없다 = 안 쓴다'는 오해를 막는 것이 이 칸의 목적이다.
const OUTSIDE = DB.outside || {};
const NOPROC = DB.noProc || {};
function outsideCard(tag) {
  const o = OUTSIDE[tag];
  if (!o) return "";
  const bits = [];
  if (o.q) bits.push(`<a href="#/by-search"><b>월 검색 ${o.q.n.toLocaleString()}회</b></a>`
    + `<span class="conf"> · 네이버 최근 한 달 · 검색어 ‘${esc(o.q.word)}’</span>`);
  if (o.app) bits.push(`<b>앱 설치 ${esc(o.app.inst || "—")}</b><span class="conf"> · ${esc(o.app.n)}`
    + `${o.app.rate ? ` · 평점 ${esc(o.app.rate)}` : ""}${o.app.rev ? ` · 리뷰 ${Number(o.app.rev).toLocaleString()}` : ""}`
    + `${o.app.by ? ` · ${esc(o.app.by)}` : ""}</span>`);
  if (!bits.length) return "";
  return `<div class="card"><h2>검색·앱 지표<span class="note">에듀테크 제품의 활용도를 간접적으로 추정하기 위한 자료입니다 ·
      <a href="#/about">수집 방법</a></span></h2>
    <div class="outside">${bits.map(b => `<div>${b}</div>`).join("")}</div></div>`;
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
      `<a href="#/vendor/${encodeURIComponent(v.k)}">${esc(nameOf(v.k))}
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
                                    c => `#/vendor/${encodeURIComponent(vkey(c))}`);
  const nd = recs.filter(r => !r.dup);
  const kind = vendorKind(key);
  // 온라인몰·조달 대행·대형 제조사는 공급 기업이 아니다 — 화면을 만들지 않는다
  if (kind !== "공급 기업") return `
    <div class="crumb"><a href="#/">홈</a> › <a href="#/vendors">공급 기업</a></div>
    <div class="pagehead"><h2>${esc(e ? e.name : key)}</h2>
      <div class="meta">${kind}입니다 — 공급 기업으로 다루지 않습니다</div></div>
    <div class="page"><p class="lead">${kind === "구매 창구"
      ? "온라인몰·조달 대행처럼 여러 회사의 물건을 파는 창구입니다. 학교가 무엇을 샀는지는 기록에 남지만, 그 물건을 이 업체가 만든 것은 아니어서 공급 기업 통계에서 뺐습니다."
      : "여러 종류의 기기를 만드는 제조사입니다. 계약명에 제품이 적혀 있으면 그 제품으로 집계되므로, 제조사 단위로 묶어 보여 주지 않습니다."}</p>
      <p>기록은 <a href="#/products">제품별</a>이나 학교 화면에서 그대로 보실 수 있습니다.</p></div>`;
  const byTag = count(nd.flatMap(r => r.tags.map(t => [t])), x => x[0]).slice(0, 12);
  const bySido = count(nd, r => r.sido).slice(0, 10);
  const byType = count(nd, r => { const g = recLeaf(r); return g ? parentLabel[parentOf[g]] : "기타·미분류"; });
  const won = a => a >= 100000000 ? `${(a / 100000000).toFixed(1)}억원` : `${Math.round(a / 10000).toLocaleString()}만원`;
  const amt = nd.reduce((a, r) => a + (r.amt || 0), 0);
  return `
    <div class="crumb"><a href="#/">홈</a> › 공급 기업</div>
    <div class="pagehead"><h2>${esc(e ? e.name : key)}</h2>
      <div class="meta">${kind} · 거래 학교 ${uniq(nd.map(r => r.school)).length.toLocaleString()}개교 ·
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
    <div class="card"><h2>거래 기록</h2>${pagedTable(recs)}</div>`;
}

function vendorsView() {
  // 온라인몰·조달 대행·대형 제조사는 공급사가 아니라 사는 창구라 목록에서 뺀다
  const all = [...VENDORS.values()].filter(v => v.n >= 5).map(v => ({...v, kind: vendorKind(v.key)}));
  const rows = all.filter(v => v.kind === "공급 기업").sort((a, b) => b.n - a.n);
  const dropped = all.length - rows.length;
  const shown = rows;
  return `
    <div class="crumb"><a href="#/">홈</a> › 공급 기업 전체</div>
    <div class="pagehead"><h2>공급 기업</h2>
      <div class="sub2">계약 상대자로 5건 이상 나온 ${rows.length.toLocaleString()}곳 ·
        이름을 누르면 그 회사가 어느 학교에 무엇을 팔았는지 볼 수 있습니다<br>
        온라인몰·조달 대행·대형 제조사 ${dropped.toLocaleString()}곳은 제품을 만든 곳이 아니라
        사는 창구여서 뺐습니다</div></div>

    <div class="plist">
      ${shown.slice(0, 400).map(v => `<a href="#/vendor/${encodeURIComponent(v.key)}">${esc(v.name)}
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
      <div class="crumb"><a href="#/">홈</a> › <a href="#/vendors">공급 기업</a> ›
        <a href="#/vendor/${encodeURIComponent(tag)}">${esc(nm)}</a> ›
        ${kind === "vt" ? "제품" : kind === "vs" ? "지역" : "계열"} 상세</div>
      <div class="pagehead"><h2>${esc(nm)} · ${kind === "vt" ? tagLabel(value) : esc(value)}</h2>
        <div class="meta">이 회사가 납품한 기록만 봅니다 ·
          학교 ${uniq(nd.map(r => r.school)).length.toLocaleString()}개교 · 기록 ${nd.length.toLocaleString()}건
          ${kind === "vt" ? `<div class="conf"><a href="#/tag/${encodeURIComponent(value)}">${esc(tagName(value))} 전체 보기(다른 회사 포함) ›</a></div>` : ""}
        </div></div>
      <div class="card">${pagedTable(recs)}</div>`;
  }
  const recs = R.filter(r => r.tags.includes(tag) && (kind === "tt" ? r.type === value : r.sido === value));
  if (!recs.length) return `<div class="empty">해당 기록이 없습니다</div>`;
  const nSchools = uniq(recs.filter(r => !r.dup).map(r => r.school)).length;
  return `
    <div class="crumb"><a href="#/">홈</a> › <a href="#/tag/${encodeURIComponent(tag)}">${esc(tagName(tag))}</a> › ${kind === "tt" ? "계열" : "지역"} 상세</div>
    <div class="pagehead"><h2>${tagLabel(tag)} · ${esc(value)}</h2>
      <div class="meta">학교 ${nSchools}개교 · 기록 ${recs.length}건</div></div>
    ${kind === "level" && value === "고등학교" ? `<div class="card"><h2>고등학교 유형별<span class="note">막대를 눌러 목록 보기</span></h2>
      ${barChart(count(recs, r => { const g = recLeaf(r); return g ? parentLabel[parentOf[g]] : "기타·미분류"; }),
                 {drillFn: t => `/drill/group/${encodeURIComponent(t)}`})}</div>` : ""}
    <div class="card">${pagedTable(recs)}</div>`;
}
function codeView(code) {
  const s = idxByCode.get(code);
  if (!s) return notFound("학교", code, schools, c => `#/school/${encodeURIComponent(c)}`);
  const recs = R.filter(r => r.schoolCode === code);
  if (recs.length) {
    const names = uniq(recs.map(r => r.school));
    return schoolView(names[0]);
  }
  return `
    <div class="crumb"><a href="#/">홈</a> › 학교 상세</div>
    <div class="pagehead"><h2>${esc(s.n)}</h2>
      <div class="meta">${esc(s.l)}${s.h ? " · " + esc(s.h) : ""} · ${esc(s.s)}
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
  const nSchools = uniq(nd.map(r => r.school)).length;
  const conds = [];
  if (periodOn()) conds.push(`기간 ${(PF || "2020-01").replace("-", ".")} ~ ${(PT || "2026-07").replace("-", ".")}`);
  if (SF.size) conds.push(`계열 ${sfLabel()}`);
  if (ES.size) conds.push(`설립 주체 ${esLabel()}`);
  if (RG.size) conds.push(`지역 ${rgLabel()}`);
  return `
    <div class="crumb"><a href="#/">홈</a> › 통계 상세</div>
    <div class="pagehead"><h2>${what}</h2>
      <div class="meta">${conds.length ? "적용 조건: " + esc(conds.join(" · ")) + " · " : ""}학교 ${nSchools}개교 · 기록 ${nd.length.toLocaleString()}건</div></div>
    <div class="card">${pagedTable(recs)}</div>`;
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
  // 조달 기록이 없는 제품은 계약이 없으니 여기서 걸릴 수가 없다 — 이름이 맞으면 그 화면으로 보낸다
  const flat = x => (x || "").replace(/\s+/g, "").toLowerCase();
  const exact = Object.keys(NOPROC).find(n => flat(n) === flat(q));
  if (exact) return {hit: [], terms, words: null, fixed: null, goNoProc: exact};
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
  for (const [t] of tags) NAME_POOL.push([tagName(t), `#/tag/${encodeURIComponent(t)}`, "제품", tagName(t)]);
  for (const v of VENDORS.values()) if (v.n >= 3 && vendorKind(v.key) === "공급 기업")
    NAME_POOL.push([v.name, `#/vendor/${encodeURIComponent(v.key)}`, "회사", core(v.name) || v.name]);
  for (const s of schools) NAME_POOL.push([s, `#/school/${encodeURIComponent(s)}`, "학교", s]);
  return NAME_POOL;
}
const nearNames = (q, min) => namePool().map(p => [p, sim(q, p[3])])
  .filter(([, v]) => v >= min).sort((a, b) => b[1] - a[1]).map(([p]) => p);

function nearMisses(q) {
  const near = nearNames(q, 0.4).slice(0, 6);
  if (!near.length) return "";
  return `<div class="card"><h2>혹시 이것을 찾으셨나요</h2>
    <div class="plist">${near.map(([nm, href, kind]) =>
      `<a href="${href}">${esc(nm)}<span class="n">${kind}</span></a>`).join("")}</div></div>`;
}

function searchView(q) {
  const {hit, terms, words, fixed, goNoProc} = searchHits(q.toLowerCase());
  if (goNoProc) return noProcView(goNoProc);
  const recs = SCOPE === "product" ? hit.filter(hasProduct) : hit;
  const hidden = hit.length - recs.length;
  // 무상 보급·공동 운영 플랫폼은 검색으로 들어와도 한계 고지가 보여야 한다
  const noteKey = Object.keys(PLATFORM_NOTES).find(k =>
    terms.some(t => k.toLowerCase().includes(t) || t.includes(k.toLowerCase())));
  const note = noteKey ? PLATFORM_NOTES[noteKey] : null;
  return `
    <div class="crumb"><a href="#/">홈</a> › 검색 결과</div>
    <div class="pagehead"><h2>“${esc(q)}” 검색 결과</h2><div class="meta">${recs.length.toLocaleString()}건${fixed ? ` · <b>${esc(fixed[0])}</b>${euRo(fixed[0])} 고쳐 찾았습니다 · <a href="${fixed[1]}">${esc(fixed[0])} 페이지 보기 ›</a>` : words ? ` · 낱말을 나눠 찾았습니다 — ${words.map(esc).join(" · ")}를 모두 담은 기록` : terms.length > 1 ? ` · 유사 표기 포함: ${terms.filter(t => t !== q.toLowerCase()).map(esc).join(", ")}` : ""}${hidden ? ` · <a href="javascript:void(0)" onclick="document.getElementById('inclUnknown').click()">미확인 제품 ${hidden.toLocaleString()}건 더 보기</a>` : ""}</div></div>
    ${note ? `<div class="notice"><b>공식 보급 플랫폼 안내</b><p>${note.body}</p><p class="cv">${note.caveat}</p>${noteSchoolList(note)}
      <p class="cv"><a href="#/tag/${encodeURIComponent(noteKey)}">${esc(tagName(noteKey))} 페이지 보기 ›</a></p></div>` : ""}
    ${hit.length ? "" : nearMisses(q)}
    <div class="card">${pagedTable(recs)}</div>`;
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
  return `
    <div class="crumb"><a href="#/">홈</a> › 데이터 안내</div>
    <div class="page">
      <div class="page-intro">
        <div>
          <h2>데이터 안내</h2>
          <p>이 서비스는 공개된 조달 기록을 모아 전국 초·중·고등학교의 에듀테크 도입 현황을 보여줍니다.
          학교가 무엇을 계약했는지는 공개 정보지만 흩어져 있어 찾기 어렵기 때문에, 한곳에서 검색할 수 있게 정리했습니다.</p>
        </div>
        <img src="hero_person_m.png?v=2" width="239" height="186" alt="">
      </div>

      <h3>어디에서 모았나</h3>
      <div class="srcgrid">
        <div class="srccard"><b>나라장터</b><span>조달청 계약정보 공개 API — 학교가 맺은 물품·용역 계약</span></div>
        <div class="srccard"><b>S2B 학교장터</b><span>한국교직원공제회 운영 학교 조달 사이트 — 수의계약 전수 (입찰분 미포함)</span></div>
        <div class="srccard"><b>에듀집</b><span>교육부·한국교육학술정보원 — 에듀테크 제품 목록 및 학습지원 소프트웨어 등록 목록</span></div>
        <div class="srccard"><b>시도교육청 계약공개</b><span>학교 수의계약 내역 — 수만 원대 소액 구매까지 포함 (현재 인천·부산·대구·광주·대전·울산·충북·전남, 확대 예정)</span></div>
        <div class="srccard"><b>나이스 교육정보 개방 포털</b><span>교육부 — 전국 학교 명단·소재지 (12,666개교 등재)</span></div>
        <div class="srccard"><b>언론 보도·공식 자료</b><span>학교 홈페이지, 교육청 발표, 보도자료</span></div>
      </div>

      <h3>어떻게 판정하나</h3>
      <p>계약명 원문에서 제품명을 찾아 태그를 붙입니다.</p>
      <ul>
        <li>회사가 단일 제품을 공급하거나 회사명이 제품명인 경우에는 계약명에 제품이 없어도 그 제품으로 봅니다.</li>
        <li>한 회사가 여러 제품을 공급하는 경우, 계약명에 제품이 표시되지 않으면 <b>제품군</b>(코스웨어·기기·인프라·SW·플랫폼 등)으로만 남습니다. 이런 계약은 <b>회사명으로 검색</b>하면 함께 찾아볼 수 있습니다.</li>
        <li>교육·연수 운영, 행사·캠프, 차량 임차처럼 제품 도입이 아닌 계약은 집계에서 제외합니다.</li>
        <li>학교가 이름을 바꾼 경우 옛 이름으로 맺은 계약도 현재 학교로 합쳐 보여 줍니다. 계약명 원문은 그대로 보존합니다.</li>
      </ul>

      <div class="example">
        <b>예를 들면</b>
        <p class="ex-q">명진초등학교 · <span>“챗GPT 플러스 (ChatGPT Plus) 챗지피티4 3개월 구독 <b>외 3종</b>”</span></p>
        <ul>
          <li>이 계약에는 <b>ChatGPT</b> 태그 하나만 붙습니다. 계약명에 이름이 적힌 제품은 그것뿐이기 때문입니다.</li>
          <li>같은 제품이라도 표기는 제각각입니다(챗GPT · ChatGPT · 챗지피티). 어느 쪽으로 적혀 있든 <b>ChatGPT</b>로 모아 두므로, <b>한글로 검색하든 영문으로 검색하든</b> 같은 결과가 나옵니다.</li>
          <li><b>“외 3종”은 기록하지 않습니다.</b> 무엇을 함께 샀는지 계약명에 없어 확인할 방법이 없습니다. 이런 계약이 많아 실제 도입 제품은 여기 실린 것보다 많습니다.</li>
        </ul>
      </div>

      <h3>무엇이 빠지나</h3>
      <p>여기 실린 숫자는 <b>하한선</b>입니다. 기록이 없다는 것이 그 학교가 에듀테크를 쓰지 않는다는 뜻은 아닙니다.</p>
      <ul>
        <li>교육청이 무상으로 보급하는 플랫폼(하이러닝·바당 등)은 학교별 구매 기록이 남지 않습니다.</li>
        <li>해외 서비스 직접 결제, 교사 개인 결제, 소액 현장 구매는 조달 기록에 잡히지 않습니다. 다만 시도교육청 계약공개 자료를 수집한 지역에서는 일부 확인됩니다.</li>
      </ul>

      <h3 id="outside">검색·앱 지표는 어떻게 모았나</h3>
      <p>조달 기록만으로는 무료로 쓰거나 개인이 결제하는 제품이 보이지 않습니다.
        활용도를 <b>간접적으로 가늠하려고</b> 두 가지를 따로 모았습니다.
        조달 기록과 성격이 다른 숫자라 도입 학교 수와 나란히 두지 않았습니다.</p>
      <ul>
        <li><b>월 검색수</b> — 네이버 <a href="https://searchad.naver.com" target="_blank" rel="noopener">검색광고</a>가
          공개하는 키워드 도구(<code>/keywordstool</code>)에서 받습니다. 네이버 통합검색에서 그 낱말을 찾은
          <b>최근 한 달 횟수</b>이고, PC와 모바일을 더한 값입니다. 광고 성과가 아니라 검색 횟수입니다.
          제품 이름을 그대로 검색어로 넣되 괄호 안 설명은 뺍니다(<code>젭(ZEP)</code> → <code>젭</code>).
          네이버가 <code>&lt; 10</code>으로 돌려주면 열 번 미만이라는 뜻이라 0으로 적습니다.</li>
        <li><b>앱 설치·평점·리뷰</b> — 구글플레이 공개 페이지에서 받습니다. 제품 이름으로 검색해
          <b>제품 이름이 앱 이름 안에 그대로 들어 있는</b> 앱만 짝지었습니다.
          설치 수는 구글이 구간으로만 공개해 <code>10만+</code> 형태입니다.
          조달 기록이 없는 제품은 앱 하나가 유일한 근거라 이름이 거의 같을 때만 인정했습니다.</li>
      </ul>
      <p class="cv">한계가 분명합니다. <b>학교에서 쓴 것인지 가릴 수 없고</b>, 이름이 흔한 제품은
        다른 검색이 섞입니다(사람 이름과 겹치는 제품이 실제로 있습니다).
        앱이 없는 웹 서비스는 설치 수가 잡히지 않습니다.
        두 숫자 모두 <b>확인한 날짜의 값</b>이라 시간이 지나면 달라집니다.</p>

      <h3>수록 범위</h3>
      <ul>
        <li>조사 기간: <b>${esc(m.coveragePeriod || "2023.1 ~ 2026.7")}</b></li>
        <li>수록 기록: <b>${(m.total || 0).toLocaleString()}건</b> · 기록 보유 학교: <b>${(m.schools || 0).toLocaleString()}개교</b></li>
        <li>검색 가능 학교: <b>12,543개교</b> — 국내 공교육 전체</li>
        <li>학교 명단은 교육부 NEIS 개방 포털 기준입니다. 초·중·고 12,078개교에 더해
          특수학교 202개교, 각종학교 116개교, 평생학교 73개교, 방송통신 중·고 66개교,
          고등기술·고등공민학교 8개교를 포함합니다.
          등재된 12,666개교 중 <b>재외한국학교 79개교, 외국인·국제학교 33개교</b>는 국내 공교육이 아니어서,
          <b>공동실습소 9곳</b>은 학교가 아니어서 제외했습니다.</li>
      </ul>
      <p style="margin-top:18px">기록에 잘못된 내용이 있다면 <a href="#/contact">정정 요청</a>으로 알려 주세요.</p>
    </div>`;
}

let VLIST_KIND = "";                    // 공급 기업 목록에서 고른 갈래
// 제품 국적 — build_data.py가 product_origin.csv를 실어 보낸다 (근거는 그 파일에 남아 있다)
const ORIGIN = DB_RAW.origin || {};
const originOf = t => ORIGIN[t] || "";
let PORIGIN = "";                       // "" 전체 · 국내 · 해외
window.setPOrigin = v => { PORIGIN = v; const y = window.scrollY; render(); window.scrollTo(0, y); };
let PSORT = "count";                    // count = 도입 학교 순(순위표), name = 가나다순
function setPSort(v) { PSORT = v; const y = window.scrollY; render(); window.scrollTo(0, y); }

function productsView() {
  const cnt = {}, sch = {};
  const src = SCOPE === "product" ? baseRecs().filter(hasProduct) : baseRecs();
  for (const r of src) for (const t of r.tags) {
    if (SCOPE === "product" && GENERIC_TAGS.has(t)) continue;
    cnt[t] = (cnt[t] || 0) + 1;
    (sch[t] = sch[t] || new Set()).add(r.school);
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
    <div class="crumb"><a href="#/">홈</a> › 제품 전체 보기</div>
    <div class="pagehead"><h2>제품 전체 보기</h2>
      <div class="sub2">조달 기록에서 확인된 ${SCOPE === "product" ? "제품" : "제품·제품군"} ${names.length}종 ·
        이름을 누르면 도입 학교를 볼 수 있습니다${Object.keys(NOPROC).length
          ? `<br><a href="#/no-record">조달 기록이 없는 제품 ${Object.keys(NOPROC).length.toLocaleString()}종도 따로 보실 수 있습니다 ›</a>` : ""}
        </div>${filterNote()}</div>
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
      ${show.map(n => `<a href="#/tag/${encodeURIComponent(n)}">${tagLabel(n)}<span class="n">${sch[n].size.toLocaleString()}개교</span></a>`).join("")}
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
  for (const r of src) (sch[r.sido] = sch[r.sido] || new Set()).add(r.school);
  return `
    <div class="crumb"><a href="#/">홈</a> › 지역별 전체</div>
    <div class="pagehead"><h2>지역별 사례 수</h2>
      <div class="sub2">전국 ${rows.length}개 시도 ·
        ${SCOPE === "product" ? "제품이 확인된 기록" : "전체 기록"} 기준 · 막대를 눌러 목록을 볼 수 있습니다</div>${filterNote()}</div>
    <div class="card">${barChart(rows, {drillFn: t => `/drill/sido/${encodeURIComponent(t)}`})}</div>
    <div class="plist" style="margin-top:14px">
      ${rows.map(([s, n]) => `<a href="#/drill/sido/${encodeURIComponent(s)}">${esc(s)}
        <span class="n">${n.toLocaleString()}건 · ${(sch[s] ? sch[s].size : 0).toLocaleString()}개교</span></a>`).join("")}
    </div>
    ${etc.length ? `<p class="sub2" style="margin-top:14px">시도를 특정하지 못한 기록:
      ${etc.map(([s, n]) => `<a href="#/drill/sido/${encodeURIComponent(s)}">${esc(s)} ${n.toLocaleString()}건</a>`).join(" · ")}</p>` : ""}`;
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
    <div class="crumb"><a href="#/">홈</a> › 정정 요청</div>
    <div class="page">
      <h2>정정 요청 · 문의</h2>
      <p class="lead">이 서비스의 기록은 공개된 조달 자료를 자동으로 정리한 것이라 사실과 다른 부분이 있을 수 있습니다.
      잘못된 내용을 알려 주시면 확인 후 바로잡겠습니다.</p>

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
        <img src="contact_person.png?v=1" width="137" height="186" alt="">
      </div>
      <p style="margin-top:18px">데이터를 어떻게 모으고 판정하는지는 <a href="#/about">데이터 안내</a>에서 보실 수 있습니다.</p>
    </div>`;
}

let PLIST_G = "";
function render() {
  const seg = (location.hash.slice(1) || "/").split("/");
  const kind = seg[1];
  const arg = seg.length > 2 ? decodeURIComponent(seg.slice(2).join("/")) : undefined;
  const view = $("#view");
  if (kind === "school") view.innerHTML = schoolView(arg);
  else if (kind === "code") view.innerHTML = codeView(arg);
  else if (kind === "tag") view.innerHTML = tagView(arg);
  else if (kind === "drill") view.innerHTML = drillView(seg[2], decodeURIComponent(seg.slice(3).join("/")));
  else if (kind === "drill2") view.innerHTML = drillTagView(seg[2], decodeURIComponent(seg[3] || ""), decodeURIComponent(seg[4] || ""));
  else if (kind === "search") view.innerHTML = searchView(arg);
  else if (kind === "about") view.innerHTML = aboutView();
  else if (kind === "products") view.innerHTML = productsView();
  else if (kind === "no-record") view.innerHTML = noProcListView();
  else if (kind === "by-search") view.innerHTML = bySearchView();
  else if (kind === "regions") view.innerHTML = regionsView();
  else if (kind === "vendor") view.innerHTML = vendorView(arg);
  else if (kind === "vendors") view.innerHTML = vendorsView();
  else if (kind === "contact") view.innerHTML = contactView();
  else {
    view.innerHTML = homeView();
    animateCount();
  }
  // 현재 화면에 해당하는 상단 메뉴 강조
  document.querySelectorAll(".navlinks a").forEach(a =>
    a.classList.toggle("on", a.getAttribute("href") === `#/${kind || ""}`));
  // 히어로는 첫 화면에서만 크게, 하위 화면에서는 접어 둔다
  document.body.classList.toggle("sub-page", !!kind);
  // 검색창은 현재 화면의 검색 상태만 반영 — 검색 결과 페이지에서만 검색어 유지
  const qEl = document.querySelector("#q");
  if (qEl) qEl.value = kind === "search" ? (arg || "") : "";
  const sEl = document.querySelector("#sugg");
  if (sEl) sEl.hidden = true;
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", () => { PAGE = 1; ROWPAGE = 1; LISTQ = ""; SORTK = "new"; PLIST_G = ""; SCHOOL_TAG = ""; VLIST_KIND = ""; render(); });
perfMark("화면 코드 준비");
render();
perfMark("첫 화면 그리기");
// 요약 파일이 원자료와 어긋나면 첫 화면 수치가 뒤늦게 바뀐다 — ?perf=1일 때 미리 알려 준다
if (PERF && typeof DB_SUM !== "undefined") {
  const BASE = R.filter(r => !r.dup);
  const RF = BASE.filter(hasProduct);
  const tp = count(RF.flatMap(r => r.tags.map(t => [t])), x => x[0]);
  const names = tp.map(p => p[0]).filter(t => !GENERIC_TAGS.has(t));
  const tags = names.slice(0, 12)
    .map(t => [t, uniq(RF.filter(r => r.tags.includes(t)).map(r => r.school)).length])
    .sort((a, b) => b[1] - a[1]);
  if (JSON.stringify(tags) !== JSON.stringify(DB_SUM.home.product.tags))
    console.warn("[perf] data_summary.js가 원자료와 다릅니다 — node make_summary.js를 다시 돌리세요");
}

// ---- 자동완성 ----
const groupBySchool = {};
R.forEach(r => { if (!(r.school in groupBySchool)) groupBySchool[r.school] = recLeaf(r); });
perfMark("학교 색인");
const suggItems = [
  ...tags.map(([t]) => ({label: tagName(t), kind: GENERIC_TAGS.has(t) ? "제품군" : "제품", href: `#/tag/${encodeURIComponent(t)}`})),
  ...schools.map(s => ({label: s, kind: "학교·기록 있음", href: `#/school/${encodeURIComponent(s)}`, g: groupBySchool[s], rg: (R.find(r => r.school === s) || {}).sido})),
  ...IDX.filter(s => !recordCodes.has(s.c)).map(s => ({label: s.n, kind: `${s.s} ${s.h || s.l}`, href: `#/code/${s.c}`, g: idxGroup(s), rg: s.s})),
  ...[...VENDORS.values()].filter(v => v.n >= 5 && vendorKind(v.key) === "공급 기업")
     .map(v => ({label: v.name, kind: "공급 기업", href: `#/vendor/${encodeURIComponent(v.key)}`})),
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
  location.hash = i >= 0 ? current[i].href.slice(1) : `/search/${encodeURIComponent(q.value.trim())}`;
  sugg.hidden = true; q.blur();
});
q.addEventListener("keydown", e => {
  if (e.isComposing || e.keyCode === 229) return;  // 한글 IME 조합 중 Enter/방향키 무시 (글자 중복 방지)
  if (sugg.hidden) { if (e.key === "Enter" && q.value.trim()) { location.hash = `/search/${encodeURIComponent(q.value.trim())}`; } return; }
  const n = current.length;
  if (e.key === "ArrowDown") { selIdx = (selIdx + 1) % n; }
  else if (e.key === "ArrowUp") { selIdx = (selIdx - 1 + n) % n; }
  else if (e.key === "Enter") {
    location.hash = selIdx >= 0 ? current[selIdx].href.slice(1) : `/search/${encodeURIComponent(q.value.trim())}`;
    sugg.hidden = true; q.blur(); return;
  } else if (e.key === "Escape") { sugg.hidden = true; return; }
  else return;
  e.preventDefault();
  [...sugg.children].forEach((el, i) => el.classList.toggle("sel", i === selIdx));
});
document.addEventListener("click", e => { if (!e.target.closest(".searchwrap")) sugg.hidden = true; });
