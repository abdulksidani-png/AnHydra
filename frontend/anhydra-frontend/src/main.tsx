import { StrictMode, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { Auth0Provider } from '@auth0/auth0-react';
import App from './App';
import { authState } from './auth/config';

const container = document.getElementById('root');
if (!container) throw new Error('Missing #root element in index.html');

/**
 * Token storage is the SDK's in-memory cache — the default.
 *
 * `cacheLocation="localstorage"` and `useRefreshTokens` are deliberately NOT
 * set. A token in localStorage is readable by any script that gets onto the
 * page, and it survives the tab, so the blast radius of an XSS bug is much
 * larger than it needs to be for a screening tool.
 *
 * What that costs: a full page reload drops the cached token, and the SDK
 * silently re-authenticates through a hidden iframe against the Auth0 session
 * cookie. That works in Chrome and Firefox today. In Safari and in Chrome with
 * third-party cookies blocked, the silent call fails and the person sees the
 * sign-in page again — one click, since the Auth0 session itself is still
 * valid.
 *
 * If that trade turns out to be wrong for the demo, the fix is to enable
 * refresh tokens with rotation in the Auth0 dashboard and set
 * `useRefreshTokens` plus `useRefreshTokensFallback={false}` here — and to say
 * so in the README, because rotation has to be configured on the tenant for it
 * to be safe.
 */
function WithAuth({ children }: { children: ReactNode }) {
  if (authState.kind !== 'configured') return <>{children}</>;

  const { domain, clientId, audience } = authState.settings;
  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience,
        scope: 'openid profile email',
      }}
    >
      {children}
    </Auth0Provider>
  );
}

createRoot(container).render(
  <StrictMode>
    <WithAuth>
      <App />
    </WithAuth>
  </StrictMode>,
);
