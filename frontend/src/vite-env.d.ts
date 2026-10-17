/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin for the built app. Unset = same origin. */
  readonly VITE_API_BASE?: string;
  /** Dev-server proxy target for /score and /health. */
  readonly VITE_PROXY_TARGET?: string;
  /** "true" uses fixtures and sends no requests. Opt-in only. */
  readonly VITE_USE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
