<script setup>
import { RouterLink, RouterView } from "vue-router";
import BillModal from "./components/BillModal.vue";
import SimilarBillModal from "./components/SimilarBillModal.vue";
import { useAppStore } from "./stores/app";

const store = useAppStore();
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
          <span v-for="item in store.tickerItems" :key="item" class="ticker-item">{{ item }}</span>
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
