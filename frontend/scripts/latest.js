// "슥 훑어보는 최신 법안" page: category chips + magazine grid.
// Depends on: data.js (CATEGORIES, BILLS, STAGES), state.js, modal.js, card3d.js
function renderFilters() {
  const wrap = $("#filters");
  wrap.innerHTML = CATEGORIES.map((c,i) => `
    <button class="chip ${c.id===activeCat?'active':''}" data-cat="${c.id}" style="animation-delay: ${i*40}ms">
      ${c.id==="all" ? '' : '<span class="dot"></span>'}
      ${c.label}
      <span class="count">${c.count}</span>
    </button>
  `).join("");
  $$(".chip", wrap).forEach(btn => {
    btn.addEventListener("click", () => {
      activeCat = btn.dataset.cat;
      renderFilters();
      renderGrid();
    });
  });
}

function billMatchesFilter(b) {
  if (activeCat === "all") return true;
  return b.cats.some(c => c.k === activeCat);
}

function renderGrid() {
  renderFilters();
  const grid = $("#grid");
  const visible = BILLS.filter(billMatchesFilter);
  if (!visible.length) {
    grid.innerHTML = `<div style="grid-column: span 6; padding: 64px 0; text-align:center; color: var(--ink-3); font-size: 14.5px;">해당 분야에서 최근 발의된 법안이 아직 없어요.</div>`;
    return;
  }
  grid.innerHTML = visible.map((b,i) => cardHTML(b,i)).join("");
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
      renderGrid();
    });
  });
}

function cardHTML(b, i) {
  const stage = STAGES[b.stage];
  const saved = savedSet.has(b.id);
  return `
    <article class="card ${b.span} ${b.compact?'compact':''}" data-id="${b.id}" style="--delay: ${Math.min(i,9) * 55}ms">
      <div class="card-shine"></div>
      <button class="bookmark ${saved?'saved':''}" data-id="${b.id}" aria-label="저장">
        ${saved
          ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 3a2 2 0 0 0-2 2v16l8-4 8 4V5a2 2 0 0 0-2-2H6z"/></svg>'
          : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>'}
      </button>
      <div class="card-meta">
        <div class="tag-row">${b.cats.map(c => `<span class="tag ${c.accent?'accent':''}">${c.label}</span>`).join("")}</div>
      </div>
      <h3>${b.title}</h3>
      <div class="summary">${b.summary.slice(0, b.compact?2:3).map(s => `• ${s}`).join("<br/>")}</div>
      <div class="card-foot">
        <span class="stage"><span class="stage-dot ${stage.cls}"></span>${stage.label}</span>
        <span class="suk-hint">슥 훑어보기 →</span>
        <span class="foot-date">${b.proposedAt}</span>
      </div>
    </article>
  `;
}

