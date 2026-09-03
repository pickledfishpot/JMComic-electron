<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  getCategories,
  getCategoryBooks,
  type BookItem,
  type Category,
  type CategoryBooksResponse,
} from "../api/books";
import { useGoBack } from "../composables/useGoBack";

const router = useRouter();
const goBack = useGoBack();

const loading = ref(false);
const error = ref<string | null>(null);
const categories = ref<Category[]>([]);
const activeSlug = ref<string>("0");
const booksResult = ref<CategoryBooksResponse | null>(null);

const sortOptions = [
  { value: "mr", label: "最新" },
  { value: "mv", label: "最多点击" },
  { value: "mv_m", label: "月排行" },
  { value: "mv_w", label: "周排行" },
  { value: "mv_t", label: "日排行" },
  { value: "mp", label: "最多图片" },
  { value: "tf", label: "最多爱心" },
];

async function loadCategories() {
  loading.value = true;
  error.value = null;
  try {
    const res = await getCategories();
    categories.value = res.categories;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function loadCategoryBooks(slug: string, page = 1, sort = "mr") {
  loading.value = true;
  error.value = null;
  try {
    booksResult.value = await getCategoryBooks(slug, page, sort);
    activeSlug.value = slug;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

function openBook(book: BookItem) {
  router.push({ name: "book-detail", params: { id: book.id } });
}

onMounted(() => {
  loadCategories().then(() => loadCategoryBooks("0"));
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
      <h1 class="text-base font-bold">分类</h1>
    </header>

    <main class="p-6">
      <div
        v-if="loading && !categories.length"
        class="py-20 text-center text-gray-400"
      >
        加载中...
      </div>
      <div v-else-if="error" class="py-20 text-center text-red-400">
        <p>{{ error }}</p>
        <p class="mt-2 text-sm text-gray-500">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
        <button
          class="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
          @click="loadCategories"
        >
          重试
        </button>
      </div>

      <div v-else class="space-y-6">
        <div class="flex flex-wrap gap-2">
          <button
            class="rounded-full px-4 py-1.5 text-sm"
            :class="
              activeSlug === '0'
                ? 'bg-[#feca57] text-[#0f0f0f]'
                : 'bg-[#1a1a1a] text-gray-300 hover:bg-[#252525]'
            "
            @click="loadCategoryBooks('0')"
          >
            全部
          </button>
          <button
            v-for="cat in categories"
            :key="cat.id"
            class="rounded-full px-4 py-1.5 text-sm"
            :class="
              activeSlug === cat.slug
                ? 'bg-[#feca57] text-[#0f0f0f]'
                : 'bg-[#1a1a1a] text-gray-300 hover:bg-[#252525]'
            "
            @click="loadCategoryBooks(cat.slug)"
          >
            {{ cat.name }}
          </button>
        </div>

        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-400">
            {{ booksResult ? `共 ${booksResult.total} 本` : "" }}
          </p>
          <div class="flex gap-2">
            <button
              v-for="opt in sortOptions"
              :key="opt.value"
              class="rounded-full px-3 py-1 text-xs"
              :class="
                booksResult?.sort === opt.value
                  ? 'bg-[#feca57] text-[#0f0f0f]'
                  : 'bg-[#1a1a1a] text-gray-400 hover:bg-[#252525]'
              "
              @click="loadCategoryBooks(activeSlug, 1, opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <div
          v-if="booksResult"
          class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
          <div
            v-for="book in booksResult.books"
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
      </div>
    </main>
  </div>
</template>
