<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useRouter } from "vue-router";
import {
  getBookDetail,
  getEpsPages,
  getReadingProgress,
  saveReadingProgress,
  type BookDetail,
  type EpsPage,
  type ReadingProgress,
} from "../api/books";
import {
  getLocalBook,
  getLocalPages,
  getLocalProgress,
  saveLocalProgress,
  type LocalBook,
  type LocalPage,
} from "../api/local";

const props = defineProps<{
  bookId: string;
  epsIndex?: string;
  local?: string;
}>();
const router = useRouter();
const isLocal = computed(() => props.local === "1");

const book = ref<BookDetail | LocalBook | null>(null);
const pages = ref<EpsPage[] | LocalPage[]>([]);
const epsIndex = ref(0);
const currentPage = ref(0);
const loading = ref(true);
const pagesLoading = ref(false);
const error = ref<string | null>(null);

type ReaderMode = "flip" | "scroll";
const mode = ref<ReaderMode>(
  (localStorage.getItem("jmcomic-reader-mode") as ReaderMode) || "flip",
);

/** 加载失败需重试的页（索引 -> 重试计数，作为 img :key 的一部分强制重建） */
const failedPages = ref(new Map<number, number>());
const toolbarVisible = ref(true);
const scrollContainer = ref<HTMLElement | null>(null);

const totalPages = computed(() => pages.value.length);
const current = computed(() => pages.value[currentPage.value] ?? null);
const canPrevEps = computed(() => epsIndex.value > 0);
const canNextEps = computed(
  () => book.value !== null && epsIndex.value < book.value.eps.length - 1,
);
const isLastPage = computed(
  () => totalPages.value > 0 && currentPage.value === totalPages.value - 1,
);

let toolbarTimer: ReturnType<typeof setTimeout> | undefined;
let progressTimer: ReturnType<typeof setTimeout> | undefined;
let observer: IntersectionObserver | null = null;

function showToolbar() {
  toolbarVisible.value = true;
  clearTimeout(toolbarTimer);
  toolbarTimer = setTimeout(() => {
    toolbarVisible.value = false;
  }, 2500);
}

async function loadPages(index: number, startPage = 0) {
  pagesLoading.value = true;
  error.value = null;
  try {
    const resp = isLocal.value
      ? await getLocalPages(props.bookId, index)
      : await getEpsPages(props.bookId, index);
    pages.value = resp.pages;
    epsIndex.value = resp.epsIndex;
    currentPage.value = Math.min(Math.max(startPage, 0), resp.pages.length - 1);
    failedPages.value = new Map();
    router.replace(
      isLocal.value
        ? `/local/read/${props.bookId}/${resp.epsIndex}`
        : `/read/${props.bookId}/${resp.epsIndex}`,
    );
  } catch (err) {
    error.value = String(err);
  } finally {
    pagesLoading.value = false;
  }
}

async function switchEps(index: number) {
  if (index === epsIndex.value || index < 0) return;
  await loadPages(index, 0);
}

function goBack() {
  router.push(isLocal.value ? "/local" : `/book/${props.bookId}`);
}

function nextPage() {
  if (currentPage.value < totalPages.value - 1) {
    currentPage.value += 1;
  }
}

function prevPage() {
  if (currentPage.value > 0) {
    currentPage.value -= 1;
  }
}

function onFlipClick(event: MouseEvent) {
  const ratio = event.clientX / window.innerWidth;
  if (ratio < 0.35) {
    prevPage();
  } else if (ratio > 0.65) {
    nextPage();
  } else {
    showToolbar();
  }
}

function onWheel(event: WheelEvent) {
  if (mode.value !== "flip") return;
  if (event.deltaY > 0) {
    nextPage();
  } else if (event.deltaY < 0) {
    prevPage();
  }
}

function toggleMode() {
  mode.value = mode.value === "flip" ? "scroll" : "flip";
  localStorage.setItem("jmcomic-reader-mode", mode.value);
}

async function toggleFullscreen() {
  if (document.fullscreenElement) {
    await document.exitFullscreen();
  } else {
    await document.documentElement.requestFullscreen();
  }
}

function onImgError(pageIndex: number) {
  failedPages.value = new Map(failedPages.value).set(
    pageIndex,
    (failedPages.value.get(pageIndex) ?? 0) + 1,
  );
}

function retryPage(pageIndex: number) {
  // 重试时移除缓存条目由后端保证（失败后未写缓存），这里仅强制重建 <img>
  failedPages.value = new Map(failedPages.value).set(pageIndex, 0);
}

function pageKey(page: EpsPage): string {
  return `${page.index}-${failedPages.value.get(page.index) ?? 0}`;
}

/* ---------------- 键盘快捷键 ---------------- */

