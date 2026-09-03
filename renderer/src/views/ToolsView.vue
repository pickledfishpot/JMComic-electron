<script setup lang="ts">
import { onMounted, ref } from "vue";
import { getWaifu2xStatus, resolveDns, testProxy } from "../api/tools";
import PageHeader from "../components/PageHeader.vue";

const waifu2xAvailable = ref<boolean | null>(null);
const dnsHost = ref("");
const dnsResult = ref<{ ok: boolean; text: string } | null>(null);
const dnsLoading = ref(false);
const proxyResult = ref<{ ok: boolean; text: string } | null>(null);
const proxyLoading = ref(false);

async function runDns() {
  const host = dnsHost.value.trim();
  if (!host) return;
  dnsLoading.value = true;
  dnsResult.value = null;
  try {
    const res = await resolveDns(host);
    dnsResult.value = {
      ok: res.ok,
      text: res.ok ? res.ips.join("、") : res.error || "解析失败",
    };
  } catch (err) {
    dnsResult.value = { ok: false, text: String(err) };
  } finally {
    dnsLoading.value = false;
  }
}

async function runProxyTest() {
  proxyLoading.value = true;
  proxyResult.value = null;
  try {
    const res = await testProxy();
    proxyResult.value = {
      ok: res.ok,
      text: res.ok
        ? `连接成功，HTTP ${res.status}，耗时 ${res.elapsed}s`
        : res.error || "连接失败",
    };
  } catch (err) {
    proxyResult.value = { ok: false, text: String(err) };
  } finally {
    proxyLoading.value = false;
  }
}

onMounted(async () => {
  try {
    waifu2xAvailable.value = (await getWaifu2xStatus()).available;
  } catch {
    waifu2xAvailable.value = false;
  }
});
</script>

<template>
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="网络工具" />

    <main class="mx-auto max-w-xl space-y-6 p-6">
      <!-- DNS 解析 -->
      <section class="card p-4">
        <h2 class="mb-3 font-medium">DNS 解析</h2>
        <div class="flex gap-2">
          <input
            v-model="dnsHost"
            placeholder="example.com"
            class="input min-w-0 flex-1"
            @keyup.enter="runDns"
          />
          <button
            class="rounded-md bg-ink px-4 text-sm font-semibold text-white transition hover:bg-ink-active disabled:opacity-50"
            :disabled="dnsLoading || !dnsHost.trim()"
            @click="runDns"
          >
            {{ dnsLoading ? "解析中..." : "解析" }}
          </button>
        </div>
        <p
          v-if="dnsResult"
          class="mt-3 rounded-md p-3 text-sm"
          :class="dnsResult.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error'"
        >
          {{ dnsResult.text }}
        </p>
      </section>

      <!-- 代理测试 -->
      <section class="card p-4">
        <h2 class="mb-1 font-medium">代理连通性测试</h2>
        <p class="mb-3 text-xs text-muted">
          使用设置中配置的代理访问测试地址，可在设置页开启并填写代理。
        </p>
        <button
          class="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-ink-active disabled:opacity-50"
          :disabled="proxyLoading"
          @click="runProxyTest"
        >
          {{ proxyLoading ? "测试中..." : "开始测试" }}
        </button>
        <p
          v-if="proxyResult"
          class="mt-3 rounded-md p-3 text-sm"
          :class="proxyResult.ok ? 'bg-success/10 text-success' : 'bg-error/10 text-error'"
        >
          {{ proxyResult.text }}
        </p>
      </section>

      <!-- Waifu2x 状态 -->
      <section class="card p-4">
        <h2 class="mb-1 font-medium">Waifu2x 超分</h2>
        <p
          class="mt-2 rounded-md p-3 text-sm"
          :class="
            waifu2xAvailable
              ? 'bg-success/10 text-success'
              : 'bg-surface-soft text-muted'
          "
        >
          {{
            waifu2xAvailable === null
              ? "检测中..."
              : waifu2xAvailable
                ? "超分引擎可用"
                : "当前环境未安装 sr_vulkan 超分引擎，超分功能不可用（不影响其他功能）。"
          }}
        </p>
      </section>
    </main>
  </div>
</template>
