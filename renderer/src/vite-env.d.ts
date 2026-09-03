/// <reference types="vite/client" />

/** 主进程经 preload 注入的后端端口（仅打包环境有意义，dev 走 vite 代理） */
declare global {
  interface Window {
    __JMCOMIC_BACKEND_PORT__?: number;
  }
}

export {};

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<object, object, any>
  export default component
}
