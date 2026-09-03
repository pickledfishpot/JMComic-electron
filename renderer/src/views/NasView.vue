<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  addNas,
  deleteNas,
  listNas,
  testNas,
  updateNas,
  uploadToNas,
  type NasConfig,
  type NasConfigInput,
} from "../api/nas";
import { listDownloads, type DownloadTask } from "../api/downloads";

const router = useRouter();
const loading = ref(false);
const error = ref<string | null>(null);
const configs = ref<NasConfig[]>([]);
const message = ref<string | null>(null);

const editing = ref<Partial<NasConfigInput> | null>(null);
const editingId = ref<string | null>(null);
const testing = ref<string | null>(null);
const uploading = ref<string | null>(null);
const showUploadFor = ref<string | null>(null);
const downloads = ref<DownloadTask[]>([]);

function startAdd() {
  editingId.value = null;
  editing.value = {
    name: "",
    protocol: "webdav",
    address: "",
    port: 0,
    username: "",
    password: "",
    remote_path: "",
  };
}

function startEdit(config: NasConfig) {
  editingId.value = config.id;
  editing.value = {
    name: config.name,
    protocol: config.protocol,
    address: config.address,
    port: config.port,
    username: config.username,
    password: config.password,
    remote_path: config.remotePath,
  };
}

async function save() {
  if (!editing.value) return;
  message.value = null;
  error.value = null;
  try {
    if (editingId.value) {
      await updateNas(editingId.value, editing.value);
    } else {
      await addNas(editing.value as NasConfigInput);
    }
    editing.value = null;
    await load();
  } catch (err) {
    error.value = String(err);
  }
}

async function remove(config: NasConfig) {
  if (!window.confirm(`删除 NAS 配置「${config.name}」？`)) return;
  await deleteNas(config.id).catch(() => {});
  await load();
}

async function test(config: NasConfig) {
  testing.value = config.id;
  message.value = null;
  try {
    const res = await testNas(config.id);
    message.value = res.ok
      ? `「${config.name}」连接成功`
      : `「${config.name}」连接失败：${res.error || "未知错误"}`;
  } finally {
    testing.value = null;
  }
}

async function openUpload(config: NasConfig) {
  showUploadFor.value = showUploadFor.value === config.id ? null : config.id;
  if (showUploadFor.value) {
    downloads.value = (await listDownloads()).tasks.filter(
      (t) => t.status === "done",
    );
  }
}

async function upload(config: NasConfig, task: DownloadTask) {
  uploading.value = task.id;
  message.value = null;
  error.value = null;
  try {
    const res = await uploadToNas(config.id, task.bookId, task.bookTitle);
    message.value = `已上传 ${res.files} 个文件到「${config.name}」`;
  } catch (err) {
    error.value = String(err);
  } finally {
    uploading.value = null;
  }
}

