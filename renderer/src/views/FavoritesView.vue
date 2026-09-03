<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  getFavorites,
  toggleFavorite,
  type FavoritesResponse,
} from "../api/account";
import { useUserStore } from "../stores/user";
import { useGoBack } from "../composables/useGoBack";
import type { BookItem } from "../api/books";

const router = useRouter();
const userStore = useUserStore();
const goBack = useGoBack();

const loading = ref(false);
const error = ref<string | null>(null);
const result = ref<FavoritesResponse | null>(null);
const sort = ref("mr");
const folderId = ref("0");
const page = ref(1);
const message = ref<string | null>(null);

async function load(nextPage = 1) {
  loading.value = true;
  error.value = null;
  try {
    const res = await getFavorites(nextPage, sort.value, folderId.value);
    result.value =
      nextPage > 1 && result.value
        ? { ...res, books: [...result.value.books, ...res.books] }
        : res;
    page.value = nextPage;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
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

onMounted(() => {
  if (!userStore.user) {
    // 用 replace 避免「收藏 → 登录 → 返回」形成回退循环
    router.replace("/login");
    return;
  }
  load(1);
});
</script>

<template>
  <div class="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
    <header
      class="sticky top-0 z-10 flex items-center gap-3 border-b border-white/10 bg-[#0f0f0f]/90 px-4 py-3 backdrop-blur"
    >
      <button class="rounded-lg p-2 hover:bg-white/10" @click="goBack">
        ← 返回
      </button>
      <h1 class="text-base font-bold">我的收藏</h1>
      <select
        v-model="sort"
        class="ml-auto rounded-lg bg-[#1a1a1a] px-2 py-1.5 text-sm outline-none"
        @change="reload"
      >
        <option value="mr" class="bg-[#1a1a1a]">按收藏时间</option>
        <option value="mp" class="bg-[#1a1a1a]">按更新时间</option>
      </select>
    </header>

    <main class="p-6">
      <div v-if="error" class="py-20 text-center text-red-400">
        <p>{{ error }}</p>
        <button
          class="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
          @click="reload"
        >
          重试
        </button>
      </div>
      <div
        v-else-if="loading && !result"
        class="py-20 text-center text-gray-400"
      >
        加载中...
      </div>

      <template v-else-if="result">
        <div v-if="result.folders.length" class="mb-4 flex flex-wrap gap-2">
          <button
            class="rounded-full px-3 py-1 text-xs"
            :class="
              folderId === '0'
                ? 'bg-[#feca57] text-black'
                : 'bg-white/10 text-gray-300'
            "
            @click="
              folderId = '0';
              reload();
            "
          >
            全部
          </button>
          <button
            v-for="folder in result.folders"
            :key="folder.id"
            class="rounded-full px-3 py-1 text-xs"
            :class="
              folderId === folder.id
                ? 'bg-[#feca57] text-black'
                : 'bg-white/10 text-gray-300'
            "
            @click="
              folderId = folder.id;
              reload();
            "
          >
            {{ folder.name }}
          </button>
        </div>

        <p v-if="message" class="mb-3 text-sm text-green-400">{{ message }}</p>

        <p class="mb-4 text-sm text-gray-500">共 {{ result.total }} 本收藏</p>

        <div
          v-if="result.books.length"
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6"
        >
          <div
            v-for="book in result.books"
            :key="book.id"
            class="group relative cursor-pointer"
            @click="openBook(book)"
          >
            <div class="aspect-[3/4] overflow-hidden rounded-xl bg-gray-800">
              <img
                :src="book.coverUrl"
                :alt="book.title"
                class="h-full w-full object-cover transition group-hover:scale-105"
                loading="lazy"
              />
            </div>
            <p class="mt-1.5 line-clamp-2 text-sm">{{ book.title }}</p>
            <button
              class="absolute right-2 top-2 hidden rounded-lg bg-black/70 px-2 py-1 text-xs text-red-300 group-hover:block"
              @click.stop="removeFavorite(book)"
            >
              取消收藏
            </button>
          </div>
        </div>
        <p v-else class="py-20 text-center text-gray-500">暂无收藏</p>

        <div v-if="result.books.length < result.total" class="mt-6 text-center">
          <button
            class="rounded-lg bg-white/10 px-6 py-2 text-sm hover:bg-white/20"
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
