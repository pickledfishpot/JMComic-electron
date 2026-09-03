<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getIndex, type BookItem, type IndexResponse } from "../api/books";
import { useUserStore } from "../stores/user";
import { assetUrl } from "../api/client";
import PageHeader from "../components/PageHeader.vue";
import BookCard from "../components/BookCard.vue";
import StateBlock from "../components/StateBlock.vue";

const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const error = ref<string | null>(null);
const sections = ref<IndexResponse["sections"]>({});

const SECTION_COLORS = [
  "text-brand-pink",
  "text-brand-teal",
  "text-brand-lavender",
  "text-brand-coral",
  "text-brand-ochre",
];

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

function go(path: string) {
  router.push(path);
}

onMounted(() => {
  loadIndex();
  userStore.fetchMe();
});
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader :back="false" title="JMComic">
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/favorites')"
      >
        收藏
      </button>
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/history')"
      >
        历史
      </button>
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/downloads')"
      >
        下载
      </button>
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/local')"
      >
        本地
      </button>
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/tools')"
      >
        工具
      </button>
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/settings')"
      >
        设置
      </button>
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/categories')"
      >
        分类
      </button>
      <button
        class="rounded-md bg-ink px-4 py-1.5 text-sm font-semibold text-white transition hover:bg-ink-active"
        @click="go('/search')"
      >
        搜索
      </button>
      <button
        class="max-w-32 truncate rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="go('/login')"
      >
        {{ userStore.user ? userStore.user.username : "登录" }}
      </button>
    </PageHeader>

    <main class="mx-auto max-w-7xl p-6">
      <StateBlock v-if="loading" type="loading" />
      <StateBlock v-else-if="error" type="error" :message="error" @retry="loadIndex">
        <p class="mt-2 text-sm text-muted-soft">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
      </StateBlock>

      <div v-else class="space-y-12">
        <section v-for="(books, title, i) in sections" :key="title">
          <h2 class="display mb-4 text-xl" :class="SECTION_COLORS[i % SECTION_COLORS.length]">
            {{ title }}
          </h2>
          <div
            class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
          >
            <BookCard
              v-for="book in books"
              :key="book.id"
              :cover="assetUrl(book.coverUrl)"
              :title="book.title"
              :author="book.authorList.join(', ') || '未知作者'"
              @open="openBook(book)"
            />
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
