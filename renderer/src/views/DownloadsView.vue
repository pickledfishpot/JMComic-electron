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
import PageHeader from "../components/PageHeader.vue";
import StateBlock from "../components/StateBlock.vue";

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
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="下载管理">
      <button
        class="rounded-md border border-hairline bg-canvas px-3 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
        @click="load()"
      >
        刷新
      </button>
    </PageHeader>

    <main class="mx-auto max-w-3xl p-6">
      <StateBlock v-if="loading" type="loading" />
      <StateBlock v-else-if="error" type="error" :message="error" @retry="load()" />
      <StateBlock
        v-else-if="!tasks.length"
        type="empty"
        message="暂无下载任务，可在书籍详情页点击「下载本书」"
      />

      <div v-else class="space-y-3">
        <div v-for="task in tasks" :key="task.id" class="card p-4">
          <div class="flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium">
                {{ task.bookTitle || `本子 ${task.bookId}` }}
                <span class="ml-2 text-xs text-muted-soft">
                  第 {{ task.epsIndex + 1 }} 话{{
                    task.epsName ? ` · ${task.epsName}` : ""
                  }}
                </span>
              </p>
              <p
                class="mt-0.5 text-xs"
                :class="task.status === 'error' ? 'text-error' : 'text-muted'"
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
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium transition hover:bg-surface-soft"
                @click="act(task, 'pause')"
              >
                暂停
              </button>
              <button
                v-if="task.status === 'paused'"
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium transition hover:bg-surface-soft"
                @click="act(task, 'resume')"
              >
                继续
              </button>
              <button
                v-if="task.status === 'error'"
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium transition hover:bg-surface-soft"
                @click="act(task, 'retry')"
              >
                重试
              </button>
              <button class="btn-danger" @click="remove(task)">删除</button>
            </div>
          </div>
          <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-strong">
            <div
              class="h-full rounded-full transition-all"
              :class="task.status === 'error' ? 'bg-error' : 'bg-brand-ochre'"
              :style="{ width: `${progressOf(task)}%` }"
            ></div>
          </div>
          <p v-if="task.error" class="mt-2 text-xs text-error/80">
            {{ task.error }}
          </p>
        </div>
      </div>
    </main>
  </div>
</template>
