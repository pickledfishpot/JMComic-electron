<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { searchBooks, type BookItem, type SearchResponse } from "../api/books";
import { assetUrl } from "../api/client";
import { useGoBack } from "../composables/useGoBack";
import { BRAND_PILL_COLORS } from "../utils/brand";
import BookCard from "../components/BookCard.vue";
import PillTabs from "../components/PillTabs.vue";
import StateBlock from "../components/StateBlock.vue";

const route = useRoute();
const router = useRouter();
const goBack = useGoBack();

const query = ref(String(route.query.q || ""));
const page = ref(Number(route.query.page) || 1);
const sort = ref(String(route.query.sort || "mr"));
const loading = ref(false);
const error = ref<string | null>(null);
const result = ref<SearchResponse | null>(null);
// 观察到的每页最大条数，作为 pageSize 估算值（JM 页大小由服务端固定，
// 尾页不满员时不能用当前页条数当 pageSize，否则会多放出空白页）
const pageSize = ref(0);
// 搜索请求序号：关键词/页码快速变化时，仅采纳最新一次响应
let searchReqSeq = 0;

const sortOptions = [
  { value: "mr", label: "最新" },
  { value: "mv", label: "最多点击" },
  { value: "mp", label: "最多图片" },
  { value: "tf", label: "最多爱心" },
];

async function loadSearch() {
  if (!query.value.trim()) {
    result.value = null;
    return;
  }
  const seq = ++searchReqSeq;
  loading.value = true;
  error.value = null;
  try {
    const res = await searchBooks(query.value.trim(), page.value, sort.value);
    if (seq !== searchReqSeq) return; // 过期响应
    result.value = res;
    if (res.books.length > pageSize.value) pageSize.value = res.books.length;
  } catch (err) {
    if (seq === searchReqSeq) error.value = String(err);
  } finally {
    if (seq === searchReqSeq) loading.value = false;
  }
}

function submitSearch() {
  page.value = 1;
  router.push({
    query: { q: query.value.trim(), page: "1", sort: sort.value },
  });
}

function changeSort(newSort: string) {
  sort.value = newSort;
  page.value = 1;
  router.push({ query: { q: query.value.trim(), page: "1", sort: newSort } });
}

function changePage(newPage: number) {
  page.value = newPage;
  router.push({
    query: { q: query.value.trim(), page: String(newPage), sort: sort.value },
  });
}

function openBook(book: BookItem) {
  router.push({ name: "book-detail", params: { id: book.id } });
}

watch(
  () => [route.query.q, route.query.page, route.query.sort],
  () => {
    query.value = String(route.query.q || "");
    page.value = Number(route.query.page) || 1;
    sort.value = String(route.query.sort || "mr");
    loadSearch();
  },
  { immediate: true },
);
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <header
      class="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-hairline bg-canvas/90 px-4 backdrop-blur"
    >
      <button
        class="rounded-md px-2 py-1.5 text-sm font-medium text-muted transition hover:bg-surface-card hover:text-ink"
        @click="goBack"
      >
        ← 返回
      </button>
      <form class="flex min-w-0 flex-1 gap-2" @submit.prevent="submitSearch">
        <input
          v-model="query"
          type="search"
          placeholder="搜索漫画..."
          class="input flex-1 text-sm"
        />
        <button
          type="submit"
          class="rounded-md bg-ink px-4 text-sm font-semibold text-white transition hover:bg-ink-active"
        >
          搜索
        </button>
      </form>
    </header>

    <main class="p-6">
      <StateBlock v-if="!query" type="empty" message="输入关键词开始搜索" />
      <StateBlock v-else-if="loading" type="loading" />
      <StateBlock
        v-else-if="error"
        type="error"
        :message="error"
        @retry="loadSearch"
      >
        <p class="mt-2 text-sm text-muted-soft">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
      </StateBlock>

      <div v-else-if="result" class="space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-muted">共 {{ result.total }} 条结果</p>
          <PillTabs
            :options="sortOptions"
            :model-value="sort"
            size="sm"
            :colors="BRAND_PILL_COLORS"
            @update:model-value="changeSort"
          />
        </div>

        <div
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
          <BookCard
            v-for="book in result.books"
            :key="book.id"
            :cover="assetUrl(book.coverUrl)"
            :title="book.title"
            :author="book.authorList.join(', ') || '未知作者'"
            @open="openBook(book)"
          />
        </div>

        <div class="flex justify-center gap-2 pt-4">
          <button
            class="rounded-md border border-hairline bg-canvas px-4 py-2 text-sm font-medium transition hover:bg-surface-soft disabled:opacity-50"
            :disabled="page <= 1"
            @click="changePage(page - 1)"
          >
            上一页
          </button>
          <span class="px-4 py-2 text-sm text-muted">第 {{ page }} 页</span>
          <button
            class="rounded-md border border-hairline bg-canvas px-4 py-2 text-sm font-medium transition hover:bg-surface-soft disabled:opacity-50"
            :disabled="
              result.books.length === 0 ||
              (pageSize > 0 && page * pageSize >= result.total)
            "
            @click="changePage(page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </main>
  </div>
</template>
