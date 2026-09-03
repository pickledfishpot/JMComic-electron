<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getWaifu2xStatus, resolveDns, testProxy } from "../api/tools";

const router = useRouter();

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

function goBack() {
  router.push("/");
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
  <div class="min-h-screen bg-[#0f0f0f] text-[#f0f0f0]">
    <header
      class="sticky top-0 z-10 flex items-center gap-3 border-b border-white/10 bg-[#0f0f0f]/90 px-4 py-3 backdrop-blur"
    >
      <button class="rounded-lg p-2 hover:bg-white/10" @click="goBack">
        ← 返回
      </button>
      <h1 class="text-base font-bold">网络工具</h1>
    </header>

    <main class="mx-auto max-w-xl space-y-6 p-6">
      <!-- DNS 解析 -->
      <section class="rounded-xl bg-[#1a1a1a] p-4">
        <h2 class="mb-3 font-medium">DNS 解析</h2>
        <div class="flex gap-2">
          <input
            v-model="dnsHost"
            placeholder="example.com"
            class="min-w-0 flex-1 rounded-lg bg-[#0f0f0f] px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[#feca57]"
            @keyup.enter="runDns"
          />
          <button
            class="rounded-lg bg-[#feca57] px-4 py-2 text-sm font-medium text-black hover:opacity-90 disabled:opacity-50"
            :disabled="dnsLoading || !dnsHost.trim()"
            @click="runDns"
          >
            {{ dnsLoading ? "解析中..." : "解析" }}
          </button>
        </div>
        <p
          v-if="dnsResult"
          class="mt-3 rounded-lg p-3 text-sm"
          :class="
            dnsResult.ok
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          "
        >
          {{ dnsResult.text }}
        </p>
      </section>

      <!-- 代理测试 -->
      <section class="rounded-xl bg-[#1a1a1a] p-4">
        <h2 class="mb-1 font-medium">代理连通性测试</h2>
        <p class="mb-3 text-xs text-gray-500">
          使用设置中配置的代理访问测试地址，可在设置页开启并填写代理。
        </p>
        <button
          class="rounded-lg bg-[#feca57] px-4 py-2 text-sm font-medium text-black hover:opacity-90 disabled:opacity-50"
          :disabled="proxyLoading"
          @click="runProxyTest"
        >
          {{ proxyLoading ? "测试中..." : "开始测试" }}
        </button>
        <p
          v-if="proxyResult"
          class="mt-3 rounded-lg p-3 text-sm"
          :class="
            proxyResult.ok
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          "
        >
          {{ proxyResult.text }}
        </p>
      </section>

      <!-- Waifu2x 状态 -->
      <section class="rounded-xl bg-[#1a1a1a] p-4">
        <h2 class="mb-1 font-medium">Waifu2x 超分</h2>
        <p
          class="mt-2 rounded-lg p-3 text-sm"
          :class="
            waifu2xAvailable
              ? 'bg-green-500/10 text-green-400'
              : 'bg-white/5 text-gray-400'
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
