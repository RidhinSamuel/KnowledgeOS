import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// VITE_API_TARGET controls the backend proxy destination:
//   - Local dev (npm run dev):  defaults to http://localhost:8000
//   - Docker container:         set to http://backend:8000 via docker-compose environment
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})

