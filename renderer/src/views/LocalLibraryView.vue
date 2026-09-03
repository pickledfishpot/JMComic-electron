<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { listLocal, scanLocal, type LocalBook } from "../api/local";
import { assetUrl } from "../api/client";
import PageHeader from "../components/PageHeader.vue";
import BookCard from "../components/BookCard.vue";
import StateBlock from "../components/StateBlock.vue";

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
  return assetUrl(`/api/local/images/${book.id}/0/0`);
}

function openBook(book: LocalBook) {
  router.push(`/local/read/${book.id}`);
}

onMounted(load);
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="本地图库">
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        :disabled="scanning"
        @click="rescan"
      >
        {{ scanning ? "扫描中..." : "重新扫描" }}
      </button>
    </PageHeader>

    <main class="p-6">
      <StateBlock v-if="loading" type="loading" />
      <StateBlock v-else-if="error" type="error" :message="error" @retry="load" />
      <StateBlock v-else-if="!books.length" type="empty" message="本地图库为空">
        <p class="mt-2 text-sm">
          下载完成的漫画会出现在这里，也可以在设置中添加更多扫描目录。
        </p>
      </StateBlock>

      <div
        v-else
        class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6"
      >
        <BookCard
          v-for="book in books"
          :key="book.id"
          :cover="coverOf(book)"
          :title="book.title"
          :author="`${book.eps.length} 话 · ${book.pageCount} 页`"
          @open="openBook(book)"
        >
          <template #badge>
            <span
              v-if="book.isZip"
              class="absolute right-2 top-2 rounded bg-ink/70 px-1.5 py-0.5 text-xs text-white"
            >
              ZIP
            </span>
          </template>
        </BookCard>
      </div>
    </main>
  </div>
</template>
