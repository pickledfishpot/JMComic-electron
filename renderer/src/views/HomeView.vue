<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getIndex, type BookItem, type IndexResponse } from "../api/books";

const router = useRouter();
const loading = ref(false);
const error = ref<string | null>(null);
const sections = ref<IndexResponse["sections"]>({});

async function loadIndex() {
  loading.value = true;
  error.value = null;
  try {
    const res = await getIndex();
    sections.value = res.sections;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

function openBook(book: BookItem) {
  router.push({ name: "book-detail", params: { id: book.id } });
}

function goSearch() {
  router.push({ name: "search" });
}

function goCategories() {
  router.push({ name: "categories" });
}

onMounted(() => {
  loadIndex();
});
</script>

<template>
  <div class="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0f0f0f]/90 px-6 py-4 backdrop-blur"
    >
      <h1 class="text-xl font-bold">JMComic</h1>
      <div class="flex gap-2">
        <button
          class="rounded-lg bg-[#1a1a1a] px-4 py-2 text-sm hover:bg-[#252525]"
          @click="goCategories"
        >
          分类
        </button>
        <button
          class="rounded-lg bg-[#feca57] px-4 py-2 text-sm font-medium text-[#0f0f0f] hover:bg-[#ffdb7a]"
          @click="goSearch"
        >
          搜索
        </button>
      </div>
    </header>

    <main class="p-6">
      <div v-if="loading" class="py-20 text-center text-gray-400">
        加载中...
      </div>
      <div v-else-if="error" class="py-20 text-center text-red-400">
        <p>{{ error }}</p>
        <p class="mt-2 text-sm text-gray-500">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
        <button
          class="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
          @click="loadIndex"
        >
          重试
        </button>
      </div>

      <div v-else class="space-y-10">
        <section v-for="(books, title) in sections" :key="title">
          <h2 class="mb-4 text-lg font-semibold text-[#feca57]">{{ title }}</h2>
          <div
            class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
          >
            <div
              v-for="book in books"
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
        </section>
      </div>
    </main>
  </div>
</template>
