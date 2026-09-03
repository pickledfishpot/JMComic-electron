<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  listDownloads,
  pauseDownload,
  removeDownload,
  resumeDownload,
  retryDownload,
  type DownloadTask,
} from "../api/downloads";
import { useGoBack } from "../composables/useGoBack";

const goBack = useGoBack();
const tasks = ref<DownloadTask[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const STATUS_TEXT: Record<DownloadTask["status"], string> = {
  pending: "排队中",
  downloading: "下载中",
  paused: "已暂停",
  done: "已完成",
  error: "失败",
};

let timer: ReturnType<typeof setInterval> | undefined;

const activeCount = computed(
  () =>
    tasks.value.filter(
      (t) => t.status === "pending" || t.status === "downloading",
    ).length,
);

async function load(silent = false) {
  if (!silent) {
    loading.value = true;
  }
  error.value = null;
  try {
    tasks.value = (await listDownloads()).tasks;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function act(task: DownloadTask, action: "pause" | "resume" | "retry") {
  try {
    if (action === "pause") await pauseDownload(task.id);
    else if (action === "resume") await resumeDownload(task.id);
    else await retryDownload(task.id);
    await load(true);
  } catch (err) {
    error.value = String(err);
  }
}

async function remove(task: DownloadTask) {
  try {
    await removeDownload(task.id);
    await load(true);
  } catch (err) {
    error.value = String(err);
  }
}

function progressOf(task: DownloadTask): number {
  return task.totalPages > 0
    ? Math.round((task.donePages / task.totalPages) * 100)
    : 0;
}

onMounted(() => {
  load();
  timer = setInterval(() => {
    if (activeCount.value > 0) load(true);
  }, 2000);
});

onBeforeUnmount(() => {
  clearInterval(timer);
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
      <h1 class="text-base font-bold">下载管理</h1>
      <button
        class="ml-auto rounded-lg bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20"
        @click="load()"
      >
        刷新
      </button>
    </header>

    <main class="mx-auto max-w-3xl p-6">
      <div v-if="loading" class="py-20 text-center text-gray-400">
        加载中...
      </div>
      <div v-else-if="error" class="py-20 text-center text-red-400">
        <p>{{ error }}</p>
        <button
          class="mt-4 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-300 hover:bg-red-500/30"
          @click="load()"
        >
          重试
        </button>
      </div>
      <p v-else-if="!tasks.length" class="py-20 text-center text-gray-500">
        暂无下载任务，可在书籍详情页点击「下载本书」
      </p>

      <div v-else class="space-y-3">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="rounded-xl bg-[#1a1a1a] p-4"
        >
          <div class="flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium">
                {{ task.bookTitle || `本子 ${task.bookId}` }}
                <span class="ml-2 text-xs text-gray-500">
                  第 {{ task.epsIndex + 1 }} 话{{
                    task.epsName ? ` · ${task.epsName}` : ""
                  }}
                </span>
              </p>
              <p
                class="mt-0.5 text-xs"
                :class="
                  task.status === 'error' ? 'text-red-400' : 'text-gray-500'
                "
              >
                {{ STATUS_TEXT[task.status] }}
                <span v-if="task.totalPages">
                  · {{ task.donePages }}/{{ task.totalPages }} 页
                </span>
              </p>
            </div>
            <div class="flex shrink-0 gap-2">
              <button
                v-if="
                  task.status === 'downloading' || task.status === 'pending'
                "
                class="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
                @click="act(task, 'pause')"
              >
                暂停
              </button>
              <button
                v-if="task.status === 'paused'"
                class="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
                @click="act(task, 'resume')"
              >
                继续
              </button>
              <button
                v-if="task.status === 'error'"
                class="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
                @click="act(task, 'retry')"
              >
                重试
              </button>
              <button
                class="rounded-lg bg-red-500/10 px-3 py-1 text-xs text-red-300 hover:bg-red-500/20"
                @click="remove(task)"
              >
                删除
              </button>
            </div>
          </div>
          <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              class="h-full rounded-full transition-all"
              :class="task.status === 'error' ? 'bg-red-400' : 'bg-[#feca57]'"
              :style="{ width: `${progressOf(task)}%` }"
            ></div>
          </div>
          <p v-if="task.error" class="mt-2 text-xs text-red-400/80">
            {{ task.error }}
          </p>
        </div>
      </div>
    </main>
  </div>
</template>
