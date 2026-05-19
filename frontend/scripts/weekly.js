// "이번 주 가장 많이 슥본 법안" Top-10 ranking list.
// Depends on: data.js (WEEKLY), modal.js
function renderWeekly() {
  const wrap = $("#weeklyList");
  wrap.innerHTML = WEEKLY.map((w,i) => `
    <article class="weekly-row" data-id="${w.ref}" style="--delay: ${i*45}ms">
      <div class="weekly-rank">${String(w.rank).padStart(2,'0')}</div>
      <div class="weekly-body">
        <div class="weekly-cats">${w.cats.map(c => `<span class="tag ${c.accent?'accent':''}">${c.label}</span>`).join("")}</div>
        <div class="weekly-title">${w.title}</div>
        <div class="weekly-snip">${w.snip}</div>
      </div>
      <div class="weekly-stats">
        <div class="weekly-views">${(w.view/1000).toFixed(1)}k</div>
        <div>조회 · 이번 주</div>
        <div class="weekly-trend ${w.down?'down':''}">${w.trend}</div>
      </div>
      <div class="weekly-go">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
      </div>
    </article>
  `).join("");
  $$(".weekly-row", wrap).forEach(el => el.addEventListener("click", () => openModal(el.dataset.id)));
}

