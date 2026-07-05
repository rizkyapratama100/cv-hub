import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Required for Docker
    port: 5173,
    proxy: {
      // In dev (Docker), proxy API calls through Vite to the backend container.
      // The backend service is reachable as "backend:8000" inside Docker's network.
      // This avoids CORS issues and works whether running in Docker or locally.
      '/health': {
        target: process.env.VITE_BACKEND_INTERNAL_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
      '/processors': {
        target: process.env.VITE_BACKEND_INTERNAL_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
      '/process-video': {
        target: process.env.VITE_BACKEND_INTERNAL_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
      '/process-image': {
        target: process.env.VITE_BACKEND_INTERNAL_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
