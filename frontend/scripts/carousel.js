// Home page carousel of "오늘 슥 보기 좋은 법안" picks.
// Pointer-drag, mouse-wheel and arrow-key navigation, dampened with locks to prevent runaway swipes.
// Depends on: state.js, modal.js (openModal), card3d.js (bindPick3D), data.js (PICKS, STAGES)
let carIndex = 0;
let carOffset = 0;
let carDragging = false;
let carStartX = 0;
let carWidth = 0;

function renderCarousel() {
  const track = $("#carouselTrack");
  track.innerHTML = PICKS.map((p, i) => `
    <div class="carousel-slide" data-i="${i}">
      ${pickHTML(p, i)}
    </div>
  `).join("");
  $("#dots").innerHTML = PICKS.map((_,i) => `<button class="dot ${i===carIndex?'active':''}" data-i="${i}" aria-label="${i+1}번"></button>`).join("");
  $$("#dots .dot").forEach(d => d.addEventListener("click", () => goTo(+d.dataset.i)));
  $$(".carousel-slide .pick-cta").forEach((el,i) => el.addEventListener("click", e => {
    e.stopPropagation();
    if (carWasDrag) return;
    openModal(PICKS[i].id);
  }));

  // Similar-bills panel: each item opens a dedicated similar-bill modal
  // (parent context + honest "in-progress" notice + actions). "더 보기" jumps
  // to the dedicated similar page.
  $$(".carousel-slide .pick-sim").forEach(el => {
    el.addEventListener("click", e => {
      e.stopPropagation();
      if (carWasDrag) return;
      openSimilarModal(el.dataset.pick, +el.dataset.idx);
    });
  });
  $$(".carousel-slide .pick-sim-more").forEach(el => {
    el.addEventListener("click", e => {
      e.stopPropagation();
      if (carWasDrag) return;
      location.hash = `#/picks/${el.dataset.pick}/similar`;
    });
  });

  $$(".carousel-slide").forEach((el,i) => el.addEventListener("click", e => { if (!carWasDrag) openModal(PICKS[i].id); }));
  $$(".carousel-slide .pick").forEach(el => bindPick3D(el));
  measureCarousel();
  applyTransform(false);
  updateArrows();
  // mark first pick as in-view for top line draw
  requestAnimationFrame(() => {
    const slides = $$(".carousel-slide .pick");
    if (slides[carIndex]) slides[carIndex].classList.add("in-view");
  });
}

function pickHTML(p, i) {
  const stage = STAGES[p.stage];
  const stageOrder = ["proposed","committee","plenary","passed"];
  const similar = (p.similar || []).slice(0, 2);
  return `
    <article class="pick">
      <div class="pick-shine"></div>
      <div class="pick-num">${String(i+1).padStart(2,'0')} <span>/ ${String(PICKS.length).padStart(2,'0')}</span></div>
      <div class="pick-body">
        <div class="pick-main">
          <span class="pick-eyebrow">오늘 슥 보기 좋은 법안 · 5월 14일</span>
          <div class="pick-cats">
            ${p.cats.map(c => `<span class="tag ${c.accent?'accent':''}">${c.label}</span>`).join("")}
          </div>
          <h2>${p.title}</h2>
          <ul class="summary">
            ${p.summary.map(s => `<li>${s}</li>`).join("")}
          </ul>
          <div class="pick-meta">
            <span><b>발의일</b> ${p.proposedAt}</span>
            <span><b>대표 발의</b> ${p.proposer}</span>
          </div>
          <button class="pick-cta">
            슥, 자세히 보기
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
          </button>
        </div>
        ${similar.length ? `
          <aside class="pick-side">
            <div class="pick-side-head">
              <span class="pick-side-eyebrow">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>
                유사한 법안 슥 보기
              </span>
              <span class="pick-side-count">${(p.similar || []).length}건</span>
            </div>
            <div class="pick-side-list">
              ${similar.map((s, si) => `
                <button class="pick-sim" data-pick="${p.id}" data-idx="${si}">
                  <div class="pick-sim-top">
                    <span class="pick-sim-num">${String(si + 1).padStart(2, '0')}</span>
                    <span class="pick-sim-stage">${s.stage}</span>
                  </div>
                  <div class="pick-sim-title">${s.title}</div>
                  <div class="pick-sim-meta">
                    <span>${s.date}</span>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
                  </div>
                </button>
              `).join("")}
            </div>
            <button class="pick-sim-more" data-pick="${p.id}">
              유사 법안 더 보기
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>
            </button>
          </aside>
        ` : ''}
      </div>
      <div class="pick-foot">
        <div class="stage-block">
          <h4>입법 단계</h4>
          <div class="stage-track">
            ${stageOrder.map((s,si) => `<div class="stage-step ${si<stage.idx?'done':''} ${si===stage.idx?'active':''}"></div>`).join("")}
          </div>
          <div class="stage-labels">
            ${stageOrder.map((s,si) => `<span class="${si===stage.idx?'active':''}">${STAGES[s].label}</span>`).join("")}
          </div>
        </div>
      </div>
    </article>
  `;
}