function onKeyDown(event: KeyboardEvent) {
  switch (event.key) {
    case "ArrowRight":
    case "d":
    case "D":
      if (mode.value === "flip") nextPage();
      else scrollByPage(1);
      break;
    case "ArrowLeft":
    case "a":
    case "A":
      if (mode.value === "flip") prevPage();
      else scrollByPage(-1);
      break;
    case "ArrowDown":
    case " ":
      scrollByPage(1);
      break;
    case "ArrowUp":
      scrollByPage(-1);
      break;
    case "Escape":
      goBack();
      break;
    case "f":
    case "F":
      toggleFullscreen();
      break;
    case "m":
    case "M":
      toggleMode();
      break;
  }
}

function scrollByPage(direction: 1 | -1) {
  scrollContainer.value?.scrollBy({
    top: direction * scrollContainer.value.clientHeight * 0.9,
    behavior: "smooth",
  });
}

/* ---------------- 滚动模式：当前页跟踪 ---------------- */

function setupObserver() {
  observer?.disconnect();
  observer = null;
  if (mode.value !== "scroll") return;
  const container = scrollContainer.value;
  if (!container) return;
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          const idx = Number(
            (entry.target as HTMLElement).dataset.index ?? "-1",
          );
          if (idx >= 0 && idx !== currentPage.value) {
            currentPage.value = idx;
          }
        }
      }
    },
    { root: container, threshold: [0.5] },
  );
  container
    .querySelectorAll<HTMLElement>("[data-index]")
    .forEach((el) => observer?.observe(el));
}

function scrollToCurrentPage() {
  if (mode.value !== "scroll") return;
  const container = scrollContainer.value;
  if (!container) return;
  const el = container.querySelector<HTMLElement>(
    `[data-index="${currentPage.value}"]`,
  );
  el?.scrollIntoView({ behavior: "instant" as ScrollBehavior, block: "start" });
}

/* ---------------- 预加载相邻页 ---------------- */

watch([currentPage, pages], () => {
  if (mode.value !== "flip" || pages.value.length === 0) return;
  const candidates = [
    currentPage.value + 1,
    currentPage.value + 2,
    currentPage.value - 1,
  ];
  for (const idx of candidates) {
    const page = pages.value[idx];
    if (page) {
      const img = new Image();
      img.src = page.url;
    }
  }
});

function saveProgress() {
  if (isLocal.value) {
    return saveLocalProgress(
      props.bookId,
      epsIndex.value,
      currentPage.value,
      book.value?.title,
    );
  }
  return saveReadingProgress(
    props.bookId,
    epsIndex.value,
    currentPage.value,
    book.value?.title,
  );
}

/* ---------------- 阅读进度保存（防抖） ---------------- */

watch([epsIndex, currentPage], () => {
  if (totalPages.value === 0) return;
  clearTimeout(progressTimer);
  progressTimer = setTimeout(() => {
    saveProgress().catch(() => {});
  }, 800);
});

function flushProgress() {
  clearTimeout(progressTimer);
  if (totalPages.value > 0) {
    saveProgress().catch(() => {});
  }
}

watch(mode, () => {
  if (mode.value === "scroll") {
    nextTick().then(() => {
      setupObserver();
      scrollToCurrentPage();
    });
  }
});

watch(pages, () => {
  if (mode.value === "scroll") {
    nextTick().then(() => {
      setupObserver();
      scrollToCurrentPage();
    });
  }
});

onMounted(async () => {
  showToolbar();
  window.addEventListener("keydown", onKeyDown);
  try {
    book.value = isLocal.value
      ? await getLocalBook(props.bookId)
      : await getBookDetail(props.bookId);

    let index =
      props.epsIndex !== undefined ? Number.parseInt(props.epsIndex, 10) : NaN;
    let progress: ReadingProgress | null = null;
    if (Number.isNaN(index)) {
      const res = isLocal.value
        ? await getLocalProgress(props.bookId)
        : await getReadingProgress(props.bookId);
      progress = res.progress;
      index = progress?.epsIndex ?? 0;
    }
    const epsCount = book.value.eps.length;
    index = Math.min(Math.max(index, 0), epsCount - 1);
    epsIndex.value = index;
    await loadPages(
      index,
      progress?.epsIndex === index ? progress.pageIndex : 0,
    );
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeyDown);
  clearTimeout(toolbarTimer);
  flushProgress();
  observer?.disconnect();
});
</script>

