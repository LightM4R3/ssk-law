import { createRouter, createWebHashHistory } from "vue-router";

import CategoriesView from "../views/CategoriesView.vue";
import CategoryDetailView from "../views/CategoryDetailView.vue";
import HomeView from "../views/HomeView.vue";
import LatestView from "../views/LatestView.vue";
import LoginView from "../views/LoginView.vue";
import SearchView from "../views/SearchView.vue";
import SignupView from "../views/SignupView.vue";
import SimilarView from "../views/SimilarView.vue";
import WeeklyView from "../views/WeeklyView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  { path: "/latest", name: "latest", component: LatestView },
  { path: "/weekly", name: "weekly", component: WeeklyView },
  { path: "/categories", name: "categories", component: CategoriesView },
  { path: "/categories/:id", name: "category-detail", component: CategoryDetailView, props: true },
  { path: "/search", name: "search", component: SearchView },
  { path: "/picks/:id/similar", name: "similar", component: SimilarView, props: true },
  { path: "/login", name: "login", component: LoginView, meta: { layout: "auth" } },
  { path: "/signup", name: "signup", component: SignupView, meta: { layout: "auth" } },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
