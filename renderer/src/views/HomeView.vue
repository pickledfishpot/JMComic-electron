<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getIndex, type BookItem, type IndexResponse } from "../api/books";
import { useUserStore } from "../stores/user";
import { assetUrl } from "../api/client";
import { brandTheme } from "../utils/brand";
import PageHeader from "../components/PageHeader.vue";
import BookCard from "../components/BookCard.vue";
import StateBlock from "../components/StateBlock.vue";

const router = useRouter();
const userStore = useUserStore();
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
          <div class="mb-4 flex items-center gap-2.5">
            <span class="h-7 w-1.5 rounded-full" :class="brandTheme(i).bg" />
            <h2
              class="display text-2xl"
              :class="brandTheme(i).title"
            >
              {{ title }}
            </h2>
          </div>

          <!-- 特色大卡：Clay 饱和单色 feature-card，每区取轮换色 -->
          <div
            v-if="books.length"
            class="mb-4 flex cursor-pointer gap-5 overflow-hidden rounded-xl p-5 transition hover:opacity-95 sm:gap-8 sm:p-7"
            :class="brandTheme(i).bg"
            @click="openBook(books[0])"
          >
            <div class="flex min-w-0 flex-1 flex-col justify-center">
              <p
                class="text-[11px] font-bold uppercase tracking-[0.2em] opacity-75"
                :class="brandTheme(i).onBg"
              >
                {{ title }} · 精选
              </p>
              <h3
                class="display mt-2 line-clamp-2 text-2xl leading-tight"
                :class="brandTheme(i).onBg"
              >
                {{ books[0].title }}
              </h3>
              <p class="mt-1.5 truncate text-sm opacity-80" :class="brandTheme(i).onBg">
                {{ books[0].authorList.join(", ") || "未知作者" }}
              </p>
              <span
                class="mt-4 inline-flex w-fit items-center rounded-md bg-canvas px-4 py-2 text-sm font-semibold text-ink shadow-sm transition hover:bg-white"
              >
                立即阅读 →
              </span>
            </div>
            <div class="w-28 shrink-0 self-center sm:w-40">
              <div class="aspect-[3/4] overflow-hidden rounded-lg shadow-xl">
                <img
                  :src="assetUrl(books[0].coverUrl)"
                  :alt="books[0].title"
                  class="h-full w-full object-cover"
                />
              </div>
            </div>
          </div>

          <div
            class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
          >
            <BookCard
              v-for="book in books.slice(1)"
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
