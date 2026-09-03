<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getHistory, removeHistory, type HistoryItem } from "../api/account";

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

function goBack() {
  router.back();
}

onMounted(load);
</script>

<template>
  <div class="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
    <header
      class="sticky top-0 z-10 flex items-center gap-3 border-b border-white/10 bg-[#0f0f0f]/90 px-4 py-3 backdrop-blur"
    >
      <button class="rounded-lg p-2 hover:bg-white/10" @click="goBack">
        ← 返回
      </button>
      <h1 class="text-base font-bold">阅读历史</h1>
    </header>

    <main class="mx-auto max-w-3xl p-6">
      <div v-if="loading" class="py-20 text-center text-gray-400">
        加载中...
      </div>
      <div v-else-if="error" class="py-20 text-center text-red-400">
        <p>{{ error }}</p>
        <button
          class="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
          @click="load"
        >
          重试
        </button>
      </div>
      <p v-else-if="!items.length" class="py-20 text-center text-gray-500">
        暂无阅读历史
      </p>

      <div v-else class="space-y-3">
        <p class="text-sm text-gray-500">共 {{ total }} 条</p>
        <div
          v-for="item in items"
          :key="item.bookId"
          class="flex items-center gap-4 rounded-xl bg-[#1a1a1a] p-3"
        >
          <img
            :src="coverOf(item.bookId)"
            class="h-24 w-18 cursor-pointer rounded-lg object-cover"
            @click="openBook(item)"
          />
          <div class="min-w-0 flex-1">
            <p
              class="cursor-pointer truncate font-medium hover:text-[#feca57]"
              @click="openBook(item)"
            >
              {{ item.title || `本子 ${item.bookId}` }}
            </p>
            <p class="mt-1 text-xs text-gray-500">
              读至第 {{ item.epsIndex + 1 }} 话 第 {{ item.pageIndex + 1 }} 页 ·
              {{ formatTime(item.updatedAt) }}
            </p>
            <div class="mt-2 flex gap-2">
              <button
                class="rounded-lg bg-[#feca57] px-3 py-1 text-xs font-medium text-black hover:opacity-90"
                @click="continueReading(item)"
              >
                继续阅读
              </button>
              <button
                class="rounded-lg bg-white/10 px-3 py-1 text-xs text-gray-400 hover:bg-white/20"
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
