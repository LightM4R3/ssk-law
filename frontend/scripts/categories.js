// Categories hub (#/categories) + per-category detail (#/categories/:id) + tag popover.
// Depends on: data.js (CATEGORIES, CATEGORY_META, BILLS, PICKS, STAGES, WEEKLY),
//             state.js, modal.js, card3d.js, latest.js (reuses cardHTML).

/* ---------------------------------------------------------------------------
   Lookup helpers
--------------------------------------------------------------------------- */
function getCategory(id) {
  return CATEGORIES.find(c => c.id === id);
}
function getCategoryMeta(id, cat = getCategory(id)) {
  return CATEGORY_META[id] || {
    glyph: cat ? cat.label.charAt(0) : "슥",
    sub: cat ? cat.id : "Category",
    hue: 245,
    blurb: cat ? `${cat.label} 분야 법안` : "분야별 법안",
    new: 0,
    hot: false,
  };
}
function billsInCategory(catId) {
  return BILLS.filter(b => b.cats && b.cats.some(c => c.k === catId));
}
function picksInCategory(catId) {
  return PICKS.filter(p => p.cats && p.cats.some(c => c.k === catId));
}
function weeklyInCategory(catId) {
  return WEEKLY.filter(w => w.cats && w.cats.some(c => c.k === catId));
}
function topTitlesForCategory(catId, n = 3) {
  // prefer hot weekly items, then bills, then picks; dedupe by title
  const seen = new Set();
  const out = [];
  const push = (t) => { if (t && !seen.has(t)) { seen.add(t); out.push(t); } };
  weeklyInCategory(catId).forEach(w => push(w.title));
  billsInCategory(catId).forEach(b => push(b.title));
  picksInCategory(catId).forEach(p => push(p.title));
  return out.slice(0, n);
}
function stageCountsForCategory(catId) {
  const counts = { proposed: 0, committee: 0, plenary: 0, passed: 0 };
  const bills = billsInCategory(catId);
  bills.forEach(b => { if (counts[b.stage] !== undefined) counts[b.stage]++; });
  // Add a synthetic baseline so the detail page reads like a real dataset,
  // not just whatever's in this demo's BILLS array.
  const cat = getCategory(catId);
  const remaining = Math.max(0, (cat?.count || 0) - bills.length);
  if (remaining) {
    // distribute remaining across stages with a stable, plausible split
    const split = [0.45, 0.32, 0.16, 0.07];
    counts.proposed  += Math.round(remaining * split[0]);
    counts.committee += Math.round(remaining * split[1]);
    counts.plenary   += Math.round(remaining * split[2]);
    counts.passed    += Math.max(0, remaining - (
      Math.round(remaining * split[0]) +
      Math.round(remaining * split[1]) +
      Math.round(remaining * split[2])
    ));
  }
  return counts;
}