async function load() {
  loading.value = true;
  try {
    configs.value = (await listNas()).configs;
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
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
      <h1 class="text-base font-bold">NAS 上传</h1>
      <button
        class="ml-auto rounded-lg bg-[#feca57] px-3 py-1.5 text-sm font-medium text-black hover:opacity-90"
        @click="startAdd"
      >
        + 添加配置
      </button>
    </header>

    <main class="mx-auto max-w-2xl p-6">
      <div
        v-if="message"
        class="mb-4 rounded-lg bg-green-500/10 p-3 text-sm text-green-400"
      >
        {{ message }}
      </div>
      <div
        v-if="error"
        class="mb-4 rounded-lg bg-red-500/10 p-3 text-sm text-red-400"
      >
        {{ error }}
      </div>

      <!-- 编辑表单 -->
      <form
        v-if="editing"
        class="mb-6 space-y-3 rounded-xl bg-[#1a1a1a] p-4"
        @submit.prevent="save"
      >
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm">
            名称
            <input
              v-model="editing.name"
              required
              class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
            />
          </label>
          <label class="block text-sm">
            协议
            <select
              v-model="editing.protocol"
              class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none"
            >
              <option value="webdav" class="bg-[#1a1a1a]">WebDAV</option>
              <option value="smb" class="bg-[#1a1a1a]">SMB</option>
              <option value="local" class="bg-[#1a1a1a]">本地目录</option>
            </select>
          </label>
        </div>
        <label v-if="editing.protocol !== 'local'" class="block text-sm">
          地址
          <input
            v-model="editing.address"
            :placeholder="
              editing.protocol === 'webdav'
                ? 'https://dav.example.com'
                : '\\\\nas\\share'
            "
            class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
          />
        </label>
        <div class="grid grid-cols-3 gap-3">
          <label v-if="editing.protocol !== 'local'" class="block text-sm">
            端口
            <input
              v-model.number="editing.port"
              type="number"
              min="0"
              max="65535"
              class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none"
            />
          </label>
          <label v-if="editing.protocol !== 'local'" class="block text-sm">
            用户名
            <input
              v-model="editing.username"
              class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none"
            />
          </label>
          <label v-if="editing.protocol !== 'local'" class="block text-sm">
            密码
            <input
              v-model="editing.password"
              type="password"
              placeholder="不变可留空"
              class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none"
            />
          </label>
        </div>
        <label class="block text-sm">
          远程目录
          <input
            v-model="editing.remote_path"
            :placeholder="
              editing.protocol === 'local' ? '/path/to/backup' : '/comics'
            "
            class="mt-1 w-full rounded-lg bg-[#0f0f0f] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
          />
        </label>
        <div class="flex gap-2 pt-1">
          <button
            type="submit"
            class="rounded-lg bg-[#feca57] px-4 py-2 text-sm font-medium text-black hover:opacity-90"
          >
            保存
          </button>
          <button
            type="button"
            class="rounded-lg bg-white/10 px-4 py-2 text-sm hover:bg-white/20"
            @click="editing = null"
          >
            取消
          </button>
        </div>
      </form>

      <div v-if="loading" class="py-20 text-center text-gray-400">
        加载中...
      </div>
      <p v-else-if="!configs.length" class="py-20 text-center text-gray-500">
        还没有 NAS 配置
      </p>

      <div v-else class="space-y-3">
        <div
          v-for="config in configs"
          :key="config.id"
          class="rounded-xl bg-[#1a1a1a] p-4"
        >
          <div class="flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium">
                {{ config.name }}
                <span class="ml-2 text-xs text-gray-500">{{
                  config.protocol
                }}</span>
              </p>
              <p class="mt-0.5 truncate text-xs text-gray-500">
                {{
                  config.protocol === "local"
                    ? config.remotePath
                    : config.address
                }}
              </p>
            </div>
            <div class="flex shrink-0 gap-2">
              <button
                class="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
                :disabled="testing === config.id"
                @click="test(config)"
              >
                {{ testing === config.id ? "测试中..." : "测试" }}
              </button>
              <button
                class="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
                @click="openUpload(config)"
              >
                上传
              </button>
              <button
                class="rounded-lg bg-white/10 px-3 py-1 text-xs hover:bg-white/20"
                @click="startEdit(config)"
              >
                编辑
              </button>
              <button
                class="rounded-lg bg-red-500/10 px-3 py-1 text-xs text-red-300 hover:bg-red-500/20"
                @click="remove(config)"
              >
                删除
              </button>
            </div>
          </div>

          <!-- 选择已下载书籍上传 -->
          <div
            v-if="showUploadFor === config.id"
            class="mt-3 border-t border-white/10 pt-3"
          >
            <p class="mb-2 text-xs text-gray-500">选择要上传的已下载书籍：</p>
            <p v-if="!downloads.length" class="text-sm text-gray-500">
              暂无已完成的下载任务
            </p>
            <div v-else class="space-y-1">
              <button
                v-for="task in downloads"
                :key="task.id"
                class="flex w-full items-center justify-between rounded-lg bg-[#0f0f0f] px-3 py-2 text-left text-sm hover:bg-[#252525]"
                :disabled="uploading === task.id"
                @click="upload(config, task)"
              >
                <span class="truncate">
                  {{ task.bookTitle || task.bookId }}
                </span>
                <span class="ml-2 shrink-0 text-xs text-gray-500">
                  {{ uploading === task.id ? "上传中..." : "点击上传" }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
