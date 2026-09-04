import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

const BACKEND_PORT = Number(process.env.JMCOMIC_BACKEND_PORT) || 8000;

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  // 打包后渲染层走 file:// 加载，资源路径必须是相对的，
  // 否则 /assets/* 会解析到文件系统根目录导致白屏
  base: "./",
  root: path.resolve(__dirname, "renderer"),
  publicDir: path.resolve(__dirname, "renderer/public"),
  build: {
    outDir: path.resolve(__dirname, "dist/renderer"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // Electron 主进程写死加载 5173，端口被占时必须直接失败而不是静默换端口
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      "/ws": {
        target: `ws://127.0.0.1:${BACKEND_PORT}`,
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      "@renderer": path.resolve(__dirname, "renderer/src"),
    },
  },
});
