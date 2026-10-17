import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * In dev, Vite proxies the backend's routes so the browser never deals with
 * CORS. The backend is the FastAPI app in app/main.py, whose routes are
 * /score and /health. Point VITE_PROXY_TARGET at it in .env.local if it isn't
 * on :8000 — e.g. the Vultr box, to develop the UI against the live model.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const target = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true,
      proxy: {
        '/score': { target, changeOrigin: true },
        '/health': { target, changeOrigin: true },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  };
});
