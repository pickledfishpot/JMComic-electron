<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { listLocal, scanLocal, type LocalBook } from "../api/local";

const router = useRouter();
const loading = ref(false);
const scanning = ref(false);
const error = ref<string | null>(null);
const books = ref<LocalBook[]>([]);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    books.value = (await listLocal()).books;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function rescan() {
  scanning.value = true;
  error.value = null;
  try {
    books.value = (await scanLocal()).books;
  } catch (err) {
    error.value = String(err);
  } finally {
    scanning.value = false;
  }
}

function coverOf(book: LocalBook): string {
  return `/api/local/images/${book.id}/0/0`;
}

function openBook(book: LocalBook) {
  router.push(`/local/read/${book.id}`);
}

function goBack() {
  router.push("/");
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
      <h1 class="text-base font-bold">本地图库</h1>
      <button
        class="ml-auto rounded-lg bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20"
        :disabled="scanning"
        @click="rescan"
      >
        {{ scanning ? "扫描中..." : "重新扫描" }}
      </button>
    </header>

    <main class="p-6">
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
      <div v-else-if="!books.length" class="py-20 text-center text-gray-500">
        <p>本地图库为空</p>
        <p class="mt-2 text-sm">
          下载完成的漫画会出现在这里，也可以在设置中添加更多扫描目录。
        </p>
      </div>

      <div
        v-else
        class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6"
      >
        <div
          v-for="book in books"
          :key="book.id"
          class="group cursor-pointer overflow-hidden rounded-xl bg-[#1a1a1a] transition hover:scale-[1.02] hover:shadow-lg"
          @click="openBook(book)"
        >
          <div class="relative aspect-[3/4] overflow-hidden bg-gray-800">
            <img
              :src="coverOf(book)"
              :alt="book.title"
              class="h-full w-full object-cover transition group-hover:opacity-90"
              loading="lazy"
            />
            <span
              v-if="book.isZip"
              class="absolute right-2 top-2 rounded bg-black/70 px-1.5 py-0.5 text-xs text-gray-300"
            >
              ZIP
            </span>
          </div>
          <div class="p-3">
            <h3 class="line-clamp-2 text-sm font-medium leading-snug">
              {{ book.title }}
            </h3>
            <p class="mt-1 truncate text-xs text-gray-500">
              {{ book.eps.length }} 话 · {{ book.pageCount }} 页
            </p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
