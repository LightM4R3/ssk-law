<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import BillModal from "./components/BillModal.vue";
import PostCreateModal from "./components/PostCreateModal.vue";
import SimilarBillModal from "./components/SimilarBillModal.vue";
import { useAppStore } from "./stores/app";
import { useAuthStore } from "./stores/auth";

const store = useAppStore();
const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const isAuthLayout = computed(() => route.meta.layout === "auth");
const isLoggingOut = ref(false);
const postCreateBill = ref(null);
const createdPostForBill = ref(null);
const isHeaderMenuOpen = ref(false);
const activeTickerIndex = ref(0);
const hasScrollablePage = ref(false);
const scrollThumbHeight = ref(64);
const scrollThumbTop = ref(0);
let tickerTimer = null;
let pageResizeObserver = null;
const activeTickerItem = computed(() => {
  const items = store.tickerItems;
  if (!items.length) return null;
  return items[activeTickerIndex.value % items.length];
});
const mobileNavItems = computed(() => [
  ...store.navItems.map((item) => ({
    ...item,
    icon: item.name,
    to: { name: item.name },
  })),
  authStore.isAuthenticated
    ? {
      name: "my-page",
      label: "마이페이지",
      icon: "user",
      to: { name: "user-page", params: { idx: authStore.account.idx } },
    }
    : authStore.initialized
      ? {
        name: "login",
        label: "로그인",
        icon: "login",
        to: { name: "login" },
      }
      : null,
].filter(Boolean));
const mobileNavIconPaths = {
  latest: [
    "M12 8v4l2.5 1.5",
    "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  ],
  weekly: [
    "M4 19V5",
    "M4 15l5-5 4 4 7-8",
    "M16 6h4v4",
  ],
  categories: [
    "M4 4h6v6H4z",
    "M14 4h6v6h-6z",
    "M4 14h6v6H4z",
    "M14 14h6v6h-6z",
  ],
  posts: [
    "M5 5h14v10H8l-3 3V5Z",
    "M8 9h8",
    "M8 12h5",
  ],
  user: [
    "M20 21a8 8 0 0 0-16 0",
    "M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z",
  ],
  login: [
    "M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4",
    "M10 17l5-5-5-5",
    "M15 12H3",
  ],
};

function closeOpenOverlays() {
  if (store.activeBill) store.closeBill();
  if (store.activeSimilarData) store.closeSimilar();
  if (postCreateBill.value !== null) closePostCreateModal();
}

function toggleHeaderMenu() {
  isHeaderMenuOpen.value = !isHeaderMenuOpen.value;
}

function closeHeaderMenu() {
  isHeaderMenuOpen.value = false;
}

function selectTickerItem(item) {
  if (item.type === "bill" && item.billId) {
    store.openBill(item.billId);
    return;
  }

  closeOpenOverlays();

  if (item.type === "category" && item.categoryId) {
    router.push({ name: "category-detail", params: { id: item.categoryId } });
    return;
  }

  if (item.type === "route" && item.route) {
    router.push(item.route);
  }
}

async function logout() {
  if (isLoggingOut.value) return;

  closeHeaderMenu();
  isLoggingOut.value = true;
  try {
    await authStore.logout();
    await router.push({ name: "home" });
  } finally {
    isLoggingOut.value = false;
  }
}

function openPostCreateModal(bill = null) {
  postCreateBill.value = bill;
}

function closePostCreateModal() {
  postCreateBill.value = null;
}

function handlePostCreated(post) {
  createdPostForBill.value = post;
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateScrollIndicator() {
  const doc = document.documentElement;
  const scrollTop = window.scrollY || doc.scrollTop || 0;
  const scrollHeight = doc.scrollHeight || 0;
  const clientHeight = window.innerHeight || doc.clientHeight || 0;
  const maxScroll = Math.max(0, scrollHeight - clientHeight);
  const isMobile = window.matchMedia("(max-width: 980px)").matches;
  const trackTop = isMobile ? 18 : 24;
  const trackBottom = isMobile ? 104 : 24;
  const trackHeight = Math.max(96, clientHeight - trackTop - trackBottom);
  const thumbHeight = Math.max(42, Math.min(trackHeight, trackHeight * (clientHeight / Math.max(scrollHeight, 1))));
  const progress = maxScroll ? scrollTop / maxScroll : 0;

  hasScrollablePage.value = maxScroll > 8;
  scrollThumbHeight.value = thumbHeight;
  scrollThumbTop.value = (trackHeight - thumbHeight) * progress;
}

function startTickerRotation() {
  window.clearInterval(tickerTimer);
  tickerTimer = window.setInterval(() => {
    const items = store.tickerItems;
    if (!items.length) return;
    activeTickerIndex.value = (activeTickerIndex.value + 1) % items.length;
  }, 3600);
}

onMounted(() => {
  if (!authStore.initialized) authStore.loadCurrentAccount();
  startTickerRotation();
  updateScrollIndicator();
  window.addEventListener("scroll", updateScrollIndicator, { passive: true });
  window.addEventListener("resize", updateScrollIndicator);
  if ("ResizeObserver" in window) {
    pageResizeObserver = new ResizeObserver(updateScrollIndicator);
    pageResizeObserver.observe(document.body);
  }
});

onUnmounted(() => {
  window.clearInterval(tickerTimer);
  window.removeEventListener("scroll", updateScrollIndicator);
  window.removeEventListener("resize", updateScrollIndicator);
  pageResizeObserver?.disconnect();
});

watch(isAuthLayout, (authLayout) => {
  if (authLayout) return;
  if (store.apiStatus === "idle") store.loadInitialData();
}, { immediate: true });

watch(() => route.fullPath, () => {
  closeOpenOverlays();
  closeHeaderMenu();
  nextTick(updateScrollIndicator);
});

watch(() => store.tickerItems.length, (length) => {
  if (!length) {
    activeTickerIndex.value = 0;
    return;
  }
  if (activeTickerIndex.value >= length) activeTickerIndex.value = 0;
});
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner" :class="{ 'menu-open': isHeaderMenuOpen }">
      <RouterLink class="brand" :to="{ name: 'home' }">
        <div class="brand-mark">슥</div>
        <span>슥법</span>
        <small>· SSK-Law</small>
      </RouterLink>

      <nav class="nav" aria-label="주요 화면">
        <RouterLink
          v-for="item in store.navItems"
          :key="item.name"
          :to="{ name: item.name }"
          @click="closeHeaderMenu"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <button
        class="header-menu-toggle"
        type="button"
        :aria-expanded="isHeaderMenuOpen"
        @click="toggleHeaderMenu"
      >
        메뉴
      </button>

      <div class="account-actions">
        <template v-if="authStore.isAuthenticated">
          <span class="account-nickname" :title="authStore.account.nickname">
            {{ authStore.account.nickname }}님
          </span>
          <RouterLink
            class="account-link"
            :to="{ name: 'user-page', params: { idx: authStore.account.idx } }"
            @click="closeHeaderMenu"
          >
            마이 페이지
          </RouterLink>
          <button
            class="account-link"
            type="button"
            :disabled="isLoggingOut"
            @click="logout"
          >
            {{ isLoggingOut ? "로그아웃 중..." : "로그아웃" }}
          </button>
        </template>
        <RouterLink v-else-if="authStore.initialized" class="account-link" :to="{ name: 'login' }" @click="closeHeaderMenu">
          로그인
        </RouterLink>
        <span v-else class="account-session-status" role="status">세션 확인 중</span>
      </div>

      <div class="mobile-account-links">
        <template v-if="authStore.isAuthenticated">
          <RouterLink
            class="account-link"
            :to="{ name: 'user-page', params: { idx: authStore.account.idx } }"
            @click="closeHeaderMenu"
          >
            마이 페이지
          </RouterLink>
          <button
            class="account-link"
            type="button"
            :disabled="isLoggingOut"
            @click="logout"
          >
            {{ isLoggingOut ? "로그아웃 중..." : "로그아웃" }}
          </button>
        </template>
        <RouterLink
          v-else-if="authStore.initialized"
          class="account-link"
          :to="{ name: 'login' }"
          @click="closeHeaderMenu"
        >
          로그인
        </RouterLink>
      </div>

    </div>
  </header>

  <nav v-if="!isAuthLayout" class="mobile-bottom-nav" aria-label="모바일 하단 메뉴">
    <RouterLink
      v-for="item in mobileNavItems"
      :key="item.name"
      class="mobile-bottom-nav-item"
      :to="item.to"
    >
      <svg class="mobile-bottom-nav-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          v-for="path in mobileNavIconPaths[item.icon]"
          :key="path"
          :d="path"
        />
      </svg>
      <span>{{ item.label }}</span>
    </RouterLink>
    <RouterLink
      v-if="false && authStore.isAuthenticated"
      class="mobile-bottom-nav-item"
      :to="{ name: 'user-page', params: { idx: authStore.account.idx } }"
    >
      마이페이지
    </RouterLink>
    <RouterLink
      v-else-if="false && authStore.initialized"
      class="mobile-bottom-nav-item"
      :to="{ name: 'login' }"
    >
      로그인
    </RouterLink>
  </nav>

  <div v-if="!isAuthLayout" class="ticker">
    <div class="ticker-inner">
      <div class="ticker-label"><span class="ticker-pulse"></span>지금 슥</div>
      <div class="ticker-viewport">
        <Transition name="ticker-slide" mode="out-in">
          <button
            v-if="activeTickerItem"
            :key="activeTickerItem.id"
            class="ticker-item"
            type="button"
            @click="selectTickerItem(activeTickerItem)"
          >
            <span class="ti-tag">{{ activeTickerItem.label }}</span>
            <b>{{ activeTickerItem.title }}</b>
            <span class="ti-sep"></span>
            <span class="ti-meta">{{ activeTickerItem.meta }}</span>
          </button>
        </Transition>
      </div>
    </div>
  </div>

  <main :class="{ 'auth-main': isAuthLayout }">
    <RouterView />
  </main>

  <footer v-if="!isAuthLayout">
    슥법 · SSK-Law
  </footer>

  <div
    v-if="!isAuthLayout && hasScrollablePage"
    class="custom-scrollbar"
    aria-hidden="true"
  >
    <div
      class="custom-scrollbar-thumb"
      :style="{
        height: `${scrollThumbHeight}px`,
        transform: `translateY(${scrollThumbTop}px)`,
      }"
    ></div>
  </div>

  <button
    v-if="!isAuthLayout"
    class="scroll-top-btn"
    type="button"
    aria-label="맨 위로 이동"
    @click="scrollToTop"
  >
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="m18 15-6-6-6 6" />
    </svg>
  </button>

  <BillModal
    v-if="store.activeBill"
    :bill="store.activeBill"
    :created-post="createdPostForBill"
    @close="store.closeBill"
    @open-similar="store.openSimilar($event.parentId, $event.index)"
    @write-post="openPostCreateModal"
  />
  <PostCreateModal
    v-if="postCreateBill !== null"
    :initial-bill="postCreateBill"
    @close="closePostCreateModal"
    @created="handlePostCreated"
  />
  <SimilarBillModal
    v-if="store.activeSimilarData"
    :parent="store.activeSimilarData.parent"
    :similar="store.activeSimilarData.similar"
    :index="store.activeSimilarData.index"
    @close="store.closeSimilar"
    @open-parent="store.openBill(store.activeSimilarData.parent.id)"
  />
</template>