/* ---------------------------------------------------------------------------
   Hub  —  #/categories
--------------------------------------------------------------------------- */
function renderCategoriesHub() {
  const wrap = $("#view-categories");
  // re-render every time so card animations replay
  const fields = CATEGORIES.filter(c => c.id !== "all");
  const cardsHTML = fields.map((c, i) => {
    const meta = getCategoryMeta(c.id, c);
    const titles = topTitlesForCategory(c.id, 3);
    return `
      <article class="cat-card" data-cat="${c.id}"
               style="--cat-h: ${meta.hue ?? 245}; --delay: ${i * 60}ms">
        <div class="cat-card-top">
          <div class="cat-glyph">${meta.glyph || c.label.charAt(0)}</div>
          ${meta.hot ? `
            <span class="cat-badge"><span class="pulse"></span>이번 주 화제</span>
          ` : `
            <span class="cat-badge" style="background: var(--surface-2); color: var(--ink-3);">신규 ${meta.new ?? 0}건</span>
          `}
        </div>
        <h3 class="cat-name">
          ${c.label}
          <span class="sub">${meta.sub || ""}</span>
        </h3>
        <p class="cat-blurb">${meta.blurb || ""}</p>
        <div class="cat-stats">
          <div class="cat-stat">
            <span class="cat-stat-num">${c.count}<span class="delta">+${meta.new ?? 0}</span></span>
            <span class="cat-stat-label">전체 / 이번주 신규</span>
          </div>
          <div class="cat-stat">
            <span class="cat-stat-num">${stageCountsForCategory(c.id).committee}</span>
            <span class="cat-stat-label">위원회 심사 중</span>
          </div>
        </div>
        <div class="cat-preview">
          ${titles.map(t => `<div class="cat-preview-item"><span>${t}</span></div>`).join("")}
        </div>
        <div class="cat-cta">슥 들어가기
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
        </div>
      </article>
    `;
  }).join("");

  wrap.innerHTML = `
    <div class="section-head">
      <div>
        <h2>분야별로 슥 둘러보기</h2>
        <div class="sub">9개 분야 · 시민 생활과 가까운 주제부터, 카드를 클릭해 들어가 보세요.</div>
      </div>
      <div class="cat-badge" style="--cat-h: 245; --cat-tint: var(--accent-soft); --cat-ink: var(--accent-ink); background: var(--accent-soft); color: var(--accent-ink);">
        <span class="pulse" style="background: var(--accent-ink);"></span>
        총 ${CATEGORIES.find(c => c.id === "all")?.count || BILLS.length}건 추적 중
      </div>
    </div>
    <div class="cat-grid" id="catGrid">${cardsHTML}</div>
  `;

  $$(".cat-card", wrap).forEach(el => {
    el.addEventListener("click", () => {
      location.hash = `#/categories/${el.dataset.cat}`;
    });
  });
}

/* ---------------------------------------------------------------------------
   Detail  —  #/categories/:id
--------------------------------------------------------------------------- */
function renderCategoryDetail(catId) {
  const wrap = $("#view-category");
  const cat = getCategory(catId);
  const meta = getCategoryMeta(catId, cat);
  if (!cat) {
    // unknown category → bounce to hub
    location.hash = "#/categories";
    return;
  }
  const bills = billsInCategory(catId);
  const sc = stageCountsForCategory(catId);
  const totalTracked = sc.proposed + sc.committee + sc.plenary + sc.passed;

  // jump-chip rail
  const jumpHTML = CATEGORIES.filter(c => c.id !== "all").map(c => {
    const m = getCategoryMeta(c.id, c);
    return `
      <button class="cat-jump-chip ${c.id === catId ? 'active' : ''}"
              data-cat="${c.id}" style="--cat-h: ${m.hue ?? 245}">
        <span class="swatch"></span>${c.label}
        <span style="opacity:.55; font-weight:500; margin-left:2px;">${c.count}</span>
      </button>
    `;
  }).join("");

  wrap.innerHTML = `
    <section class="cat-hero" style="--cat-h: ${meta.hue}">
      <div class="cat-hero-glyph">${meta.glyph}</div>
      <div class="cat-hero-text">
        <div class="crumb" id="crumbBack">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          분야별
        </div>
        <h1>${cat.label}<span class="sub-en">${meta.sub}</span></h1>
        <p class="desc">${meta.blurb}. 이 분야의 최신 법안과 진행 단계, 인기 법안을 한 화면에 모았어요.</p>
      </div>
      <div class="cat-hero-stats">
        <span class="cat-hero-stat-num">${cat.count}</span>
        <span class="cat-hero-stat-label">전체 추적 법안</span>
        <span class="cat-hero-stat-num" style="font-size: 18px; margin-top: 10px;">+${meta.new}</span>
        <span class="cat-hero-stat-label">이번 주 신규 발의</span>
      </div>
    </section>

    <div class="cat-jump" id="catJump">${jumpHTML}</div>

    <div class="cat-stage-row">
      <div class="cat-stage-cell s1">
        <span class="cat-stage-cell-label">발의</span>
        <span class="cat-stage-cell-num">${sc.proposed}</span>
      </div>
      <div class="cat-stage-cell s2">
        <span class="cat-stage-cell-label">위원회 심사</span>
        <span class="cat-stage-cell-num">${sc.committee}</span>
      </div>
      <div class="cat-stage-cell s3">
        <span class="cat-stage-cell-label">본회의 상정</span>
        <span class="cat-stage-cell-num">${sc.plenary}</span>
      </div>
      <div class="cat-stage-cell s4">
        <span class="cat-stage-cell-label">통과 · 공포</span>
        <span class="cat-stage-cell-num">${sc.passed}</span>
      </div>
    </div>

    <div class="section-head" style="margin: 4px 0 16px;">
      <div>
        <h2 style="font-size: 22px;">이 분야의 법안 ${bills.length}건</h2>
        <div class="sub">샘플 데이터입니다. 카드를 클릭해 상세 내용을 확인하세요.</div>
      </div>
    </div>

    <section class="grid" id="catBillsGrid">
      ${bills.length
        ? bills.map((b, i) => cardHTML(b, i)).join("")
        : `<div style="grid-column: span 6; padding: 64px 0; text-align:center; color: var(--ink-3); font-size: 14.5px;">
             해당 분야에 표시할 샘플 법안이 아직 없어요. 곧 추가될 예정이에요.
           </div>`
      }
    </section>
  `;

  // crumb + jump rail
  $("#crumbBack").addEventListener("click", () => { location.hash = "#/categories"; });
  $$("#catJump .cat-jump-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      location.hash = `#/categories/${btn.dataset.cat}`;
    });
  });

  // bind grid cards (reuse latest-page behavior)
  $$("#catBillsGrid .card").forEach(el => {
    bindCard3D(el);
    el.addEventListener("click", (e) => {
      if (e.target.closest(".bookmark")) return;
      if (e.target.closest(".tag")) return; // tag click opens popover, handled below
      openModal(el.dataset.id);
    });
  });
  $$("#catBillsGrid .bookmark").forEach(b => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = b.dataset.id;
      if (savedSet.has(id)) savedSet.delete(id); else savedSet.add(id);
      renderCategoryDetail(catId);
    });
  });
}

