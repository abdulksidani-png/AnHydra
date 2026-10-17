/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin for the built app. Unset = same origin. */
  readonly VITE_API_BASE?: string;
  /** Dev-server proxy target for /score and /health. */
  readonly VITE_PROXY_TARGET?: string;
  /** "true" uses fixtures and sends no requests. Opt-in only. */
  readonly VITE_USE_MOCK?: string;
  /** Auth0 tenant domain. Unset = no sign-in. */
  readonly VITE_AUTH0_DOMAIN?: string;
  /** Auth0 Single Page Application client ID (public). */
  readonly VITE_AUTH0_CLIENT_ID?: string;
  /** Auth0 API identifier; the backend checks tokens against it. */
  readonly VITE_AUTH0_AUDIENCE?: string;
  /** Email + password connection name. Default Username-Password-Authentication. */
  readonly VITE_AUTH0_DB_CONNECTION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
