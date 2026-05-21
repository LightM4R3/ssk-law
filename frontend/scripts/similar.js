// Similar-bills detail page (#/picks/:id/similar) + similar-bill modal.
// Similar bills carry sparse data ({title, date, stage}) — they are not full
// bills in BILLS/PICKS, so they get their own modal that is honest about the
// limited info and links back to the parent (original) bill.
//
// Depends on: data.js (PICKS, BILLS, STAGES, CATEGORY_META), state.js, modal.js.

/* Map the short stage label used inside similar items ("위원회", "본회의",
   "통과") back to a STAGES key. The main bills use the long form ("위원회 심사"
   etc.) — fuzzy-match instead of a strict lookup. */
function stageKeyFromLabel(label) {
  if (!label) return "proposed";
  if (label.includes("발의")) return "proposed";
  if (label.includes("위원")) return "committee";
  if (label.includes("본회의")) return "plenary";
  if (label.includes("통과") || label.includes("공포")) return "passed";
  return "committee";
}

/* Pick the dominant category id for a parent bill, so the similar page hero
   can be tinted with that category's hue. */
function dominantCatKey(bill) {
  if (!bill || !bill.cats || !bill.cats.length) return null;
  const accent = bill.cats.find(c => c.accent);
  return (accent || bill.cats[0]).k;
}