/* ---------------------------------------------------------------------------
   Tag popover  —  click any .tag in cards/modal to peek into that category
--------------------------------------------------------------------------- */
function openTagPopover(catKey, anchor) {
  const cat = getCategory(catKey);
  const meta = getCategoryMeta(catKey, cat);
  if (!cat) return;

  // close any existing popover first
  closeTagPopover();

  const titles = topTitlesForCategory(catKey, 4);
  const sc = stageCountsForCategory(catKey);

  const overlay = document.createElement("div");
  overlay.className = "tag-pop-overlay";
  overlay.innerHTML = `
    <div class="scrim"></div>
    <div class="tag-pop" style="--cat-h: ${meta.hue}">
      <div class="tag-pop-head">
        <div class="tag-pop-glyph">${meta.glyph}</div>
        <div>
          <div class="tag-pop-title">${cat.label}</div>
          <div class="tag-pop-sub">${meta.sub} · ${meta.blurb}</div>
        </div>
        <button class="tag-pop-close" aria-label="닫기">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="tag-pop-stats">
        <div>
          <div class="tag-pop-stat-num">${cat.count}</div>
          <div class="tag-pop-stat-label">전체</div>
        </div>
        <div>
          <div class="tag-pop-stat-num">+${meta.new}</div>
          <div class="tag-pop-stat-label">이번 주 신규</div>
        </div>
        <div>
          <div class="tag-pop-stat-num">${sc.committee}</div>
          <div class="tag-pop-stat-label">심사 중</div>
        </div>
      </div>
      <div class="tag-pop-list">
        ${titles.map((t, i) => `
          <div class="tag-pop-item" data-title="${t}">
            <span class="num">${String(i + 1).padStart(2, "0")}</span>
            <span class="t">${t}</span>
          </div>
        `).join("") || `<div style="padding: 8px 10px; color: var(--ink-3); font-size: 13px;">표시할 법안이 아직 없어요.</div>`}
      </div>
      <button class="tag-pop-cta" data-cta>
        분야 페이지로 이동
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
      </button>
    </div>
  `;
  document.body.appendChild(overlay);

  // Position the .tag-pop near the anchor, clamped to viewport.
  const pop = overlay.querySelector(".tag-pop");
  // make it temporarily visible to measure
  pop.style.visibility = "hidden";
  pop.style.opacity = "0";
  requestAnimationFrame(() => {
    const r = anchor.getBoundingClientRect();
    const popW = pop.offsetWidth;
    const popH = pop.offsetHeight;
    const margin = 12;
    let left = r.left + r.width / 2 - popW / 2;
    let top = r.bottom + 10;
    if (left < margin) left = margin;
    if (left + popW > window.innerWidth - margin) left = window.innerWidth - popW - margin;
    if (top + popH > window.innerHeight - margin) {
      // flip above the anchor
      top = r.top - popH - 10;
    }
    if (top < margin) top = margin;
    pop.style.left = left + "px";
    pop.style.top = top + "px";
    pop.style.visibility = "";
    pop.style.opacity = "";
    requestAnimationFrame(() => overlay.classList.add("open"));
  });

  // close interactions
  overlay.querySelector(".scrim").addEventListener("click", closeTagPopover);
  overlay.querySelector(".tag-pop-close").addEventListener("click", closeTagPopover);
  overlay.querySelector("[data-cta]").addEventListener("click", () => {
    closeTagPopover();
    location.hash = `#/categories/${catKey}`;
  });
  // list-item: open the bill modal if we can find it by title
  overlay.querySelectorAll(".tag-pop-item").forEach(item => {
    item.addEventListener("click", () => {
      const title = item.dataset.title;
      const bill = [...PICKS, ...BILLS].find(b => b.title === title);
      closeTagPopover();
      if (bill) openModal(bill.id);
      else location.hash = `#/categories/${catKey}`;
    });
  });
  // Esc to close
  document.addEventListener("keydown", tagPopoverEscHandler);
}
function tagPopoverEscHandler(e) { if (e.key === "Escape") closeTagPopover(); }
function closeTagPopover() {
  const ov = document.querySelector(".tag-pop-overlay");
  if (!ov) return;
  ov.classList.remove("open");
  document.removeEventListener("keydown", tagPopoverEscHandler);
  setTimeout(() => ov.remove(), 220);
}

