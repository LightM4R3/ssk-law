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
  $$(".carousel-slide .pick-cta").forEach((el,i) => el.addEventListener("click", e => { e.stopPropagation(); openModal(PICKS[i].id); }));
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
  return `
    <article class="pick">
      <div class="pick-shine"></div>
      <div class="pick-num">${String(i+1).padStart(2,'0')} <span>/ ${String(PICKS.length).padStart(2,'0')}</span></div>
      <div>
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
        <div class="pick-stat">
          <div class="stat-num stat-pos">${p.sentiment}<span style="font-size:14px; font-weight: 700;">%</span></div>
          <div class="stat-lbl">시민 찬성 여론</div>
        </div>
        <div class="pick-stat">
          <div class="stat-num">${p.comments.toLocaleString()}</div>
          <div class="stat-lbl">시민 의견</div>
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

  // pointer drag
  let wheelAccum = 0;
  let wheelTimer = null;
  viewport.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".pick-cta") || e.target.closest("button")) return;
    carDragging = true;
    carWasDrag = false;
    carStartX = e.clientX;
    track.classList.add("dragging");
    viewport.setPointerCapture(e.pointerId);
  });
  viewport.addEventListener("pointermove", (e) => {
    if (!carDragging) return;
    const dx = e.clientX - carStartX;
    if (Math.abs(dx) > 6) carWasDrag = true;
    // dampened drag follow (resistance)
    const damped = dx * 0.7;
    track.style.transform = `translateX(${carOffset + damped}px)`;
  });
  const endDrag = (e) => {
    if (!carDragging) return;
    carDragging = false;
    const dx = (e.clientX || 0) - carStartX;
    const threshold = carWidth * 0.35;
    track.classList.remove("dragging");
    if (dx < -threshold) goTo(carIndex + 1);
    else if (dx > threshold) goTo(carIndex - 1);
    else goTo(carIndex);
    setTimeout(() => { carWasDrag = false; }, 50);
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

