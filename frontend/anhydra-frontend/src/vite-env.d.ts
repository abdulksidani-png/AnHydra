/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin for the built app. Unset = same origin. */
  readonly VITE_API_BASE?: string;
  /** Dev-server proxy target for /score, /health and /me. */
  readonly VITE_PROXY_TARGET?: string;
  /** "true" uses fixtures and sends no requests. Opt-in only. */
  readonly VITE_USE_MOCK?: string;

  // --- Auth0. All public settings; never put a secret in a VITE_ variable. ---

  /** Auth0 tenant domain, e.g. anhydra.us.auth0.com. Required. */
  readonly VITE_AUTH0_DOMAIN?: string;
  /** Auth0 Single Page Application client ID. Required. */
  readonly VITE_AUTH0_CLIENT_ID?: string;
  /** Auth0 API identifier the backend validates against. Required. */
  readonly VITE_AUTH0_AUDIENCE?: string;
  /** Database connection name. Default Username-Password-Authentication. */
  readonly VITE_AUTH0_DB_CONNECTION?: string;
  /**
   * Microsoft connection name, exactly as configured in the tenant. Unset
   * hides the Microsoft button; there is no safe default, because the right
   * name depends on how the tenant was set up.
   */
  readonly VITE_AUTH0_MICROSOFT_CONNECTION?: string;
  /**
   * "true" runs the UI with no sign-in. Development builds ONLY — a
   * production build ignores it, so it cannot expose the app.
   */
  readonly VITE_AUTH0_ALLOW_ANONYMOUS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
