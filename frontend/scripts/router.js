// Hash-based router for: home (#/), latest (#/latest), weekly (#/weekly),
// categories hub (#/categories), category detail (#/categories/:id),
// search (#/search?q=...).
// Depends on: state.js + the render* functions defined in the per-page scripts.
function routeFromHash() {
  const h = location.hash.replace(/^#\/?/, "");
  if (h.startsWith("search")) return "search";
  if (/^picks\/[^/]+\/similar/.test(h)) return "similar";
  if (h.startsWith("categories/")) return "category";
  if (h === "categories") return "categories";
  if (h === "latest" || h === "weekly") return h;
  return "home";
}
function getQuery() {
  const m = location.hash.match(/\?q=([^&]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}
function getCategoryParam() {
  const m = location.hash.match(/^#\/?categories\/([^?]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}
function getPickParamForSimilar() {
  const m = location.hash.match(/^#\/?picks\/([^/]+)\/similar/);
  return m ? decodeURIComponent(m[1]) : "";
}
function setRoute(name) {
  $$(".view").forEach(v => v.classList.remove("active"));
  $(`#view-${name}`).classList.add("active");
  // Highlight the nav link. Both "categories" and "category" views map to the
  // "분야별" top-nav entry.
  const navKey = (name === "category") ? "categories" : name;
  $$("#nav a").forEach(a => a.classList.toggle("active", a.dataset.route === navKey));
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (name === "home") setTimeout(() => renderCarousel(), 30);
  if (name === "latest") renderGrid();
  if (name === "weekly") renderWeekly();
  if (name === "categories") renderCategoriesHub();
  if (name === "category") renderCategoryDetail(getCategoryParam());
  if (name === "similar") renderSimilarPage(getPickParamForSimilar());
  if (name === "search") renderSearch(getQuery());
}
window.addEventListener("hashchange", () => setRoute(routeFromHash()));
