// Bill-detail modal. openModal(id) reads from backend API dynamically.
async function openModal(id) {
  const root = $("#modalRoot");
  
  // 1. Render loading skeleton state immediately
  root.innerHTML = `
    <div class="modal-overlay" id="ov">
      <div class="modal" role="dialog" aria-modal="true" style="min-height: 220px; display: flex; align-items: center; justify-content: center;">
        <div style="text-align: center; color: var(--ink-3);">
          <span style="font-size: 14px; font-weight: 500;">슥 법안 상세 정보를 불러오고 있어요...</span>
          <div class="ai-loading-dots" style="margin-top: 12px;"><span>•</span><span>•</span><span>•</span></div>
        </div>
      </div>
    </div>
  `;
  
  const close = () => { root.innerHTML = ""; document.body.style.overflow = ""; };
  document.body.style.overflow = "hidden";
  $("#ov").addEventListener("click", (e) => { if (e.target.id === "ov") close(); });
  
  try {
    // 2. Fetch fresh detailed bill data from the backend
    const raw = await fetchJson(`/api/bills/${id}`);
    const b = normalizeBill(raw);
    
    // Cache it back to the global index
    ALL_BY_ID[b.id] = b;
    
    const stage = STAGES[b.stage] || STAGES.proposed;
    const stageOrder = ["proposed","committee","plenary","passed"];
    
    // 3. Render the dynamic detailed modal content
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
                <span><b>법안번호</b> 의안 ${(raw.billNo || "22-0000")}</span>
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
                <div style="font-size: 12.5px; color: var(--ink-3);">조회수 ${(raw.viewCount || raw.view_count || b.comments || 0)}회</div>
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
              <ul>${b.summary.length ? b.summary.map(s => `<li>${s}</li>`).join("") : '<li>AI 요약 정보가 존재하지 않거나 준비 중입니다.</li>'}</ul>
            </div>
            <div class="modal-section">
              <h4>예상 영향</h4>
              <p>${b.impact || "해당 법안의 예상 영향 정보가 제공되지 않습니다."}</p>
            </div>
            ${(b.similar && b.similar.length) ? `
            <div class="modal-section">
              <h4>유사 법안 ${b.similar.length}건</h4>
              <div class="similar">
                ${b.similar.map(s => `
                  <div class="similar-item">
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
              <button class="btn btn-primary" id="modalBookmarkBtn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>
                북마크
              </button>
              <button class="btn btn-ghost" id="modalShareBtn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.9 4M15.5 6.5l-6.9 4"/></svg>
                공유
              </button>
              <button class="btn btn-ghost" id="modalSourceBtn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
                원문 보기
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Wire modal events
    $("#ov").addEventListener("click", (e) => { if (e.target.id === "ov") close(); });
    $("#closeBtn").addEventListener("click", close);
    
    $("#modalShareBtn").addEventListener("click", () => {
      alert("링크가 클립보드에 복사되었습니다! (시안)");
    });
    
    $("#modalSourceBtn").addEventListener("click", () => {
      const link = raw.detailLink || raw.detail_link;
      if (link) {
        window.open(link, "_blank");
      } else {
        alert("원문 링크가 존재하지 않습니다.");
      }
    });
    
    const bookmarkBtn = $("#modalBookmarkBtn");
    const updateBookmarkStyle = () => {
      const saved = savedSet.has(b.id);
      bookmarkBtn.classList.toggle("saved", saved);
      bookmarkBtn.innerHTML = saved
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 3a2 2 0 0 0-2 2v16l8-4 8 4V5a2 2 0 0 0-2-2H6z"/></svg> 저장됨'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg> 북마크';
    };
    updateBookmarkStyle();
    bookmarkBtn.addEventListener("click", () => {
      if (savedSet.has(b.id)) savedSet.delete(b.id); else savedSet.add(b.id);
      updateBookmarkStyle();
      
      // Sync styles in behind grids
      const currentRoute = routeFromHash();
      if (currentRoute === "latest") renderGrid();
      if (currentRoute === "search") renderSearch(getQuery());
    });

  } catch (error) {
    console.error("Failed to load bill detail from API:", error);
    root.innerHTML = `
      <div class="modal-overlay" id="ov">
        <div class="modal" role="dialog" aria-modal="true" style="min-height: 200px; padding: 24px; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center;">
          <h3 style="margin-bottom: 12px; color: var(--accent-ink);">법안 정보를 가져오지 못했습니다</h3>
          <p style="color: var(--ink-3); font-size: 13.5px; margin-bottom: 20px;">서버와의 연결이 원활하지 않거나 데이터가 존재하지 않습니다.</p>
          <button class="btn btn-primary" id="errorCloseBtn" style="padding: 8px 24px;">닫기</button>
        </div>
      </div>
    `;
    $("#ov").addEventListener("click", (e) => { if (e.target.id === "ov") close(); });
    $("#errorCloseBtn").addEventListener("click", close);
  }
  
  document.addEventListener("keydown", function esc(e){ if (e.key === "Escape") { close(); document.removeEventListener("keydown", esc); } });
}


