import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 构建产物输出到后端 static/ 目录，由 FastAPI 直接托管，保持单进程部署。
// base 必须为 /static/：产物位于 static/assets/，而 FastAPI 把 static 目录挂在 /static 前缀下。
export default defineConfig({
  base: '/static/',
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    outDir: '../static',
    emptyOutDir: false,
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    // 开发期把 /api 与 /static 代理到 FastAPI，前端热更新 + 真实接口联调
    proxy: {
      '/api': 'http://127.0.0.1:8011',
      '/static': 'http://127.0.0.1:8011',
    },
  },
})
