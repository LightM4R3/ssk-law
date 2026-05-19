// Shared DOM helpers and runtime state.
// Depends on: data.js (PICKS, BILLS)
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// Mutable globals used across page scripts.
// Kept as plain globals (not a module) because the project ships as static files
// loaded via <script> tags in order — see index.html.
let activeCat = "all";
let savedSet = new Set(["b2"]);

const ALL_BY_ID = {};

function rebuildAllById() {
  Object.keys(ALL_BY_ID).forEach(id => delete ALL_BY_ID[id]);
  PICKS.forEach(p => ALL_BY_ID[p.id] = p);
  BILLS.forEach(b => ALL_BY_ID[b.id] = b);
}

rebuildAllById();
