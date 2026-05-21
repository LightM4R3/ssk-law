// Bill-detail modal. openModal(id) reads from ALL_BY_ID (see state.js).
function openModal(id) {
  const b = ALL_BY_ID[id];
  if (!b) return;
  const stage = STAGES[b.stage];
  const stageOrder = ["proposed","committee","plenary","passed"];
  const root = $("#modalRoot");
  root.innerHTML = `
    <div class="modal-overlay" id="ov">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <div class="tag-row" style="margin-bottom: 6px;">
              ${b.cats.map(c => `<span class="tag ${c.accent?'accent':''}">${c.label}</span>`).join("")}
            </div>
            <h2>${b.title}</h2>
            <div class="modal-meta">
              <span><b>발의일</b> ${b.proposedAt}</span>
              <span><b>대표 발의</b> ${b.proposer}</span>
              <span><b>법안번호</b> 의안 2126-${(b.id||"").toUpperCase()}</span>
            </div>
          </div>
          <button class="close" id="closeBtn" aria-label="닫기">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="modal-stage">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px;">
              <div style="font-weight:700; font-size: 14px;">현재 단계 · <span style="color:var(--accent-ink)">${stage.label}</span></div>
              <div style="font-size: 12.5px; color: var(--ink-3);">최근 업데이트 2026.05.13</div>
            </div>
            <div class="stage-track">
              ${stageOrder.map((s,i) => `<div class="stage-step ${i<stage.idx?'done':''} ${i===stage.idx?'active':''}"></div>`).join("")}
            </div>
            <div class="stage-labels">
              ${stageOrder.map((s,i) => `<span class="${i===stage.idx?'active':''}">${STAGES[s].label}</span>`).join("")}
            </div>
          </div>
          <div class="modal-section">
            <h4>세 줄 요약</h4>
            <ul>${b.summary.map(s => `<li>${s}</li>`).join("")}</ul>
          </div>
          <div class="modal-section">
            <h4>예상 영향</h4>
            <p>${b.impact}</p>
          </div>
          ${(b.similar && b.similar.length) ? `
          <div class="modal-section">
            <h4>유사 법안 ${b.similar.length}건</h4>
            <div class="similar">
              ${b.similar.map((s, si) => `
                <div class="similar-item" data-parent="${b.id}" data-idx="${si}">
                  <div>
                    <div class="similar-title">${s.title}</div>
                    <div class="similar-meta">${s.date} · ${s.stage}</div>
                  </div>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--ink-4);"><path d="M9 18l6-6-6-6"/></svg>
                </div>
              `).join("")}
            </div>
          </div>` : ''}
          <div class="modal-actions">
            <button class="btn btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>
              북마크
            </button>
            <button class="btn btn-ghost">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.9 4M15.5 6.5l-6.9 4"/></svg>
              공유
            </button>
            <button class="btn btn-ghost">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
              원문 보기
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  const close = () => { root.innerHTML = ""; document.body.style.overflow = ""; };
  document.body.style.overflow = "hidden";
  $("#ov").addEventListener("click", (e) => { if (e.target.id === "ov") close(); });
  $("#closeBtn").addEventListener("click", close);
  // similar-item click: open the dedicated similar modal
  $$(".similar-item", root).forEach(el => {
    el.addEventListener("click", () => {
      close();
      openSimilarModal(el.dataset.parent, +el.dataset.idx);
    });
    el.style.cursor = "pointer";
  });
  document.addEventListener("keydown", function esc(e){ if (e.key === "Escape") { close(); document.removeEventListener("keydown", esc); } });
}

