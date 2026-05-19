// Top "지금 슥" marquee ticker.
function renderTicker() {
  const seen = new Set();
  const items = [...PICKS, ...BILLS]
    .filter(b => {
      if (seen.has(b.id)) return false;
      seen.add(b.id);
      return true;
    })
    .slice(0, 10)
    .map(b => ({
      t: b.title,
      c: b.cats[0] ? b.cats[0].label : "법안",
      s: STAGES[b.stage] ? STAGES[b.stage].label : "발의",
    }));

  const row = items.map(x => `
    <span class="ticker-item">
      <span class="ti-tag">${x.c}</span>
      <b>${x.t}</b>
      <span class="ti-sep"></span>
      <span>${x.s}</span>
    </span>
  `).join("");
  $("#tickerTrack").innerHTML = row + row;
}
