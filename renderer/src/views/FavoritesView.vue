<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  getFavorites,
  toggleFavorite,
  type FavoritesResponse,
} from "../api/account";
import { useUserStore } from "../stores/user";
import { assetUrl } from "../api/client";
import type { BookItem } from "../api/books";
import PageHeader from "../components/PageHeader.vue";
import BookCard from "../components/BookCard.vue";
import PillTabs from "../components/PillTabs.vue";
import StateBlock from "../components/StateBlock.vue";

const router = useRouter();
const userStore = useUserStore();

const loading = ref(false);
const error = ref<string | null>(null);
const result = ref<FavoritesResponse | null>(null);
const sort = ref("mr");
const folderId = ref("0");
const page = ref(1);
const message = ref<string | null>(null);
// 收藏请求序号：翻页/筛选快速变化时，仅采纳最新一次响应
let favReqSeq = 0;

async function load(nextPage = 1) {
  const seq = ++favReqSeq;
  loading.value = true;
  error.value = null;
  try {
    const res = await getFavorites(nextPage, sort.value, folderId.value);
    if (seq !== favReqSeq) return; // 过期响应
    result.value =
      nextPage > 1 && result.value
        ? { ...res, books: [...result.value.books, ...res.books] }
        : res;
    page.value = nextPage;
  } catch (err) {
    if (seq === favReqSeq) error.value = String(err);
  } finally {
    if (seq === favReqSeq) loading.value = false;
  }
}

function reload() {
  result.value = null;
  load(1);
}

function openBook(book: BookItem) {
  router.push(`/book/${book.id}`);
}

async function removeFavorite(book: BookItem) {
  message.value = null;
  try {
    const res = await toggleFavorite(book.id);
    message.value = res.message || "已取消收藏";
    reload();
  } catch (err) {
    error.value = String(err);
  }
}

onMounted(async () => {
  // 等待会话探测完成再判定登录，避免慢网络下误跳登录页
  if (!userStore.loaded) {
    await userStore.fetchMe();
  }
  if (!userStore.user) {
    // 用 replace 避免「收藏 → 登录 → 返回」形成回退循环
    router.replace("/login");
    return;
  }
  load(1);
});
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="我的收藏">
      <select
        v-model="sort"
        class="rounded-md border border-hairline bg-canvas px-2 py-1.5 text-sm outline-none"
        @change="reload"
      >
        <option value="mr">按收藏时间</option>
        <option value="mp">按更新时间</option>
      </select>
    </PageHeader>

    <main class="p-6">
      <StateBlock v-if="error" type="error" :message="error" @retry="reload" />
      <StateBlock v-else-if="loading && !result" type="loading" />

      <template v-else-if="result">
        <PillTabs
          v-if="result.folders.length"
          v-model="folderId"
          class="mb-4"
          size="sm"
          :options="[
            { value: '0', label: '全部' },
            ...result.folders.map((f) => ({ value: f.id, label: f.name })),
          ]"
          @update:model-value="reload"
        />

        <p v-if="message" class="mb-3 text-sm text-success">{{ message }}</p>

        <p class="mb-4 text-sm text-muted">共 {{ result.total }} 本收藏</p>

        <div
          v-if="result.books.length"
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6"
        >
          <BookCard
            v-for="book in result.books"
            :key="book.id"
            :cover="assetUrl(book.coverUrl)"
            :title="book.title"
            @open="openBook(book)"
          >
            <template #badge>
              <button
                class="absolute right-2 top-2 hidden rounded-md bg-ink/70 px-2 py-1 text-xs text-white group-hover:block"
                @click.stop="removeFavorite(book)"
              >
                取消收藏
              </button>
            </template>
          </BookCard>
        </div>
        <StateBlock v-else type="empty" message="暂无收藏" />

        <div v-if="result.books.length < result.total" class="mt-6 text-center">
          <button
            class="rounded-md border border-hairline bg-canvas px-6 py-2 text-sm font-medium transition hover:bg-surface-soft"
            :disabled="loading"
            @click="load(page + 1)"
          >
            {{ loading ? "加载中..." : "加载更多" }}
          </button>
        </div>
      </template>
    </main>
  </div>
</template>
