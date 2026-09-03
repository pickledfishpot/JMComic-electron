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
import { assetUrl } from "../api/client";
import { useUserStore } from "../stores/user";
import PageHeader from "../components/PageHeader.vue";
import StateBlock from "../components/StateBlock.vue";

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
// 详情/评论请求序号：路由快速切换书籍时，仅采纳最新一次响应
let detailReqSeq = 0;

async function loadDetail() {
  const seq = ++detailReqSeq;
  loading.value = true;
  error.value = null;
  try {
    const id = props.id;
    const [detail, progressRes] = await Promise.all([
      getBookDetail(id),
      getReadingProgress(id).catch(() => ({
        bookId: id,
        progress: null,
      })),
    ]);
    if (seq !== detailReqSeq) return; // 已切换到新书籍，丢弃过期响应
    book.value = detail;
    progress.value = progressRes.progress;
    await loadComments(seq);
  } catch (err) {
    if (seq === detailReqSeq) error.value = String(err);
  } finally {
    if (seq === detailReqSeq) loading.value = false;
  }
}

async function loadComments(page = 1, seq = detailReqSeq) {
  commentsLoading.value = true;
  commentsError.value = null;
  try {
    const res = await getBookComments(props.id, page);
    if (seq !== detailReqSeq) return;
    commentsResult.value = res;
  } catch (err) {
    if (seq === detailReqSeq) commentsError.value = String(err);
  } finally {
    if (seq === detailReqSeq) commentsLoading.value = false;
  }
}

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
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader :title="book?.title || '书籍详情'" />

    <main class="p-6">
      <StateBlock v-if="loading" type="loading" />
      <StateBlock v-else-if="error" type="error" :message="error" @retry="loadDetail">
        <p class="mt-2 text-sm text-muted-soft">
          JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
        </p>
      </StateBlock>

      <div v-else-if="book" class="mx-auto max-w-4xl space-y-8">
        <div class="flex flex-col gap-6 md:flex-row">
          <div class="w-full shrink-0 md:w-64">
            <div class="aspect-[3/4] overflow-hidden rounded-xl bg-surface-strong">
              <img
                :src="assetUrl(book.coverUrl)"
                :alt="book.title"
                class="h-full w-full object-cover"
              />
            </div>
          </div>

          <div class="flex-1">
            <h2 class="display text-2xl">{{ book.title }}</h2>
            <div class="mt-2 flex flex-wrap gap-2 text-sm text-muted">
              <span>作者：{{ book.authorList.join(", ") || "未知" }}</span>
              <span v-if="book.likes">❤️ {{ book.likes }}</span>
              <span v-if="book.views">👁️ {{ book.views }}</span>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <span v-for="tag in book.tags" :key="tag" class="badge-pill">
                {{ tag }}
              </span>
            </div>

            <p v-if="book.description" class="mt-6 leading-relaxed text-body">
              {{ book.description }}
            </p>

            <div class="mt-8">
              <div class="mb-3 flex flex-wrap items-center gap-3">
                <h3 class="font-semibold">章节列表</h3>
                <button
                  class="inline-flex h-9 items-center rounded-md bg-ink px-4 text-xs font-semibold text-white transition hover:bg-ink-active"
                  @click="startReading()"
                >
                  {{
                    progress
                      ? `继续阅读 · 第 ${progress.epsIndex + 1} 话`
                      : "开始阅读"
                  }}
                </button>
                <button
                  class="inline-flex h-9 items-center gap-1 rounded-md px-4 text-xs font-semibold transition"
                  :class="
                    book.isFavorite
                      ? 'bg-brand-pink/15 text-brand-pink'
                      : 'border border-hairline bg-canvas text-ink hover:bg-surface-soft'
                  "
                  :disabled="favoriteBusy"
                  @click="toggleFav"
                >
                  {{ book.isFavorite ? "★ 已收藏" : "☆ 收藏" }}
                </button>
                <button
                  class="inline-flex h-9 items-center gap-1 rounded-md border border-hairline bg-canvas px-4 text-xs font-semibold text-ink transition hover:bg-surface-soft"
                  :disabled="downloadBusy"
                  @click="downloadBook"
                >
                  {{ downloadBusy ? "创建中..." : "⬇ 下载本书" }}
                </button>
                <router-link
                  to="/downloads"
                  class="text-xs text-muted-soft underline-offset-4 hover:text-ink hover:underline"
                >
                  下载管理 →
                </router-link>
              </div>
              <p v-if="favoriteMessage" class="mb-2 text-xs text-muted">
                {{ favoriteMessage }}
              </p>
              <p v-if="downloadMessage" class="mb-2 text-xs text-muted">
                {{ downloadMessage }}
              </p>
              <div class="grid gap-2 sm:grid-cols-2">
                <button
                  v-for="eps in book.eps"
                  :key="eps.index"
                  class="rounded-md bg-surface-card px-4 py-3 text-left text-sm transition hover:bg-surface-strong"
                  @click="startReading(eps.index)"
                >
                  第 {{ eps.index + 1 }} 话
                  <span v-if="eps.name" class="ml-2 text-muted-soft">{{
                    eps.name
                  }}</span>
                  <span
                    v-if="progress && progress.epsIndex === eps.index"
                    class="ml-2 text-xs text-brand-teal"
                  >
                    ● 读至第 {{ progress.pageIndex + 1 }} 页
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-hairline pt-8">
          <h3 class="mb-4 font-semibold">
            评论
            <span v-if="book.commentTotal" class="ml-2 text-sm text-muted-soft">
              ({{ book.commentTotal }})
            </span>
          </h3>

          <StateBlock
            v-if="commentsLoading"
            type="loading"
            message="加载评论中..."
          />
          <StateBlock
            v-else-if="commentsError"
            type="error"
            :message="commentsError"
            @retry="loadComments()"
          />

          <div v-else-if="commentsResult" class="space-y-4">
            <div
              v-for="comment in commentsResult.comments"
              :key="comment.id"
              class="card p-4"
            >
              <div class="flex items-start gap-3">
                <img
                  v-if="comment.headUrl"
                  :src="assetUrl(comment.headUrl)"
                  class="h-10 w-10 rounded-full object-cover"
                />
                <div
                  v-else
                  class="flex h-10 w-10 items-center justify-center rounded-full bg-surface-strong text-sm"
                >
                  {{ comment.name?.[0] || "?" }}
                </div>
                <div class="flex-1">
                  <div class="flex items-center gap-2 text-sm">
                    <span class="font-medium">{{ comment.name }}</span>
                    <span v-if="comment.title" class="text-xs text-brand-coral">{{
                      comment.title
                    }}</span>
                    <span v-if="comment.date" class="text-xs text-muted-soft">{{
                      comment.date
                    }}</span>
                  </div>
                  <p class="mt-2 text-sm text-body">
                    {{ comment.content }}
                  </p>

                  <div
                    v-if="comment.subComments.length"
                    class="mt-3 space-y-2 pl-4"
                  >
                    <div
                      v-for="sub in comment.subComments"
                      :key="sub.id"
                      class="rounded-md bg-surface-soft p-3 text-sm"
                    >
                      <div class="flex items-center gap-2">
                        <span class="font-medium">{{ sub.name }}</span>
                        <span v-if="sub.title" class="text-xs text-brand-coral">{{
                          sub.title
                        }}</span>
                      </div>
                      <p class="mt-1 text-muted">{{ sub.content }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <StateBlock
              v-if="commentsResult.comments.length === 0"
              type="empty"
              message="暂无评论"
            />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
