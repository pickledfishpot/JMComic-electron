<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  getBookDetail,
  getBookComments,
  getReadingProgress,
  type BookDetail,
  type CommentsResponse,
  type ReadingProgress,
} from "../api/books";
import { toggleFavorite } from "../api/account";
import { startDownload } from "../api/downloads";
import { useUserStore } from "../stores/user";
import { useGoBack } from "../composables/useGoBack";

const props = defineProps<{ id: string }>();
const router = useRouter();
const userStore = useUserStore();

const loading = ref(false);
const error = ref<string | null>(null);
const book = ref<BookDetail | null>(null);
const progress = ref<ReadingProgress | null>(null);

const favoriteBusy = ref(false);
const favoriteMessage = ref<string | null>(null);
const downloadBusy = ref(false);
const downloadMessage = ref<string | null>(null);

const commentsLoading = ref(false);
const commentsError = ref<string | null>(null);
const commentsResult = ref<CommentsResponse | null>(null);

async function loadDetail() {
  loading.value = true;
  error.value = null;
  try {
    const [detail, progressRes] = await Promise.all([
      getBookDetail(props.id),
      getReadingProgress(props.id).catch(() => ({
        bookId: props.id,
        progress: null,
      })),
    ]);
    book.value = detail;
    progress.value = progressRes.progress;
    await loadComments();
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function loadComments(page = 1) {
  commentsLoading.value = true;
  commentsError.value = null;
  try {
    commentsResult.value = await getBookComments(props.id, page);
  } catch (err) {
    commentsError.value = String(err);
  } finally {
    commentsLoading.value = false;
  }
}

const goBack = useGoBack();

function startReading(epsIndex?: number) {
  const idx = epsIndex ?? progress.value?.epsIndex ?? 0;
  router.push(`/read/${props.id}/${idx}`);
}

async function toggleFav() {
  if (!userStore.user) {
    // 用 replace 避免「详情 → 登录 → 返回」形成回退循环
    router.replace("/login");
    return;
  }
  if (!book.value) return;
  favoriteBusy.value = true;
  favoriteMessage.value = null;
  try {
    const res = await toggleFavorite(book.value.id);
    favoriteMessage.value = res.message || "操作成功";
    book.value.isFavorite = !book.value.isFavorite;
  } catch (err) {
    favoriteMessage.value = String(err);
  } finally {
    favoriteBusy.value = false;
  }
}

async function downloadBook() {
  if (!book.value) return;
  downloadBusy.value = true;
  downloadMessage.value = null;
  try {
    const res = await startDownload(book.value.id, undefined, book.value.title);
    downloadMessage.value = `已创建 ${res.taskIds.length} 个下载任务`;
  } catch (err) {
    downloadMessage.value = String(err);
  } finally {
    downloadBusy.value = false;
  }
}

watch(() => props.id, loadDetail, { immediate: true });
</script>

<template>
  <div class="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
    <header
      class="sticky top-0 z-10 flex items-center gap-3 border-b border-white/10 bg-[#0f0f0f]/90 px-4 py-3 backdrop-blur"
    >
      <button class="rounded-lg p-2 hover:bg-white/10" @click="goBack">
        ← 返回
      </button>
      <h1 class="line-clamp-1 text-base font-bold">
        {{ book?.title || "书籍详情" }}
      </h1>
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
          @click="loadDetail"
        >
          重试
        </button>
      </div>

      <div v-else-if="book" class="mx-auto max-w-4xl space-y-8">
        <div class="flex flex-col gap-6 md:flex-row">
          <div class="w-full shrink-0 md:w-64">
            <div class="aspect-[3/4] overflow-hidden rounded-xl bg-gray-800">
              <img
                :src="book.coverUrl"
                :alt="book.title"
                class="h-full w-full object-cover"
              />
            </div>
          </div>

          <div class="flex-1">
            <h2 class="text-2xl font-bold">{{ book.title }}</h2>
            <div class="mt-2 flex flex-wrap gap-2 text-sm text-gray-400">
              <span>作者：{{ book.authorList.join(", ") || "未知" }}</span>
              <span v-if="book.likes">❤️ {{ book.likes }}</span>
              <span v-if="book.views">👁️ {{ book.views }}</span>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <span
                v-for="tag in book.tags"
                :key="tag"
                class="rounded-full bg-white/10 px-3 py-1 text-xs text-gray-300"
              >
                {{ tag }}
              </span>
            </div>

            <p
              v-if="book.description"
              class="mt-6 leading-relaxed text-gray-300"
            >
              {{ book.description }}
            </p>

            <div class="mt-8">
              <div class="mb-3 flex flex-wrap items-center gap-3">
                <h3 class="font-semibold">章节列表</h3>
                <button
                  class="rounded-lg bg-[#feca57] px-4 py-1.5 text-sm font-medium text-black hover:opacity-90"
                  @click="startReading()"
                >
                  {{
                    progress
                      ? `继续阅读 · 第 ${progress.epsIndex + 1} 话`
                      : "开始阅读"
                  }}
                </button>
                <button
                  class="rounded-lg px-4 py-1.5 text-sm"
                  :class="
                    book.isFavorite
                      ? 'bg-[#feca57]/20 text-[#feca57]'
                      : 'bg-white/10 hover:bg-white/20'
                  "
                  :disabled="favoriteBusy"
                  @click="toggleFav"
                >
                  {{ book.isFavorite ? "★ 已收藏" : "☆ 收藏" }}
                </button>
                <button
                  class="rounded-lg bg-white/10 px-4 py-1.5 text-sm hover:bg-white/20"
                  :disabled="downloadBusy"
                  @click="downloadBook"
                >
                  {{ downloadBusy ? "创建中..." : "⬇ 下载本书" }}
                </button>
                <router-link
                  to="/downloads"
                  class="text-xs text-gray-500 hover:text-gray-300"
                >
                  下载管理 →
                </router-link>
              </div>
              <p v-if="favoriteMessage" class="mb-2 text-xs text-gray-400">
                {{ favoriteMessage }}
              </p>
              <p v-if="downloadMessage" class="mb-2 text-xs text-gray-400">
                {{ downloadMessage }}
              </p>
              <div class="grid gap-2 sm:grid-cols-2">
                <button
                  v-for="eps in book.eps"
                  :key="eps.index"
                  class="rounded-lg bg-[#1a1a1a] px-4 py-3 text-left text-sm hover:bg-[#252525]"
                  @click="startReading(eps.index)"
                >
                  第 {{ eps.index + 1 }} 话
                  <span v-if="eps.name" class="ml-2 text-gray-500">{{
                    eps.name
                  }}</span>
                  <span
                    v-if="progress && progress.epsIndex === eps.index"
                    class="ml-2 text-xs text-[#feca57]"
                  >
                    ● 读至第 {{ progress.pageIndex + 1 }} 页
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-white/10 pt-8">
          <h3 class="mb-4 font-semibold">
            评论
            <span v-if="book.commentTotal" class="ml-2 text-sm text-gray-500">
              ({{ book.commentTotal }})
            </span>
          </h3>

          <div v-if="commentsLoading" class="py-10 text-center text-gray-400">
            加载评论中...
          </div>
          <div v-else-if="commentsError" class="py-10 text-center text-red-400">
            <p>{{ commentsError }}</p>
            <button
              class="mt-2 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
              @click="loadComments()"
            >
              重试
            </button>
          </div>

          <div v-else-if="commentsResult" class="space-y-4">
            <div
              v-for="comment in commentsResult.comments"
              :key="comment.id"
              class="rounded-xl bg-[#1a1a1a] p-4"
            >
              <div class="flex items-start gap-3">
                <img
                  v-if="comment.headUrl"
                  :src="comment.headUrl"
                  class="h-10 w-10 rounded-full object-cover"
                />
                <div
                  v-else
                  class="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-sm"
                >
                  {{ comment.name?.[0] || "?" }}
                </div>
                <div class="flex-1">
                  <div class="flex items-center gap-2 text-sm">
                    <span class="font-medium">{{ comment.name }}</span>
                    <span v-if="comment.title" class="text-xs text-[#feca57]">{{
                      comment.title
                    }}</span>
                    <span v-if="comment.date" class="text-xs text-gray-500">{{
                      comment.date
                    }}</span>
                  </div>
                  <p class="mt-2 text-sm text-gray-300">
                    {{ comment.content }}
                  </p>

                  <div
                    v-if="comment.subComments.length"
                    class="mt-3 space-y-2 pl-4"
                  >
                    <div
                      v-for="sub in comment.subComments"
                      :key="sub.id"
                      class="rounded-lg bg-[#0f0f0f] p-3 text-sm"
                    >
                      <div class="flex items-center gap-2">
                        <span class="font-medium">{{ sub.name }}</span>
                        <span v-if="sub.title" class="text-xs text-[#feca57]">{{
                          sub.title
                        }}</span>
                      </div>
                      <p class="mt-1 text-gray-400">{{ sub.content }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <p
              v-if="commentsResult.comments.length === 0"
              class="py-10 text-center text-gray-500"
            >
              暂无评论
            </p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
