import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import { resolveAuthMode } from "./src/auth/config";

/**
 * In dev, Vite proxies the backend's routes so the browser never deals with CORS. The backend is the
 * FastAPI app in app/main.py. Point VITE_PROXY_TARGET at it in .env.local if it isn't on :8000.
 */
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, ".", "");
  const target = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";
  // A build must say how people get in: the three Auth0 settings, or VITE_PUBLIC_ACCESS=true for a
  // backend without sign-in. A missing or half-set configuration fails here, not in production.
  const auth = resolveAuthMode(env);
  if (command === "build" && auth.kind === "misconfigured") {
    throw new Error(`Sign-in settings incomplete: set ${auth.missing.join(", ")} (see .env.example).`);
  }

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