<template>
  <div
    class="fixed inset-0 flex select-none flex-col bg-surface-dark text-canvas"
    @mousemove="showToolbar"
  >
    <!-- 顶栏 -->
    <header
      v-show="toolbarVisible"
      class="absolute inset-x-0 top-0 z-20 flex items-center gap-3 border-b border-white/10 bg-surface-dark/80 px-4 py-2.5 backdrop-blur transition-opacity"
    >
      <button class="rounded-lg p-1.5 hover:bg-white/10" @click="goBack">
        ← 返回
      </button>
      <h1 class="line-clamp-1 text-sm font-bold">
        {{ book?.title || "阅读器" }}
        <span class="ml-2 text-xs font-normal text-gray-400">
          第 {{ epsIndex + 1 }} 话
        </span>
      </h1>
      <div class="ml-auto flex items-center gap-2 text-sm">
        <span v-if="totalPages" class="tabular-nums text-gray-300">
          {{ currentPage + 1 }} / {{ totalPages }}
        </span>
        <select
          v-if="book && book.eps.length > 1"
          class="rounded-lg bg-white/10 px-2 py-1 text-xs outline-none"
          :value="epsIndex"
          @change="
            switchEps(Number(($event.target as HTMLSelectElement).value))
          "
        >
          <option
            v-for="eps in book.eps"
            :key="eps.index"
            :value="eps.index"
            class="bg-surface-dark-elevated"
          >
            第 {{ eps.index + 1 }} 话{{ eps.name ? ` · ${eps.name}` : "" }}
          </option>
        </select>
        <button
          class="rounded-lg bg-white/10 px-2.5 py-1 text-xs hover:bg-white/20"
          @click="toggleMode"
        >
          {{ mode === "flip" ? "📜 滚动" : "📖 翻页" }}
        </button>
        <button
          class="rounded-lg bg-white/10 px-2.5 py-1 text-xs hover:bg-white/20"
          @click="toggleFullscreen"
        >
          ⛶ 全屏
        </button>
      </div>
    </header>

    <!-- 加载 / 错误 -->
    <div
      v-if="loading || pagesLoading"
      class="flex flex-1 items-center justify-center text-gray-400"
    >
      {{ loading ? "加载书籍信息..." : "加载章节图片..." }}
    </div>
    <div
      v-else-if="error"
      class="flex flex-1 flex-col items-center justify-center gap-3 text-red-400"
    >
      <p>{{ error }}</p>
      <p class="text-sm text-gray-500">
        JM 服务器不太稳定，若重试三次仍失败，可能是对方服务器问题。
      </p>
      <button
        class="rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
        @click="loadPages(epsIndex, currentPage)"
      >
        重试
      </button>
    </div>

    <!-- 翻页模式 -->
    <div
      v-else-if="mode === 'flip'"
      class="relative flex-1 cursor-pointer overflow-hidden"
      @click="onFlipClick"
      @wheel.prevent="onWheel"
    >
      <img
        v-if="current"
        :key="pageKey(current)"
        :src="current.url"
        :alt="`第 ${currentPage + 1} 页`"
        class="absolute inset-0 m-auto max-h-full max-w-full object-contain"
        draggable="false"
        @error="onImgError(current.index)"
      />
      <!-- 单页加载失败重试 -->
      <div
        v-if="current && failedPages.has(current.index)"
        class="absolute inset-0 flex flex-col items-center justify-center gap-3"
        @click.stop
      >
        <p class="text-gray-400">第 {{ currentPage + 1 }} 页加载失败</p>
        <button
          class="rounded-lg bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
          @click="retryPage(current.index)"
        >
          重试
        </button>
      </div>
      <!-- 末页：章节导航 -->
      <div
        v-if="isLastPage"
        class="absolute inset-x-0 bottom-16 flex justify-center gap-3"
        @click.stop
      >
        <button
          v-if="canPrevEps"
          class="rounded-lg bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
          @click="switchEps(epsIndex - 1)"
        >
          ← 上一话
        </button>
        <button
          v-if="canNextEps"
          class="rounded-lg bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
          @click="switchEps(epsIndex + 1)"
        >
          下一话 →
        </button>
      </div>
    </div>

    <!-- 滚动模式 -->
    <div
      v-else
      ref="scrollContainer"
      class="flex-1 overflow-y-auto"
      @scroll.passive="showToolbar"
    >
      <div class="mx-auto flex max-w-4xl flex-col items-center gap-1 py-2">
        <div
          v-for="page in pages"
          :key="pageKey(page)"
          :data-index="page.index"
          class="relative w-full"
        >
          <img
            :src="page.url"
            :alt="`第 ${page.index + 1} 页`"
            class="w-full object-contain"
            loading="lazy"
            draggable="false"
            @error="onImgError(page.index)"
          />
          <button
            v-if="failedPages.has(page.index)"
            class="absolute inset-0 flex items-center justify-center bg-black/60 text-sm text-gray-300 hover:text-white"
            @click="retryPage(page.index)"
          >
            第 {{ page.index + 1 }} 页加载失败，点击重试
          </button>
        </div>
      </div>
    </div>

    <!-- 底部进度条 -->
    <footer
      v-if="totalPages && !loading && !error"
      v-show="toolbarVisible || mode === 'flip'"
      class="absolute inset-x-0 bottom-0 z-20 border-t border-white/10 bg-surface-dark/80 px-4 py-2 backdrop-blur"
    >
      <input
        v-model.number="currentPage"
        type="range"
        :min="0"
        :max="totalPages - 1"
        class="w-full accent-brand-ochre"
      />
    </footer>
  </div>
</template>
