import { StrictMode, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { Auth0Provider } from '@auth0/auth0-react';
import App from './App';
import { auth0Config, authEnabled } from './auth/config';

const container = document.getElementById('root');
if (!container) throw new Error('Missing #root element in index.html');

function WithAuth({ children }: { children: ReactNode }) {
  if (!authEnabled) return <>{children}</>;
  return (
    <Auth0Provider
      domain={auth0Config.domain}
      clientId={auth0Config.clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        ...(auth0Config.audience ? { audience: auth0Config.audience } : {}),
      }}
      // Refresh tokens + localStorage keep people signed in across reloads,
      // including in Safari, which blocks the iframe-based silent refresh.
      useRefreshTokens
      cacheLocation="localstorage"
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
