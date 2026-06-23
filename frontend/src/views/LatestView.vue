<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import ApiStateCard from "../components/ApiStateCard.vue";
import BillCard from "../components/BillCard.vue";
import { getApiErrorState, lawApi, normalizeBill } from "../services/api";
import { useAppStore } from "../stores/app";

const store = useAppStore();
const bills = ref([]);
const status = ref("idle");
const errorState = ref(null);
const sentinel = ref(null);
const pagination = ref({
  page: 0,
  page_size: 10,
  total_count: 0,
  total_pages: 1,
});
let observer = null;

const billLayout = [
  { span: "span-6", featured: true },
  { span: "span-3" },
  { span: "span-3" },
  { span: "span-2", compact: true },
  { span: "span-2", compact: true },
  { span: "span-2", compact: true },
  { span: "span-3" },
  { span: "span-3" },
  { span: "span-2", compact: true },
  { span: "span-2", compact: true },
];

const displayedBills = computed(() => bills.value.map((bill, index) => ({
  ...(billLayout[index % billLayout.length] || {}),
  ...bill,
  stageLabel: store.stageLabel(bill.stage),
  stageClass: store.stageClass(bill.stage),
})));
const isInitialLoading = computed(() => status.value === "loading" && !bills.value.length);
const isLoadingMore = computed(() => status.value === "loading" && bills.value.length > 0);
const hasMore = computed(() => pagination.value.page < pagination.value.total_pages);

async function loadBills(page = 1) {
  if (status.value === "loading") return;
  if (page > 1 && !hasMore.value) return;

  status.value = "loading";
  errorState.value = null;
  try {
    const payload = await lawApi.getBills({
      sort: "-proposed_at",
      page,
      page_size: 10,
    });
    const incoming = (payload?.bills || []).map(normalizeBill);
    bills.value = page === 1 ? incoming : [...bills.value, ...incoming];
    pagination.value = {
      page: Number(payload?.pagination?.page || page),
      page_size: Number(payload?.pagination?.page_size || 10),
      total_count: Number(payload?.pagination?.total_count || incoming.length),
      total_pages: Number(payload?.pagination?.total_pages || 1),
    };
    status.value = "ready";
    await nextTick();
    observeSentinel();
  } catch (error) {
    status.value = "error";
    errorState.value = getApiErrorState(error, "최신 법안을 불러오지 못했어요");
  }
}

function loadNextPage() {
  if (!hasMore.value || status.value === "loading") return;
  loadBills(pagination.value.page + 1);
}

function observeSentinel() {
  if (!sentinel.value || !("IntersectionObserver" in window)) return;

  if (!observer) {
    observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        loadNextPage();
      }
    }, { rootMargin: "280px 0px" });
  }

  observer.disconnect();
  observer.observe(sentinel.value);
}

onMounted(() => {
  loadBills(1);
});

onBeforeUnmount(() => {
  if (observer) observer.disconnect();
});
</script>

<template>
  <section class="view active">
    <div class="section-head">
      <div>
        <h2>최신 법안</h2>
        <div class="sub">최근 발의된 법안을 슥 살펴봐요</div>
      </div>
    </div>

    <div class="grid">
      <ApiStateCard
        v-if="errorState && !bills.length"
        :state="errorState"
        @retry="loadBills(1)"
      />
      <ApiStateCard
        v-else-if="isInitialLoading"
        :state="store.loadingState"
        :show-action="false"
      />
      <ApiStateCard
        v-else-if="!displayedBills.length"
        :state="store.emptyState('최신 법안이 아직 없어요', '백엔드 응답은 성공했지만 표시할 최신 법안이 없습니다.')"
        @retry="loadBills(1)"
      />
      <template v-else>
        <BillCard
          v-for="bill in displayedBills"
          :key="bill.id"
          :bill="bill"
          @select="store.openBill($event.id)"
        />
      </template>
    </div>

    <div ref="sentinel" class="post-load-sentinel" aria-hidden="true"></div>

    <div v-if="displayedBills.length" class="pagination-actions">
      <div class="pagination-status">
        {{ pagination.total_count }}건 중 {{ displayedBills.length }}건 표시
      </div>
      <button
        v-if="hasMore"
        class="pagination-more"
        type="button"
        :disabled="isLoadingMore"
        @click="loadNextPage"
      >
        {{ isLoadingMore ? "불러오는 중" : "더 보기" }}
      </button>
      <div v-else class="pagination-end">
        모든 최신 법안을 확인했어요
      </div>
    </div>
  </section>
</template>