function measureCarousel() {
  carWidth = $("#carouselViewport").getBoundingClientRect().width;
}

function goTo(i, animate=true) {
  carIndex = Math.max(0, Math.min(PICKS.length - 1, i));
  carOffset = -carIndex * carWidth;
  applyTransform(animate);
  $$("#dots .dot").forEach((d,di) => d.classList.toggle("active", di===carIndex));
  $$(".carousel-slide .pick").forEach((el,ei) => el.classList.toggle("in-view", ei===carIndex));
  updateArrows();
}

function applyTransform(animate=true) {
  const t = $("#carouselTrack");
  t.classList.toggle("dragging", !animate);
  t.style.transform = `translateX(${carOffset}px)`;
}

function updateArrows() {
  $("#prev").disabled = carIndex === 0;
  $("#next").disabled = carIndex === PICKS.length - 1;
}

let carWasDrag = false;
function bindCarousel() {
  const viewport = $("#carouselViewport");
  const track = $("#carouselTrack");

  $("#prev").addEventListener("click", () => goTo(carIndex - 1));
  $("#next").addEventListener("click", () => goTo(carIndex + 1));

  /* Drag with intent detection.
     Previously we early-returned on `closest("button")` in pointerdown, which
     meant the user couldn't drag the slide from the new similar-bills side
     panel area at all. Instead: on pointerdown we just record the start
     position. Only after the pointer has actually moved >8px do we commit to
     drag mode and capture the pointer — at that point button clicks are
     naturally suppressed (the click event won't fire if the pointer-capture
     target differs from the press target). This restores natural feel: short
     presses on buttons click; longer drags from anywhere on the card slide. */
  let pendingDrag = false;
  let activePointerId = null;
  let wheelAccum = 0;
  let wheelTimer = null;

  viewport.addEventListener("pointerdown", (e) => {
    // The primary CTA is a strong click intent — never start drag from there.
    if (e.target.closest(".pick-cta")) return;
    pendingDrag = true;
    carDragging = false;
    carWasDrag = false;
    carStartX = e.clientX;
    activePointerId = e.pointerId;
  });
  viewport.addEventListener("pointermove", (e) => {
    if (!pendingDrag && !carDragging) return;
    const dx = e.clientX - carStartX;
    // Commit to drag once meaningful motion happens — and only then capture.
    if (pendingDrag && !carDragging && Math.abs(dx) > 8) {
      carDragging = true;
      carWasDrag = true;
      track.classList.add("dragging");
      try { viewport.setPointerCapture(activePointerId); } catch (_) {}
    }
    if (carDragging) {
      const damped = dx * 0.7;
      track.style.transform = `translateX(${carOffset + damped}px)`;
    }
  });
  const endDrag = (e) => {
    if (!pendingDrag && !carDragging) return;
    pendingDrag = false;
    if (!carDragging) { activePointerId = null; return; }
    carDragging = false;
    const dx = (e.clientX || 0) - carStartX;
    const threshold = carWidth * 0.35;
    track.classList.remove("dragging");
    if (dx < -threshold) goTo(carIndex + 1);
    else if (dx > threshold) goTo(carIndex - 1);
    else goTo(carIndex);
    activePointerId = null;
    setTimeout(() => { carWasDrag = false; }, 80);
  };
  viewport.addEventListener("pointerup", endDrag);
  viewport.addEventListener("pointercancel", endDrag);
  viewport.addEventListener("pointerleave", endDrag);

  // wheel horizontal swipe (accumulate to avoid sensitivity)
  let wheelLock = false;
  viewport.addEventListener("wheel", (e) => {
    if (Math.abs(e.deltaX) < 14 || wheelLock) return;
    wheelAccum += e.deltaX;
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => { wheelAccum = 0; }, 220);
    if (Math.abs(wheelAccum) < 80) return;
    wheelLock = true;
    if (wheelAccum > 0) goTo(carIndex + 1);
    else goTo(carIndex - 1);
    wheelAccum = 0;
    setTimeout(() => wheelLock = false, 900);
  }, { passive: true });

  // keyboard
  let keyLock = false;
  document.addEventListener("keydown", (e) => {
    if (routeFromHash() !== "home") return;
    if (e.target.tagName === "INPUT") return;
    if (keyLock) return;
    if (e.key === "ArrowRight") { e.preventDefault(); keyLock = true; goTo(carIndex + 1); setTimeout(() => keyLock = false, 700); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); keyLock = true; goTo(carIndex - 1); setTimeout(() => keyLock = false, 700); }
  });

  // resize
  window.addEventListener("resize", () => { measureCarousel(); applyTransform(false); });
}

