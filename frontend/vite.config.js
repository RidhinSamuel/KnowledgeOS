import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// VITE_API_TARGET controls the backend proxy destination:
//   - Local dev (npm run dev):  defaults to http://127.0.0.1:8000
//     (not "localhost": Node may resolve it to ::1, but the backend container
//      only publishes on 127.0.0.1, so the proxy would get ECONNREFUSED)
//   - Docker container:         set to http://backend:8000 via docker-compose environment
// VITE_USE_POLLING=true enables polling file watching, needed for HMR when the
//   source is bind-mounted from a Windows host into the container.
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    host: true,
    strictPort: true,
    watch: process.env.VITE_USE_POLLING === 'true'
      ? { usePolling: true, interval: 300 }
      : undefined,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        secure: false,
      },
      '/healthz': {
        target: apiTarget,
        changeOrigin: true,
      },
    }
  }
})
