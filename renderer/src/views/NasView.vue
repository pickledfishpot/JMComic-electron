<script setup lang="ts">
import { onMounted, ref } from "vue";
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
import PageHeader from "../components/PageHeader.vue";
import StateBlock from "../components/StateBlock.vue";

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

onMounted(load);
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="NAS 上传">
      <button
        class="rounded-md bg-ink px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-ink-active"
        @click="startAdd"
      >
        + 添加配置
      </button>
    </PageHeader>

    <main class="mx-auto max-w-2xl p-6">
      <div v-if="message" class="banner-success mb-4">{{ message }}</div>
      <div v-if="error" class="banner-error mb-4">{{ error }}</div>

      <!-- 编辑表单 -->
      <form v-if="editing" class="card mb-6 space-y-3 p-4" @submit.prevent="save">
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm">
            名称
            <input v-model="editing.name" required class="input mt-1" />
          </label>
          <label class="block text-sm">
            协议
            <select v-model="editing.protocol" class="input mt-1">
              <option value="webdav">WebDAV</option>
              <option value="smb">SMB</option>
              <option value="local">本地目录</option>
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
            class="input mt-1"
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
              class="input mt-1"
            />
          </label>
          <label v-if="editing.protocol !== 'local'" class="block text-sm">
            用户名
            <input v-model="editing.username" class="input mt-1" />
          </label>
          <label v-if="editing.protocol !== 'local'" class="block text-sm">
            密码
            <input
              v-model="editing.password"
              type="password"
              placeholder="不变可留空"
              class="input mt-1"
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
            class="input mt-1"
          />
        </label>
        <div class="flex gap-2 pt-1">
          <button
            type="submit"
            class="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-ink-active"
          >
            保存
          </button>
          <button
            type="button"
            class="rounded-md border border-hairline bg-canvas px-4 py-2 text-sm font-medium transition hover:bg-surface-soft"
            @click="editing = null"
          >
            取消
          </button>
        </div>
      </form>

      <StateBlock v-if="loading" type="loading" />
      <StateBlock
        v-else-if="!configs.length"
        type="empty"
        message="还没有 NAS 配置"
      />

      <div v-else class="space-y-3">
        <div v-for="config in configs" :key="config.id" class="card p-4">
          <div class="flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium">
                {{ config.name }}
                <span class="ml-2 text-xs text-muted-soft">{{
                  config.protocol
                }}</span>
              </p>
              <p class="mt-0.5 truncate text-xs text-muted">
                {{
                  config.protocol === "local"
                    ? config.remotePath
                    : config.address
                }}
              </p>
            </div>
            <div class="flex shrink-0 gap-2">
              <button
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium transition hover:bg-surface-soft"
                :disabled="testing === config.id"
                @click="test(config)"
              >
                {{ testing === config.id ? "测试中..." : "测试" }}
              </button>
              <button
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium transition hover:bg-surface-soft"
                @click="openUpload(config)"
              >
                上传
              </button>
              <button
                class="rounded-md border border-hairline bg-canvas px-3 py-1 text-xs font-medium transition hover:bg-surface-soft"
                @click="startEdit(config)"
              >
                编辑
              </button>
              <button class="btn-danger" @click="remove(config)">删除</button>
            </div>
          </div>

          <!-- 选择已下载书籍上传 -->
          <div
            v-if="showUploadFor === config.id"
            class="mt-3 border-t border-hairline pt-3"
          >
            <p class="mb-2 text-xs text-muted">选择要上传的已下载书籍：</p>
            <p v-if="!downloads.length" class="text-sm text-muted">
              暂无已完成的下载任务
            </p>
            <div v-else class="space-y-1">
              <button
                v-for="task in downloads"
                :key="task.id"
                class="flex w-full items-center justify-between rounded-md bg-surface-soft px-3 py-2 text-left text-sm transition hover:bg-surface-strong"
                :disabled="uploading === task.id"
                @click="upload(config, task)"
              >
                <span class="truncate">
                  {{ task.bookTitle || task.bookId }}
                </span>
                <span class="ml-2 shrink-0 text-xs text-muted">
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
