// Natural-language search results page.
// Flow:
// 1. Echo the query, show skeleton results + AI thinking dots.
// 2. Call window.claude.complete with the query + a compact bill list.
// 3. Parse {intro, ids[], keywords[], followups[]} JSON; fall back to keyword scoring.
// 4. Type-out the AI answer, populate keywords, render result cards with 3D hover.
// 5. Show category-refine chips, follow-up questions, and a feedback row.

const EXAMPLE_QUERIES = [
  "최근 청년 월세와 관련된 법안은 뭐가 있어?",
  "노동자 보호를 강화하는 법안 알려줘",
  "올해 환경·기후 분야 주요 법안은?",
  "소상공인을 위한 법안 있어?",
  "교육 분야에서 최근 올라온 법안",
  "1인 가구·독거 보건 관련 법안",
];

const FOLLOWUP_LIBRARY = [
  { tag: "왜", q: "이 법안이 통과되면 시민에게 어떤 영향이 있어?" },
  { tag: "비교", q: "비슷한 외국 사례는 어떤 게 있어?" },
  { tag: "쟁점", q: "이 법안에 반대하는 입장은 뭐야?" },
  { tag: "일정", q: "다음 심사 일정은 언제야?" },
  { tag: "발의자", q: "이 법안을 발의한 의원은 누구야?" },
  { tag: "이력", q: "비슷한 법안이 과거에도 있었어?" },
];

let lastSearchState = { all: [], filteredCat: "all", query: "" };

function allBillsForSearch() {
  const set = {};
  PICKS.forEach(p => set[p.id] = { id: p.id, title: p.title, sum: p.summary[0], cats: p.cats.map(c=>c.label).join(",") });
  BILLS.forEach(b => { if (!set[b.id]) set[b.id] = { id: b.id, title: b.title, sum: b.summary[0], cats: b.cats.map(c=>c.label).join(",") }; });
  return Object.values(set);
}

function keywordFallback(query, list) {
  const q = query.toLowerCase();
  const tokens = q.replace(/[?!.,]/g, "").split(/\s+/).filter(t => t.length > 1);
  const scored = list.map(b => {
    const hay = (b.title + " " + b.sum + " " + b.cats).toLowerCase();
    let s = 0;
    if (hay.includes(q)) s += 5;
    tokens.forEach(t => { if (hay.includes(t)) s += 1; });
    return { ...b, s };
  }).filter(x => x.s > 0).sort((a,b) => b.s - a.s).slice(0, 5);
  return scored.length ? scored : list.slice(0, 3);
}

function extractKeywords(query, matchedBills) {
  // Build keyword pills from query tokens + matched categories
  const stop = new Set(["관련","최근","있어","있나요","뭐가","뭐","어떤","좀","알려줘","올해","주요","법안","법안은","법안이","법안을"]);
  const tokens = query.replace(/[?!.,·]/g, " ").split(/\s+/)
    .map(t => t.trim())
    .filter(t => t.length > 1 && !stop.has(t));
  const cats = new Set();
  matchedBills.forEach(b => (b.cats || []).forEach(c => cats.add(c.label)));
  const out = [];
  tokens.slice(0, 3).forEach(t => out.push(t));
  [...cats].slice(0, 4).forEach(c => { if (!out.includes(c)) out.push(c); });
  return out.slice(0, 6);
}

