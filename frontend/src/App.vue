<script setup>
import { onMounted } from "vue";
import { RouterLink, RouterView, useRouter } from "vue-router";
import BillModal from "./components/BillModal.vue";
import SimilarBillModal from "./components/SimilarBillModal.vue";
import { useAppStore } from "./stores/app";

const store = useAppStore();
const router = useRouter();

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

onMounted(() => {
  store.loadInitialData();
});
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

    </div>
  </header>

  <div class="ticker">
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

  <main>
    <RouterView />
  </main>

  <footer>
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
