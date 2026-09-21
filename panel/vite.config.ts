import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

// Frappe backend (frappe_docker frontend container)
const FRAPPE_URL = process.env.FRAPPE_URL ?? 'http://localhost:8080'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // Vite's default "localhost" binds IPv6-only here; the browser and tools use 127.0.0.1.
    host: '127.0.0.1',
    port: 5173,
    // Same-origin proxy: the session cookie and CSRF token just work, no CORS needed.
    proxy: {
      '/api': { target: FRAPPE_URL, changeOrigin: true },
      '/files': { target: FRAPPE_URL, changeOrigin: true },
      '/private': { target: FRAPPE_URL, changeOrigin: true },
    },
  },
})
