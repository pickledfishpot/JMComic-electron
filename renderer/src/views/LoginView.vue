<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useUserStore } from "../stores/user";
import { getCaptchaUrl, register } from "../api/account";
import { useGoBack } from "../composables/useGoBack";

const userStore = useUserStore();
const goBack = useGoBack();

const tab = ref<"login" | "register">("login");

const username = ref("");
const password = ref("");
const email = ref("");
const passwordConfirm = ref("");
const gender = ref("Male");
const verification = ref("");
const captchaUrl = ref(getCaptchaUrl());

const loading = ref(false);
const error = ref<string | null>(null);
const notice = ref<string | null>(null);

function refreshCaptcha() {
  verification.value = "";
  captchaUrl.value = getCaptchaUrl();
}

async function submitLogin() {
  loading.value = true;
  error.value = null;
  notice.value = null;
  try {
    await userStore.login(username.value, password.value);
    goBack();
  } catch (err) {
    error.value = String(err);
  } finally {
    loading.value = false;
  }
}

async function submitRegister() {
  loading.value = true;
  error.value = null;
  notice.value = null;
  try {
    const res = await register({
      username: username.value,
      email: email.value,
      password: password.value,
      passwordConfirm: passwordConfirm.value,
      gender: gender.value,
      verification: verification.value,
    });
    if (res.ok) {
      notice.value = res.message || "注册成功，请查收验证邮件后登录";
      tab.value = "login";
      refreshCaptcha();
    } else {
      error.value = res.message || "注册失败";
      refreshCaptcha();
    }
  } catch (err) {
    error.value = String(err);
    refreshCaptcha();
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  userStore.fetchMe();
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
      <h1 class="text-base font-bold">登录 / 注册</h1>
    </header>

    <main class="mx-auto max-w-md p-6">
      <div class="mb-6 flex rounded-lg bg-[#1a1a1a] p-1">
        <button
          class="flex-1 rounded-md py-2 text-sm"
          :class="
            tab === 'login'
              ? 'bg-[#feca57] font-medium text-black'
              : 'text-gray-400'
          "
          @click="tab = 'login'"
        >
          登录
        </button>
        <button
          class="flex-1 rounded-md py-2 text-sm"
          :class="
            tab === 'register'
              ? 'bg-[#feca57] font-medium text-black'
              : 'text-gray-400'
          "
          @click="tab = 'register'"
        >
          注册
        </button>
      </div>

      <div
        v-if="userStore.user"
        class="mb-6 rounded-xl bg-[#1a1a1a] p-4 text-sm"
      >
        <p>
          当前已登录：<b>{{ userStore.user.username }}</b>
          <span v-if="userStore.user.title" class="ml-2 text-xs text-[#feca57]">
            {{ userStore.user.title }}
          </span>
        </p>
        <button
          class="mt-3 rounded-lg bg-white/10 px-4 py-1.5 text-sm hover:bg-white/20"
          @click="userStore.logout()"
        >
          退出登录
        </button>
      </div>

      <form
        class="space-y-4"
        @submit.prevent="tab === 'login' ? submitLogin() : submitRegister()"
      >
        <label class="block text-sm">
          用户名
          <input
            v-model="username"
            required
            class="mt-1 w-full rounded-lg bg-[#1a1a1a] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
          />
        </label>

        <template v-if="tab === 'register'">
          <label class="block text-sm">
            邮箱
            <input
              v-model="email"
              type="email"
              required
              class="mt-1 w-full rounded-lg bg-[#1a1a1a] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
            />
          </label>
          <label class="block text-sm">
            确认密码
            <input
              v-model="passwordConfirm"
              type="password"
              required
              class="mt-1 w-full rounded-lg bg-[#1a1a1a] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
            />
          </label>
          <label class="block text-sm">
            性别
            <select
              v-model="gender"
              class="mt-1 w-full rounded-lg bg-[#1a1a1a] px-3 py-2 outline-none"
            >
              <option value="Male" class="bg-[#1a1a1a]">男</option>
              <option value="Female" class="bg-[#1a1a1a]">女</option>
            </select>
          </label>
          <label class="block text-sm">
            验证码
            <div class="mt-1 flex items-center gap-2">
              <input
                v-model="verification"
                required
                class="flex-1 rounded-lg bg-[#1a1a1a] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
              />
              <img
                :src="captchaUrl"
                alt="验证码"
                class="h-10 w-32 cursor-pointer rounded-lg bg-white object-cover"
                title="点击刷新"
                @click="refreshCaptcha"
              />
            </div>
          </label>
        </template>

        <label class="block text-sm">
          密码
          <input
            v-model="password"
            type="password"
            required
            class="mt-1 w-full rounded-lg bg-[#1a1a1a] px-3 py-2 outline-none focus:ring-1 focus:ring-[#feca57]"
          />
        </label>

        <div
          v-if="error"
          class="rounded-lg bg-red-500/10 p-3 text-sm text-red-400"
        >
          {{ error }}
        </div>
        <div
          v-if="notice"
          class="rounded-lg bg-green-500/10 p-3 text-sm text-green-400"
        >
          {{ notice }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-lg bg-[#feca57] py-2.5 font-medium text-black hover:opacity-90 disabled:opacity-50"
        >
          {{ loading ? "提交中..." : tab === "login" ? "登录" : "注册" }}
        </button>
      </form>
    </main>
  </div>
</template>
