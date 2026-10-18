import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { Auth0Provider } from "@auth0/auth0-react";
import { RuntimeErrorBoundary } from "@/components/RuntimeErrorBoundary";
import { resolveAuthMode } from "@/auth/config";
import { Auth0Session, StaticSession } from "@/auth/session";
import { setAuthRequired } from "@/auth/token";
import { routeTree } from "./routeTree.gen";
import "./styles.css";

const router = createRouter({
  routeTree,
  scrollRestoration: true,
  defaultErrorComponent: RuntimeErrorBoundary,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const mode = resolveAuthMode(import.meta.env);
// Set before anything renders, so no request can go out without knowing whether it needs a token.
setAuthRequired(mode.kind === "auth0");

// Tokens stay in the SDK's in-memory cache: no localStorage, no refresh tokens. A reload renews
// silently through the Auth0 session cookie where the browser allows it, and otherwise costs one
// click on the sign-in page.
function WithSession({ children }: { children: ReactNode }) {
  if (mode.kind !== "auth0") {
    return <StaticSession session={mode.kind === "public" ? { mode: "public" } : { mode: "misconfigured", missing: mode.missing }}>{children}</StaticSession>;
  }
  return (
    <Auth0Provider
      domain={mode.domain}
      clientId={mode.clientId}
      authorizationParams={{ redirect_uri: window.location.origin, audience: mode.audience, scope: "openid profile email" }}
      onRedirectCallback={(appState) => {
        const to = typeof appState?.returnTo === "string" && appState.returnTo.startsWith("/") && !appState.returnTo.startsWith("//") ? appState.returnTo : "/";
        router.history.replace(to);
      }}
    >
      <Auth0Session>{children}</Auth0Session>
    </Auth0Provider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WithSession>
      <RouterProvider router={router} />
    </WithSession>
  </StrictMode>,
);
