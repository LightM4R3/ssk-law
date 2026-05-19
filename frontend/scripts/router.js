// Hash-based router for: home (#/), latest (#/latest), weekly (#/weekly), search (#/search?q=...)
// Depends on: state.js + the render* functions defined in the per-page scripts.
function routeFromHash() {
  const h = location.hash.replace(/^#\/?/, "");
  if (h.startsWith("search")) return "search";
  if (h === "latest" || h === "weekly") return h;
  return "home";
}
function getQuery() {
  const m = location.hash.match(/\?q=([^&]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}
function setRoute(name) {
  $$(".view").forEach(v => v.classList.remove("active"));
  $(`#view-${name}`).classList.add("active");
  $$("#nav a").forEach(a => a.classList.toggle("active", a.dataset.route === name));
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "home") setTimeout(() => renderCarousel(), 30);
  if (name === "latest") renderGrid();
  if (name === "weekly") renderWeekly();
  if (name === "search") renderSearch(getQuery());
}
window.addEventListener("hashchange", () => setRoute(routeFromHash()));
