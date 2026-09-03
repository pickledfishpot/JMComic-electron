<script setup lang="ts">
import { onMounted, ref } from "vue";
import { apiFetch } from "../api/client";
import PageHeader from "../components/PageHeader.vue";

interface Settings {
  theme: string;
  language: string;
  proxy: {
    enabled: boolean;
    http: string;
    https: string;
    socks5: string;
  };
  local: { dirs: string[] };
}

const loading = ref(false);
const saving = ref(false);
const message = ref<string | null>(null);
const error = ref<string | null>(null);

const settings = ref<Settings | null>(null);
const newDir = ref("");

async function load() {
  loading.value = true;
  try {
    settings.value = await apiFetch<Settings>("/settings");
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!settings.value) return;
  saving.value = true;
  message.value = null;
  error.value = null;
  try {
    await apiFetch("/settings", {
      method: "PUT",
      body: JSON.stringify(settings.value),
    });
    message.value = "已保存";
  } catch (err) {
    error.value = String(err);
  } finally {
    saving.value = false;
  }
}

function addDir() {
  const dir = newDir.value.trim();
  if (!dir || !settings.value) return;
  if (!settings.value.local.dirs.includes(dir)) {
    settings.value.local.dirs.push(dir);
  }
  newDir.value = "";
}

function removeDir(index: number) {
  settings.value?.local.dirs.splice(index, 1);
}

onMounted(load);
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="设置" />

    <main class="mx-auto max-w-xl space-y-6 p-6">
      <div v-if="loading" class="py-20 text-center text-muted">加载中...</div>
      <template v-else-if="settings">
        <div v-if="message" class="banner-success">{{ message }}</div>
        <div v-if="error" class="banner-error">{{ error }}</div>

        <!-- 代理 -->
        <section class="card p-4">
          <h2 class="mb-3 font-medium">网络代理</h2>
          <label class="flex items-center gap-2 text-sm">
            <input
              v-model="settings.proxy.enabled"
              type="checkbox"
              class="accent-ink"
            />
            启用代理
          </label>
          <div v-if="settings.proxy.enabled" class="mt-3 space-y-3">
            <label class="block text-sm">
              HTTP 代理
              <input
                v-model="settings.proxy.http"
                placeholder="http://127.0.0.1:7890"
                class="input mt-1"
              />
            </label>
            <label class="block text-sm">
              HTTPS 代理
              <input
                v-model="settings.proxy.https"
                placeholder="https://127.0.0.1:7890"
                class="input mt-1"
              />
            </label>
            <label class="block text-sm">
              SOCKS5 代理
              <input
                v-model="settings.proxy.socks5"
                placeholder="socks5://127.0.0.1:7890"
                class="input mt-1"
              />
            </label>
            <p class="text-xs text-muted">
              按 HTTP → HTTPS → SOCKS5 顺序取第一个非空值生效。
            </p>
          </div>
        </section>

        <!-- 本地图库目录 -->
        <section class="card p-4">
          <h2 class="mb-3 font-medium">本地图库扫描目录</h2>
          <p class="mb-3 text-xs text-muted">
            下载目录始终包含在内，此处添加额外的漫画存放目录。
          </p>
          <div
            v-for="(dir, index) in settings.local.dirs"
            :key="dir"
            class="mb-2 flex items-center gap-2"
          >
            <span
              class="min-w-0 flex-1 truncate rounded-md bg-surface-soft px-3 py-2 text-sm"
            >
              {{ dir }}
            </span>
            <button class="btn-danger" @click="removeDir(index)">删除</button>
          </div>
          <div class="flex gap-2">
            <input
              v-model="newDir"
              placeholder="/path/to/comics"
              class="input min-w-0 flex-1"
              @keyup.enter="addDir"
            />
            <button
              class="rounded-md border border-hairline bg-canvas px-3 text-sm font-medium transition hover:bg-surface-soft"
              @click="addDir"
            >
              添加
            </button>
          </div>
        </section>

        <button class="btn-primary w-full" :disabled="saving" @click="save">
          {{ saving ? "保存中..." : "保存设置" }}
        </button>
      </template>
    </main>
  </div>
</template>
