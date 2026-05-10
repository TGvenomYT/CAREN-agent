import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
//
// Without these proxies, the Vite dev server (5173) does not know about
// the FastAPI backend (8000): /api/mail/* fails, and the <iframe src="/voice/">
// gets caught by Vite's SPA fallback, which returns index.html — making the
// iframe load the dashboard inside itself ("mirrored" effect).
const BACKEND = 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/api':   { target: BACKEND, changeOrigin: true },
      '/voice': { target: BACKEND, changeOrigin: true, ws: true },
      // FastRTC uses websockets for the audio stream; Gradio also pushes
      // events over WS at /queue/join et al. Proxy them all.
      '/queue':           { target: BACKEND, changeOrigin: true, ws: true },
      '/gradio_api':      { target: BACKEND, changeOrigin: true, ws: true },
      '/webrtc':          { target: BACKEND, changeOrigin: true, ws: true },
      '/file':            { target: BACKEND, changeOrigin: true },
      '/assets/gradio':   { target: BACKEND, changeOrigin: true },
    },
  },
})
