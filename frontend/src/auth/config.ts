/**
 * Auth0 settings, read from Vite env at build time. None of these are secrets —
 * a single-page app's domain and client ID are public by design. The secret
 * part (the signing key) never leaves Auth0, and the backend checks every token.
 *
 * Leave VITE_AUTH0_DOMAIN unset to run the UI without sign-in (local dev).
 */
export const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN?.trim() ?? '',
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID?.trim() ?? '',
  audience: import.meta.env.VITE_AUTH0_AUDIENCE?.trim() ?? '',
  /** The email + password connection's name in Auth0 (Authentication → Database). */
  dbConnection:
    import.meta.env.VITE_AUTH0_DB_CONNECTION?.trim() || 'Username-Password-Authentication',
  googleConnection: 'google-oauth2',
};

export const authEnabled = Boolean(auth0Config.domain && auth0Config.clientId);

if (auth0Config.domain && !auth0Config.clientId) {
  console.warn('VITE_AUTH0_DOMAIN is set but VITE_AUTH0_CLIENT_ID is not; sign-in is disabled.');
}
