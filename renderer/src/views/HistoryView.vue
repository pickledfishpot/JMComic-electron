<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getHistory, removeHistory, type HistoryItem } from "../api/account";
import PageHeader from "../components/PageHeader.vue";
import StateBlock from "../components/StateBlock.vue";

const router = useRouter();
const loading = ref(false);
const error = ref<string | null>(null);
const items = ref<HistoryItem[]>([]);
const total = ref(0);

function coverOf(bookId: string): string {
  return `/api/images/media/albums/${bookId}_3x4.jpg`;
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const res = await getHistory(1, 100);
    items.value = res.items;
    total.value = res.total;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function remove(item: HistoryItem) {
  await removeHistory(item.bookId).catch(() => {});
  await load();
}

function openBook(item: HistoryItem) {
  router.push(`/book/${item.bookId}`);
}

function continueReading(item: HistoryItem) {
  router.push(`/read/${item.bookId}/${item.epsIndex}`);
}

onMounted(load);
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="阅读历史" />

    <main class="mx-auto max-w-3xl p-6">
      <StateBlock v-if="loading" type="loading" />
      <StateBlock v-else-if="error" type="error" :message="error" @retry="load" />
      <StateBlock
        v-else-if="!items.length"
        type="empty"
        message="暂无阅读历史"
      />

      <div v-else class="space-y-3">
        <p class="text-sm text-muted">共 {{ total }} 条</p>
        <div
          v-for="item in items"
          :key="item.bookId"
          class="card flex items-center gap-4 p-3"
        >
          <img
            :src="coverOf(item.bookId)"
            class="h-24 w-18 cursor-pointer rounded-md object-cover"
            @click="openBook(item)"
          />
          <div class="min-w-0 flex-1">
            <p
              class="cursor-pointer truncate font-medium hover:text-brand-coral"
              @click="openBook(item)"
            >
              {{ item.title || `本子 ${item.bookId}` }}
            </p>
            <p class="mt-1 text-xs text-muted-soft">
              读至第 {{ item.epsIndex + 1 }} 话 第 {{ item.pageIndex + 1 }} 页 ·
              {{ formatTime(item.updatedAt) }}
            </p>
            <div class="mt-2 flex gap-2">
              <button
                class="rounded-md bg-ink px-3 py-1 text-xs font-semibold text-white transition hover:bg-ink-active"
                @click="continueReading(item)"
              >
                继续阅读
              </button>
              <button
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium text-muted transition hover:bg-surface-soft hover:text-ink"
                @click="remove(item)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
