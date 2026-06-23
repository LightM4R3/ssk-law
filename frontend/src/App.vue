<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import BillModal from "./components/BillModal.vue";
import SimilarBillModal from "./components/SimilarBillModal.vue";
import { useAppStore } from "./stores/app";
import { useAuthStore } from "./stores/auth";

const store = useAppStore();
const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const isAuthLayout = computed(() => route.meta.layout === "auth");
const isLoggingOut = ref(false);

function closeOpenOverlays() {
  if (store.activeBill) store.closeBill();
  if (store.activeSimilarData) store.closeSimilar();
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

  isLoggingOut.value = true;
  try {
    await authStore.logout();
    await router.push({ name: "home" });
  } finally {
    isLoggingOut.value = false;
  }
}

onMounted(() => {
  if (!authStore.initialized) authStore.loadCurrentAccount();
});

watch(isAuthLayout, (authLayout) => {
  if (authLayout) return;
  if (store.apiStatus === "idle") store.loadInitialData();
}, { immediate: true });
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
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
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="account-actions">
        <template v-if="authStore.isAuthenticated">
          <span class="account-nickname" :title="authStore.account.nickname">
            {{ authStore.account.nickname }}님
          </span>
          <button
            class="account-link"
            type="button"
            :disabled="isLoggingOut"
            @click="logout"
          >
            {{ isLoggingOut ? "로그아웃 중..." : "로그아웃" }}
          </button>
        </template>
        <RouterLink v-else-if="authStore.initialized" class="account-link" :to="{ name: 'login' }">
          로그인
        </RouterLink>
        <span v-else class="account-session-status" role="status">세션 확인 중</span>
      </div>

    </div>
  </header>

  <div v-if="!isAuthLayout" class="ticker">
    <div class="ticker-inner">
      <div class="ticker-label"><span class="ticker-pulse"></span>지금 슥</div>
      <div class="ticker-viewport">
        <div class="ticker-track">
          <button
            v-for="item in store.tickerItems"
            :key="item.id"
            class="ticker-item"
            type="button"
            @click="selectTickerItem(item)"
          >
            <span class="ti-tag">{{ item.label }}</span>
            <b>{{ item.title }}</b>
            <span class="ti-sep"></span>
            <span class="ti-meta">{{ item.meta }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <main :class="{ 'auth-main': isAuthLayout }">
    <RouterView />
  </main>

  <footer v-if="!isAuthLayout">
    슥법 · SSK-Law
  </footer>

  <BillModal
    v-if="store.activeBill"
    :bill="store.activeBill"
    @close="store.closeBill"
    @open-similar="store.openSimilar($event.parentId, $event.index)"
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
