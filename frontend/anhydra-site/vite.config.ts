import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

/**
 * In dev, Vite proxies the backend's routes so the browser never deals with CORS. The backend is the
 * FastAPI app in app/main.py. Point VITE_PROXY_TARGET at it in .env.local if it isn't on :8000.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const target = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [tanstackRouter({ target: "react", autoCodeSplitting: true }), react(), tailwindcss()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: 5173,
      host: "127.0.0.1",
      strictPort: true,
      proxy: {
        "/score": { target, changeOrigin: true },
        "/health": { target, changeOrigin: true },
        "/me": { target, changeOrigin: true },
        "/ready": { target, changeOrigin: true },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
