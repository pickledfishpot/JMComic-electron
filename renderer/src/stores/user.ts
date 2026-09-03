import { ref } from "vue";
import { defineStore } from "pinia";
import { getMe, login as apiLogin, logout as apiLogout } from "../api/account";
import type { UserInfo } from "../api/account";

export const useUserStore = defineStore("user", () => {
  const user = ref<UserInfo | null>(null);
  const loaded = ref(false);

  async function fetchMe() {
    try {
      const res = await getMe();
      // 防御：后端异常返回空壳用户时视为未登录
      user.value = res.user?.username ? res.user : null;
    } catch {
      user.value = null;
    } finally {
      loaded.value = true;
    }
  }

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password);
    user.value = res.user;
    loaded.value = true;
  }

  async function logout() {
    await apiLogout();
    user.value = null;
  }

  return { user, loaded, fetchMe, login, logout };
});
