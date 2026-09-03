<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useUserStore } from "../stores/user";
import { getCaptchaUrl, register } from "../api/account";
import PageHeader from "../components/PageHeader.vue";
import PillTabs from "../components/PillTabs.vue";
import { useGoBack } from "../composables/useGoBack";

const userStore = useUserStore();
const goBack = useGoBack();

const tab = ref("login");

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

const TABS = [
  { value: "login", label: "登录" },
  { value: "register", label: "注册" },
];

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
  <div class="min-h-screen bg-canvas text-ink">
    <PageHeader title="登录 / 注册" />

    <main class="mx-auto max-w-md p-6">
      <PillTabs v-model="tab" class="mb-6" :options="TABS" />

      <div v-if="userStore.user" class="card mb-6 p-4 text-sm">
        <p>
          当前已登录：<b>{{ userStore.user.username }}</b>
          <span v-if="userStore.user.title" class="ml-2 text-xs text-brand-coral">
            {{ userStore.user.title }}
          </span>
        </p>
        <button
          class="mt-3 rounded-md border border-hairline bg-canvas px-4 py-1.5 text-sm font-medium transition hover:bg-surface-soft"
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
          <input v-model="username" required class="input mt-1" />
        </label>

        <template v-if="tab === 'register'">
          <label class="block text-sm">
            邮箱
            <input v-model="email" type="email" required class="input mt-1" />
          </label>
          <label class="block text-sm">
            确认密码
            <input
              v-model="passwordConfirm"
              type="password"
              required
              class="input mt-1"
            />
          </label>
          <label class="block text-sm">
            性别
            <select v-model="gender" class="input mt-1">
              <option value="Male">男</option>
              <option value="Female">女</option>
            </select>
          </label>
          <label class="block text-sm">
            验证码
            <div class="mt-1 flex items-center gap-2">
              <input v-model="verification" required class="input flex-1" />
              <img
                :src="captchaUrl"
                alt="验证码"
                class="h-11 w-32 cursor-pointer rounded-md border border-hairline bg-white object-cover"
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
            class="input mt-1"
          />
        </label>

        <div v-if="error" class="banner-error">{{ error }}</div>
        <div v-if="notice" class="banner-success">{{ notice }}</div>

        <button type="submit" :disabled="loading" class="btn-primary w-full">
          {{ loading ? "提交中..." : tab === "login" ? "登录" : "注册" }}
        </button>
      </form>
    </main>
  </div>
</template>