/* Delegated tag click: any element matching `.tag[data-cat]` opens the popover.
   Use CAPTURE phase so we intercept before card-level click handlers (which
   open the bill modal on .card click). */
document.addEventListener("click", (e) => {
  const tag = e.target.closest(".tag[data-cat]");
  if (!tag) return;
  e.preventDefault();
  e.stopPropagation();
  openTagPopover(tag.dataset.cat, tag);
}, true);

/* Decorate existing cards so their .tag elements carry data-cat and pointer cursor.
   The cards are produced by cardHTML in latest.js — we monkey-patch by walking the
   DOM after each render via a MutationObserver. Lightweight and idempotent. */
function decorateTagsIn(root) {
  $$(".tag", root).forEach(t => {
    if (t.dataset.cat) return;
    // The label is the text content (we don't have the k attribute on the rendered
    // tag) — match it back to a category id by Korean label.
    const label = t.textContent.trim();
    // exact match first
    let match = CATEGORIES.find(c => c.label === label);
    if (!match) {
      // some bills use "생활" or "교통" — map to nearest category
      const aliasMap = { "생활": "welfare", "교통": "safety", "환경": "env" };
      const aliasId = aliasMap[label];
      if (aliasId) match = CATEGORIES.find(c => c.id === aliasId);
    }
    if (match && match.id !== "all") {
      t.dataset.cat = match.id;
      t.classList.add("tag-interactive");
    }
  });
}
const _decorateObserver = new MutationObserver((muts) => {
  muts.forEach(m => {
    m.addedNodes.forEach(n => {
      if (n.nodeType === 1) decorateTagsIn(n);
    });
  });
});
_decorateObserver.observe(document.body, { childList: true, subtree: true });
// initial pass for anything already in the DOM
document.addEventListener("DOMContentLoaded", () => decorateTagsIn(document));
