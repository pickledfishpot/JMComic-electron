import { useRouter } from "vue-router";

/**
 * 返回上一页；如果没有可返回的历史记录（例如直接进入本页），则回首页。
 * vue-router 会在 history.state 中记录上一跳位置，借此判断能否 go back。
 */
export function useGoBack(fallback: string | { name: string } = { name: "home" }) {
  const router = useRouter();

  return function goBack() {
    if (window.history.state?.back) {
      router.back();
    } else {
      router.push(fallback);
    }
  };
}