function pickFollowups(matchedBills) {
  // Rotate suggestions, biased by which categories appear
  const shuffled = [...FOLLOWUP_LIBRARY].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

async function nlSearch(query) {
  const list = allBillsForSearch();
  const compact = list.map(b => `- ${b.id} | ${b.title} | ${b.cats} | ${b.sum.slice(0,60)}`).join("\n");
  const prompt = `당신은 시민에게 한국 법안을 친근하게 큐레이션하는 '슥법'의 AI 어시스턴트입니다.

사용자 질문: "${query}"

아래 법안 목록에서 질문과 가장 관련있는 3-5개를 골라 id를 나열하고, 친근한 반말로 2-3문장 요약해주세요.
${compact}

반드시 이 JSON 형식으로만 응답하세요 (다른 텍스트 절대 금지):
{"intro":"친근한 2-3문장 한국어 답변","ids":["id1","id2","id3"]}`;

  try {
    const res = await window.claude.complete(prompt);
    const m = res.match(/\{[\s\S]*\}/);
    if (m) {
      const obj = JSON.parse(m[0]);
      const validIds = (obj.ids || []).filter(id => ALL_BY_ID[id]);
      if (validIds.length && obj.intro) return { intro: obj.intro, ids: validIds.slice(0,5) };
    }
  } catch (e) { console.warn("AI search fallback:", e); }

  const matched = keywordFallback(query, list);
  return {
    intro: `"${query}"와(과) 관련된 법안 ${matched.length}건을 슥 찾아봤어요. 카드를 눌러 더 자세히 확인해보세요.`,
    ids: matched.map(b => b.id)
  };
}

function showSkeleton() {
  const grid = $("#searchGrid");
  const spans = ["span-3","span-3","span-2","span-2","span-2"];
  grid.innerHTML = spans.map(sp => `
    <article class="card skel ${sp}">
      <div class="skel-row" style="gap:8px;">
        <div class="skel-line tag"></div>
        <div class="skel-line tag" style="width: 40px;"></div>
      </div>
      <div class="skel-stack">
        <div class="skel-line lg w90"></div>
        <div class="skel-line lg w70"></div>
      </div>
      <div class="skel-stack" style="gap: 6px; margin-top: 4px;">
        <div class="skel-line w90"></div>
        <div class="skel-line w70"></div>
      </div>
      <div class="skel-row" style="margin-top: auto; padding-top: 12px;">
        <div class="skel-line w40"></div>
      </div>
    </article>
  `).join("");
}

function renderRefineChips(matched) {
  const counts = {};
  matched.forEach(b => (b.cats || []).forEach(c => { counts[c.label] = (counts[c.label] || 0) + 1; }));
  const chips = [
    { label: "전체", count: matched.length, key: "all" },
    ...Object.entries(counts).map(([label, count]) => ({ label, count, key: label })),
  ];
  $("#refineChips").innerHTML = chips.map((c,i) => `
    <button class="refine-chip ${c.key === lastSearchState.filteredCat ? 'active' : ''}" data-key="${c.key}" style="animation-delay: ${i*40}ms">
      ${c.label}
      <span class="rc-count">${c.count}</span>
    </button>
  `).join("");
  $$(".refine-chip").forEach(el => {
    el.addEventListener("click", () => {
      lastSearchState.filteredCat = el.dataset.key;
      renderResults();
    });
  });
}

function renderResults() {
  const grid = $("#searchGrid");
  let visible = lastSearchState.all;
  if (lastSearchState.filteredCat !== "all") {
    visible = visible.filter(b => (b.cats || []).some(c => c.label === lastSearchState.filteredCat));
  }
  $("#resultsTitle").textContent = `관련 법안 ${visible.length}건`;
  $("#resultsSub").textContent = lastSearchState.filteredCat === "all"
    ? "관련도 순으로 정렬했어요. 카드 위에 마우스를 올리면 슥 따라와요."
    : `"${lastSearchState.filteredCat}" 분야로 좁혔어요.`;

  if (!visible.length) {
    grid.innerHTML = `<div style="grid-column: span 6; padding: 48px 0; color: var(--ink-3); font-size: 14px; text-align: center;">선택한 분야에 해당하는 결과가 없어요.</div>`;
    return;
  }

  const spanCycle = ["span-3","span-3","span-2","span-2","span-2"];
  grid.innerHTML = visible.map((b,idx) => {
    const span = spanCycle[idx] || "span-2";
    const ghost = { ...b, span, compact: span === "span-2" };
    return cardHTML(ghost, idx);
  }).join("");
  $$(".card", grid).forEach(el => {
    bindCard3D(el);
    el.addEventListener("click", (e) => {
      if (e.target.closest(".bookmark")) return;
      openModal(el.dataset.id);
    });
  });
  $$(".bookmark", grid).forEach(b => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = b.dataset.id;
      if (savedSet.has(id)) savedSet.delete(id); else savedSet.add(id);
      renderResults();
    });
  });
}

function renderFollowups() {
  const items = pickFollowups();
  $("#followupChips").innerHTML = items.map((f, i) => `
    <button class="followup-chip" data-q="${f.q.replace(/"/g,'&quot;')}" style="animation-delay: ${i*60}ms">
      <span class="fc-q">${f.tag}</span>
      <span>${f.q}</span>
      <svg class="fc-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
    </button>
  `).join("");
  $$("#followupChips .followup-chip").forEach(el => {
    el.addEventListener("click", () => {
      location.hash = `#/search?q=${encodeURIComponent(el.dataset.q)}`;
    });
  });
}