/* ---------------------------------------------------------------------------
   Similar-bill modal
--------------------------------------------------------------------------- */
function openSimilarModal(parentId, simIdx) {
  const parent = ALL_BY_ID[parentId];
  if (!parent) return;
  const sim = (parent.similar || [])[simIdx];
  if (!sim) return;
  const stageKey = stageKeyFromLabel(sim.stage);
  const stage = STAGES[stageKey];
  const stageOrder = ["proposed", "committee", "plenary", "passed"];
  const root = $("#modalRoot");
  root.innerHTML = `
    <div class="modal-overlay" id="ov">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <div class="tag-row" style="margin-bottom: 8px;">
              <span class="tag" style="background: var(--accent); color: #fff;">유사 법안</span>
              ${parent.cats.map(c => `<span class="tag ${c.accent ? 'accent' : ''}">${c.label}</span>`).join("")}
            </div>
            <h2>${sim.title}</h2>
            <div class="modal-meta">
              <span><b>발의일</b> ${sim.date}</span>
              <span><b>현재 단계</b> ${sim.stage}</span>
              <span><b>관련 법안</b> ${parent.title}</span>
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
              <div style="font-size: 12.5px; color: var(--ink-3);">발의일 ${sim.date}</div>
            </div>
            <div class="stage-track">
              ${stageOrder.map((s, i) => `<div class="stage-step ${i < stage.idx ? 'done' : ''} ${i === stage.idx ? 'active' : ''}"></div>`).join("")}
            </div>
            <div class="stage-labels">
              ${stageOrder.map((s, i) => `<span class="${i === stage.idx ? 'active' : ''}">${STAGES[s].label}</span>`).join("")}
            </div>
          </div>

          <div class="modal-section">
            <h4>이 법안 한 줄로</h4>
            <p style="color: var(--ink-2); font-size: 14.5px; margin: 0;">
              <strong>${parent.title}</strong>과 유사한 주제·정책 방향을 다루는 발의안으로 슥법이 분류했어요.
              현재 <strong>${sim.stage}</strong> 단계에 있으며,
              ${parent.cats.map(c => c.label).join(" · ")} 분야에 속합니다.
            </p>
          </div>

          <div class="modal-section">
            <h4>원본 법안</h4>
            <div class="sim-parent" data-parent="${parent.id}">
              <div class="sim-parent-top">
                <div class="tag-row">
                  ${parent.cats.map(c => `<span class="tag ${c.accent ? 'accent' : ''}">${c.label}</span>`).join("")}
                </div>
                <span class="sim-parent-stage"><span class="stage-dot ${STAGES[parent.stage].cls}"></span>${STAGES[parent.stage].label}</span>
              </div>
              <div class="sim-parent-title">${parent.title}</div>
              <div class="sim-parent-summary">${parent.summary[0]}</div>
              <div class="sim-parent-foot">
                <span>${parent.proposedAt} · ${parent.proposer}</span>
                <span class="sim-parent-cta">슥, 원본 보기
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
                </span>
              </div>
            </div>
          </div>

          <div class="modal-section sim-pending">
            <div class="sim-pending-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/></svg>
            </div>
            <div>
              <div class="sim-pending-title">슥법이 시민의 언어로 정리 중이에요</div>
              <div class="sim-pending-text">이 법안의 세 줄 요약·예상 영향·전체 조문은 곧 추가될 예정입니다. 그동안은 원본 법안 카드를 통해 맥락을 슥 둘러보세요.</div>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn btn-primary" id="openParent">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
              원본 법안 보기
            </button>
            <button class="btn btn-ghost" id="openSimilarPage">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 9h6M9 13h6M9 17h3"/></svg>
              유사 법안 전체 보기
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
  // parent-card click: swap to parent bill modal
  $(".sim-parent").addEventListener("click", () => { close(); openModal(parent.id); });
  $("#openParent").addEventListener("click", () => { close(); openModal(parent.id); });
  $("#openSimilarPage").addEventListener("click", () => { close(); location.hash = `#/picks/${parent.id}/similar`; });
  document.addEventListener("keydown", function esc(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", esc); } });
}

/* ---------------------------------------------------------------------------
   Similar-bills detail page  —  #/picks/:id/similar
--------------------------------------------------------------------------- */
function renderSimilarPage(parentId) {
  const wrap = $("#view-similar");
  const parent = ALL_BY_ID[parentId];
  if (!parent) {
    location.hash = "#/";
    return;
  }
  const similar = parent.similar || [];
  const catKey = dominantCatKey(parent);
  const meta = catKey ? CATEGORY_META[catKey] : null;
  const hue = meta ? meta.hue : 245;
  const parentStage = STAGES[parent.stage];

  wrap.innerHTML = `
    <nav class="similar-crumb" id="simCrumb">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      <span>홈으로</span>
    </nav>

    <section class="cat-hero similar-hero" style="--cat-h: ${hue}">
      <div class="cat-hero-glyph">${meta ? meta.glyph : "슥"}</div>
      <div class="cat-hero-text">
        <div class="similar-hero-eyebrow">이 법안과 유사한 법안</div>
        <h1>${parent.title}</h1>
        <div class="similar-hero-cats">
          ${parent.cats.map(c => `<span class="tag ${c.accent ? 'accent' : ''}" data-cat="${c.k}">${c.label}</span>`).join("")}
        </div>
        <div class="similar-hero-meta">
          <span><b>발의일</b> ${parent.proposedAt}</span>
          <span><b>대표 발의</b> ${parent.proposer}</span>
          <span class="similar-hero-stage"><span class="stage-dot ${parentStage.cls}"></span>${parentStage.label}</span>
        </div>
        <p class="desc">슥법이 함께 살펴볼 만한 법안 ${similar.length}건을 모았어요. 카드를 클릭하면 해당 법안의 상세를 슥 들여다볼 수 있어요.</p>
      </div>
      <div class="cat-hero-stats">
        <span class="cat-hero-stat-num">${similar.length}</span>
        <span class="cat-hero-stat-label">유사 법안</span>
        <button class="similar-hero-cta" id="openParentFromHero">
          원본 법안 보기
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
        </button>
      </div>
    </section>

    <div class="section-head" style="margin: 4px 0 16px;">
      <div>
        <h2 style="font-size: 22px;">유사한 법안 ${similar.length}건</h2>
        <div class="sub">슥법은 분야·정책 방향·키워드를 종합해 유사 법안을 묶어요.</div>
      </div>
    </div>

    ${similar.length ? `
      <div class="similar-grid">
        ${similar.map((s, i) => {
          const sStage = STAGES[stageKeyFromLabel(s.stage)];
          return `
            <article class="similar-card" data-idx="${i}" style="--delay: ${i * 60}ms">
              <div class="similar-card-top">
                <span class="similar-card-num">${String(i + 1).padStart(2, "0")}</span>
                <span class="similar-card-stage"><span class="stage-dot ${sStage.cls}"></span>${s.stage}</span>
              </div>
              <h3 class="similar-card-title">${s.title}</h3>
              <div class="similar-card-cats">
                ${parent.cats.map(c => `<span class="tag ${c.accent ? 'accent' : ''}">${c.label}</span>`).join("")}
              </div>
              <div class="similar-card-foot">
                <span>${s.date}</span>
                <span class="similar-card-cta">슥 들어가기
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
                </span>
              </div>
            </article>
          `;
        }).join("")}
      </div>
    ` : `
      <div class="similar-empty">
        아직 분류된 유사 법안이 없어요. 슥법이 새 법안을 추적해 곧 추가할 예정입니다.
      </div>
    `}
  `;

  $("#simCrumb").addEventListener("click", () => { location.hash = "#/"; });
  $("#openParentFromHero").addEventListener("click", () => openModal(parent.id));
  $$(".similar-card").forEach(el => {
    el.addEventListener("click", () => openSimilarModal(parent.id, +el.dataset.idx));
  });
}
