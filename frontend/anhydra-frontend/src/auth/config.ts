/**
 * Auth0 settings, read from Vite env at build time.
 *
 * None of these are secrets: a single-page app's domain, client ID, audience
 * and connection names are public by design, and they are baked into the
 * bundle. The signing key never leaves Auth0, and the backend validates every
 * token independently. Client secrets and Management API credentials must
 * never appear in a VITE_* variable.
 *
 * Production configuration is explicit. Domain, client ID and API audience are
 * all required; a partial configuration is a startup failure rather than a
 * quiet downgrade to an open screener. The anonymous mode below is a
 * development convenience and is ignored in a production build, so a missing
 * setting cannot expose the app through the bypass.
 */

export interface Auth0Settings {
  domain: string;
  clientId: string;
  audience: string;
  /** Auth0 database (email + password) connection name. */
  dbConnection: string;
  /** Google social connection. Fixed name in every tenant. */
  googleConnection: string;
  /**
   * Microsoft connection name, exactly as configured in the tenant. Empty
   * when the tenant has none — the UI then omits the Microsoft button rather
   * than offering a login that cannot succeed.
   */
  microsoftConnection: string;
}

function read(key: keyof ImportMetaEnv): string {
  const value = import.meta.env[key];
  return typeof value === 'string' ? value.trim() : '';
}

const domain = read('VITE_AUTH0_DOMAIN');
const clientId = read('VITE_AUTH0_CLIENT_ID');
const audience = read('VITE_AUTH0_AUDIENCE');

const settings: Auth0Settings = {
  domain,
  clientId,
  audience,
  dbConnection: read('VITE_AUTH0_DB_CONNECTION') || 'Username-Password-Authentication',
  googleConnection: 'google-oauth2',
  microsoftConnection: read('VITE_AUTH0_MICROSOFT_CONNECTION'),
};

const REQUIRED: Array<[keyof Auth0Settings, string]> = [
  ['domain', 'VITE_AUTH0_DOMAIN'],
  ['clientId', 'VITE_AUTH0_CLIENT_ID'],
  ['audience', 'VITE_AUTH0_AUDIENCE'],
];

const missing = REQUIRED.filter(([field]) => !settings[field]).map(([, name]) => name);

/**
 * The anonymous mode must be asked for explicitly AND can only take effect in
 * a development build. `import.meta.env.DEV` is false in anything produced by
 * `npm run build`, so a production deployment cannot fall through to it.
 */
const anonymousRequested = read('VITE_AUTH0_ALLOW_ANONYMOUS') === 'true';
const anonymousAllowed = anonymousRequested && import.meta.env.DEV;

export type AuthState =
  /** Fully configured: sign-in is required. */
  | { kind: 'configured'; settings: Auth0Settings }
  /** Development build with the bypass explicitly enabled and no Auth0 config. */
  | { kind: 'anonymous' }
  /** Something is missing. The app shows a configuration failure. */
  | {
      kind: 'misconfigured';
      missing: string[];
      /** True when the bypass was requested but refused because this is a production build. */
      anonymousIgnored: boolean;
    };

function resolve(): AuthState {
  if (missing.length === 0) return { kind: 'configured', settings };
  if (missing.length === REQUIRED.length && anonymousAllowed) return { kind: 'anonymous' };
  return {
    kind: 'misconfigured',
    missing,
    anonymousIgnored: anonymousRequested && !import.meta.env.DEV,
  };
}

export const authState: AuthState = resolve();

/** Convenience for the common check. */
export const authRequired = authState.kind === 'configured';

export const auth0Settings: Auth0Settings | null =
  authState.kind === 'configured' ? authState.settings : null;
