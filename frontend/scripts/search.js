// Natural-language search results page.
// Hits window.claude.complete with the question + a compact bill list, parses {intro, ids} JSON,
// falls back to a keyword-scoring search if the model call fails or returns malformed output.
const EXAMPLE_QUERIES = [
  "최근 청년 월세와 관련된 법안은 뭐가 있어?",
  "노동자 보호를 강화하는 법안 알려줘",
  "올해 환경·기후 분야 주요 법안은?",
  "소상공인을 위한 법안 있어?",
  "교육 분야에서 최근 올라온 법안",
  "1인 가구·독거 보건 관련 법안",
];

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
  }).filter(x => x.s > 0).sort((a,b) => b.s - a.s).slice(0, 4);
  return scored.length ? scored : list.slice(0, 3);
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

async function renderSearch(query) {
  $("#queryEcho").textContent = query || "—";
  $("#searchInput2").value = query;
  const aiText = $("#aiText");
  const grid = $("#searchGrid");
  aiText.innerHTML = `<span style="color:var(--ink-3)">슥, 법안을 훑어보고 있어요</span><span class="ai-loading-dots"><span>•</span><span>•</span><span>•</span></span>`;
  grid.innerHTML = `<div style="grid-column: span 6; padding: 32px 0; color: var(--ink-4); font-size: 13.5px; text-align: center;">슥 결과를 불러오는 중…</div>`;
  renderExamples();

  if (!query) {
    aiText.innerHTML = `<span style="color:var(--ink-3)">질문을 입력해 주세요.</span>`;
    grid.innerHTML = "";
    return;
  }

  let result;
  try {
    result = await nlSearch(query);
  } catch (e) {
    result = { intro: "지금은 결과를 불러올 수 없어요. 잠시 뒤 다시 시도해주세요.", ids: [] };
  }

  // typewriter-ish reveal
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

  // render result cards
  const matched = result.ids.map(id => ALL_BY_ID[id]).filter(Boolean);
  $("#resultsTitle").textContent = `관련 법안 ${matched.length}건`;
  if (!matched.length) {
    grid.innerHTML = `<div style="grid-column: span 6; padding: 48px 0; color: var(--ink-3); font-size: 14px; text-align: center;">관련 법안을 찾지 못했어요. 다른 키워드로 다시 물어보세요.</div>`;
    return;
  }
  // give matched bills appropriate spans for magazine feel
  const spanCycle = ["span-3","span-3","span-2","span-2","span-2"];
  grid.innerHTML = matched.map((b,idx) => {
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
      renderSearch(query);
    });
  });
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

