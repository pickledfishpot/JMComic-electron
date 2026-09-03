<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { searchBooks, type BookItem, type SearchResponse } from "../api/books";

const route = useRoute();
const router = useRouter();

const query = ref(String(route.query.q || ""));
const page = ref(Number(route.query.page) || 1);
const sort = ref(String(route.query.sort || "mr"));
const loading = ref(false);
const error = ref<string | null>(null);
const result = ref<SearchResponse | null>(null);

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
  loading.value = true;
  error.value = null;
  try {
    result.value = await searchBooks(
      query.value.trim(),
      page.value,
      sort.value,
    );
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
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
  <div class="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
    <header
      class="sticky top-0 z-10 flex items-center gap-3 border-b border-white/10 bg-[#0f0f0f]/90 px-4 py-3 backdrop-blur"
    >
      <button class="rounded-lg p-2 hover:bg-white/10" @click="router.back()">
        ← 返回
      </button>
      <form class="flex flex-1 gap-2" @submit.prevent="submitSearch">
        <input
          v-model="query"
          type="search"
          placeholder="搜索漫画..."
          class="flex-1 rounded-lg bg-[#1a1a1a] px-4 py-2 text-sm outline-none ring-1 ring-white/10 focus:ring-[#feca57]"
        />
        <button
          type="submit"
          class="rounded-lg bg-[#feca57] px-4 py-2 text-sm font-medium text-[#0f0f0f] hover:bg-[#ffdb7a]"
        >
          搜索
        </button>
      </form>
    </header>

    <main class="p-6">
      <div v-if="!query" class="py-20 text-center text-gray-500">
        输入关键词开始搜索
      </div>

      <div v-else-if="loading" class="py-20 text-center text-gray-400">
        加载中...
      </div>
      <div v-else-if="error" class="py-20 text-center text-red-400">
        <p>{{ error }}</p>
        <p class="mt-2 text-sm text-gray-500">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
        <button
          class="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
          @click="loadSearch"
        >
          重试
        </button>
      </div>

      <div v-else-if="result" class="space-y-6">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-400">共 {{ result.total }} 条结果</p>
          <div class="flex gap-2">
            <button
              v-for="opt in sortOptions"
              :key="opt.value"
              class="rounded-full px-3 py-1 text-xs"
              :class="
                sort === opt.value
                  ? 'bg-[#feca57] text-[#0f0f0f]'
                  : 'bg-[#1a1a1a] text-gray-400 hover:bg-[#252525]'
              "
              @click="changeSort(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
          <div
            v-for="book in result.books"
            :key="book.id"
            class="group cursor-pointer overflow-hidden rounded-xl bg-[#1a1a1a] transition hover:scale-[1.02] hover:shadow-lg"
            @click="openBook(book)"
          >
            <div class="aspect-[3/4] overflow-hidden bg-gray-800">
              <img
                :src="book.coverUrl"
                :alt="book.title"
                class="h-full w-full object-cover transition group-hover:opacity-90"
                loading="lazy"
              />
            </div>
            <div class="p-3">
              <h3 class="line-clamp-2 text-sm font-medium leading-snug">
                {{ book.title }}
              </h3>
              <p class="mt-1 truncate text-xs text-gray-500">
                {{ book.authorList.join(", ") || "未知作者" }}
              </p>
            </div>
          </div>
        </div>

        <div class="flex justify-center gap-2 pt-4">
          <button
            class="rounded-lg bg-[#1a1a1a] px-4 py-2 text-sm hover:bg-[#252525] disabled:opacity-50"
            :disabled="page <= 1"
            @click="changePage(page - 1)"
          >
            上一页
          </button>
          <span class="px-4 py-2 text-sm text-gray-400">第 {{ page }} 页</span>
          <button
            class="rounded-lg bg-[#1a1a1a] px-4 py-2 text-sm hover:bg-[#252525] disabled:opacity-50"
            :disabled="result.books.length === 0"
            @click="changePage(page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </main>
  </div>
</template>
