// App bootstrap: load API data, wire ticker, carousel, initial route, search submit, and ⌘K shortcut.
async function initApp() {
  const dataState = await loadAppData();
  rebuildAllById();
  document.documentElement.dataset.dataSource = dataState.source;

  renderTicker();
  bindCarousel();
  wireSearch();
  setRoute(routeFromHash());
}

/* search submit on Enter (both inputs) */
function wireSearchInput(el) {
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = e.target.value.trim();
      if (!q) return;
      location.hash = `#/search?q=${encodeURIComponent(q)}`;
    }
  });
}

function wireSearch() {
  wireSearchInput($("#searchInput"));
  wireSearchInput($("#searchInput2"));
  $("#backHome").addEventListener("click", () => { location.hash = "#/"; });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      const r = routeFromHash();
      if (r === "home") $("#searchInput").focus();
      else if (r === "search") $("#searchInput2").focus();
      else { location.hash = "#/"; setTimeout(() => $("#searchInput").focus(), 100); }
    }
  });
}

initApp();
