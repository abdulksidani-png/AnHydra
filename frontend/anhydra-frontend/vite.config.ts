import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * In dev, Vite proxies the backend's routes so the browser never deals with
 * CORS. The backend is the FastAPI app in app/main.py, whose routes are
 * /me, /score, /health, and /ready. Point VITE_PROXY_TARGET at it in .env.local if it isn't
 * on :8000 — e.g. the Vultr box, to develop the UI against the live model.
 */
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, '.', '');
  const target = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';
  if (command === 'build') {
    const missing = ['VITE_AUTH0_DOMAIN', 'VITE_AUTH0_CLIENT_ID', 'VITE_AUTH0_AUDIENCE'].filter(key => !env[key]?.trim());
    if (missing.length) throw new Error(`Missing production auth settings: ${missing.join(', ')}`);
    if (env.VITE_AUTH0_ALLOW_ANONYMOUS === 'true' || env.VITE_USE_MOCK === 'true') {
      throw new Error('Production builds cannot use anonymous access or fixture scores.');
    }
  }

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: '127.0.0.1',
      strictPort: true,
      proxy: {
        '/score': { target, changeOrigin: true },
        '/health': { target, changeOrigin: true },
        '/me': { target, changeOrigin: true },
        '/ready': { target, changeOrigin: true },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  };
});