function bindFeedback() {
  $$("#feedback .fb-btn").forEach(btn => {
    btn.onclick = () => {
      $$("#feedback .fb-btn").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      const label = $("#feedback .feedback-label");
      const kind = btn.dataset.fb;
      label.textContent = kind === "up" ? "고마워요! 더 잘 훑어볼게요." :
                         kind === "down" ? "아쉬워요. 어떤 부분이 부족했는지 알려주세요." :
                         "신고 접수했어요. 검토 후 반영할게요.";
    };
  });
}

async function renderSearch(query) {
  $("#queryEcho").textContent = query || "—";
  $("#searchInput2").value = query;
  const aiText = $("#aiText");
  const startedAt = performance.now();

  // reset UI
  aiText.innerHTML = `<span style="color:var(--ink-3)">슥, 법안을 훑어보고 있어요</span><span class="ai-loading-dots"><span>•</span><span>•</span><span>•</span></span>`;
  $("#aiBadge").textContent = "검색 중…";
  $("#aiKeywords").innerHTML = "";
  $("#metaCount").textContent = "—";
  $("#metaTime").textContent = "—";
  $("#refineChips").innerHTML = "";
  renderExamples();
  renderFollowups();
  bindFeedback();

  if (!query) {
    aiText.innerHTML = `<span style="color:var(--ink-3)">위 검색창에 자연어로 질문을 적거나, 아래 예시를 눌러보세요.</span>`;
    $("#aiBadge").textContent = "대기 중";
    $("#searchGrid").innerHTML = "";
    $("#resultsTitle").textContent = "관련 법안";
    $("#resultsSub").textContent = "질문을 입력하면 슥법이 관련 법안을 찾아 드려요.";
    lastSearchState = { all: [], filteredCat: "all", query: "" };
    return;
  }

  showSkeleton();

  let result;
  try {
    result = await nlSearch(query);
  } catch (e) {
    result = { intro: "지금은 결과를 불러올 수 없어요. 잠시 뒤 다시 시도해주세요.", ids: [] };
  }

  const elapsed = ((performance.now() - startedAt) / 1000).toFixed(2);
  const matched = result.ids.map(id => ALL_BY_ID[id]).filter(Boolean);

  // state
  lastSearchState = { all: matched, filteredCat: "all", query };

  // meta
  $("#metaCount").textContent = matched.length;
  $("#metaTime").textContent = elapsed;
  $("#aiBadge").innerHTML = matched.length
    ? `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg> 법안 ${matched.length}건 참조`
    : "참조 없음";

  // keywords
  const kws = extractKeywords(query, matched);
  $("#aiKeywords").innerHTML = kws.map((k,i) => `<button class="ai-kw" data-k="${k}" style="animation-delay:${100 + i*45}ms">${k}</button>`).join("");
  $$(".ai-kw").forEach(el => el.addEventListener("click", () => {
    location.hash = `#/search?q=${encodeURIComponent(el.dataset.k)}`;
  }));

  // refine chips
  renderRefineChips(matched);

  // results
  if (!matched.length) {
    $("#searchGrid").innerHTML = `<div style="grid-column: span 6; padding: 48px 0; color: var(--ink-3); font-size: 14px; text-align: center;">관련 법안을 찾지 못했어요. 다른 키워드로 다시 물어보세요.</div>`;
    $("#resultsTitle").textContent = "관련 법안 0건";
  } else {
    renderResults();
  }

  // typewriter answer (last so cards appear before/while text types)
  aiText.textContent = "";
  const text = result.intro;
  let i = 0;
  const step = () => {
    if (i >= text.length) {
      aiText.innerHTML = text + `<span class="blink"></span>`;
      return;
    }
    aiText.textContent = text.slice(0, i+1);
    i += 1;
    setTimeout(step, 18 + Math.random()*22);
  };
  step();
}

function renderExamples() {
  $("#exampleChips").innerHTML = EXAMPLE_QUERIES.map((q,i) => `
    <button class="example-chip" data-q="${q.replace(/"/g,'&quot;')}">
      <span class="ec-mark">슥</span>
      <span>${q}</span>
    </button>
  `).join("");
  $$("#exampleChips .example-chip").forEach(el => {
    el.addEventListener("click", () => {
      const q = el.dataset.q;
      location.hash = `#/search?q=${encodeURIComponent(q)}`;
    });
  });
}
