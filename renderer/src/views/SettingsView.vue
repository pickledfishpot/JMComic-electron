<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { apiFetch } from "../api/client";

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

const router = useRouter();
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
      <h1 class="text-base font-bold">设置</h1>
    </header>

    <main class="mx-auto max-w-xl space-y-6 p-6">
      <div v-if="loading" class="py-20 text-center text-gray-400">
        加载中...
      </div>
      <template v-else-if="settings">
        <div
          v-if="message"
          class="rounded-lg bg-green-500/10 p-3 text-sm text-green-400"
        >
          {{ message }}
        </div>
        <div
          v-if="error"
          class="rounded-lg bg-red-500/10 p-3 text-sm text-red-400"
        >
          {{ error }}
        </div>

        <!-- 代理 -->
        <section class="rounded-xl bg-[#1a1a1a] p-4">
          <h2 class="mb-3 font-medium">网络代理</h2>
          <label class="flex items-center gap-2 text-sm">
            <input
              v-model="settings.proxy.enabled"
              type="checkbox"
              class="accent-[#feca57]"
            />
            启用代理
          </label>
          <div v-if="settings.proxy.enabled" class="mt-3 space-y-3">
            <label class="block text-sm">
              HTTP 代理
              <input
                v-model="settings.proxy.http"
                placeholder="http://127.0.0.1:7890"
                class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
              />
            </label>
            <label class="block text-sm">
              HTTPS 代理
              <input
                v-model="settings.proxy.https"
                placeholder="https://127.0.0.1:7890"
                class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
              />
            </label>
            <label class="block text-sm">
              SOCKS5 代理
              <input
                v-model="settings.proxy.socks5"
                placeholder="socks5://127.0.0.1:7890"
                class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
              />
            </label>
            <p class="text-xs text-gray-500">
              按 HTTP → HTTPS → SOCKS5 顺序取第一个非空值生效。
            </p>
          </div>
        </section>

        <!-- 本地图库目录 -->
        <section class="rounded-xl bg-[#1a1a1a] p-4">
          <h2 class="mb-3 font-medium">本地图库扫描目录</h2>
          <p class="mb-3 text-xs text-gray-500">
            下载目录始终包含在内，此处添加额外的漫画存放目录。
          </p>
          <div
            v-for="(dir, index) in settings.local.dirs"
            :key="dir"
            class="mb-2 flex items-center gap-2"
          >
            <span
              class="min-w-0 flex-1 truncate rounded-lg bg-[#0f0f0f] px-3 py-2 text-sm"
            >
              {{ dir }}
            </span>
            <button
              class="rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/20"
              @click="removeDir(index)"
            >
              删除
            </button>
          </div>
          <div class="flex gap-2">
            <input
              v-model="newDir"
              placeholder="/path/to/comics"
              class="min-w-0 flex-1 rounded-lg bg-[#0f0f0f] px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[#feca57]"
              @keyup.enter="addDir"
            />
            <button
              class="rounded-lg bg-white/10 px-3 py-2 text-sm hover:bg-white/20"
              @click="addDir"
            >
              添加
            </button>
          </div>
        </section>

        <button
          class="w-full rounded-lg bg-[#feca57] py-2.5 font-medium text-black hover:opacity-90 disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? "保存中..." : "保存设置" }}
        </button>
      </template>
    </main>
  </div>
</template>
