import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';

const BACKEND_PORT = Number(process.env.JMCOMIC_BACKEND_PORT) || 8000;

export default defineConfig({
  plugins: [vue()],
  root: path.resolve(__dirname, 'renderer'),
  publicDir: path.resolve(__dirname, 'renderer/public'),
  build: {
    outDir: path.resolve(__dirname, 'dist/renderer'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://127.0.0.1:${BACKEND_PORT}`,
        ws: true,
      },
    },
  },
  resolve: {
    alias: {
      '@renderer': path.resolve(__dirname, 'renderer/src'),
    },
  },
});
