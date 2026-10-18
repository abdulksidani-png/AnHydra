// Sign-in settings, read at build time. Domain, client ID and audience are public by design (they are
// in every browser's copy of the bundle); client secrets never belong in a VITE_ variable.
//
// The site runs in one of two explicit modes, matching the backend:
//   auth0   all three Auth0 settings present: screening needs a signed-in, admitted account.
//   public  VITE_PUBLIC_ACCESS=true and no Auth0 settings: no sign-in, for a backend running
//           with PUBLIC_ACCESS=true.
// Anything else is a configuration error. vite.config.ts refuses to build it, and at runtime the
// Screen page shows what is missing instead of quietly serving an open screener.

export type AuthMode =
  | { kind: "auth0"; domain: string; clientId: string; audience: string }
  | { kind: "public" }
  | { kind: "misconfigured"; missing: string[] };

const REQUIRED = ["VITE_AUTH0_DOMAIN", "VITE_AUTH0_CLIENT_ID", "VITE_AUTH0_AUDIENCE"] as const;

export function resolveAuthMode(env: Record<string, string | undefined>): AuthMode {
  const [domain, clientId, audience] = REQUIRED.map((key) => (env[key] ?? "").trim());
  const missing = REQUIRED.filter((key) => !(env[key] ?? "").trim());
  const publicAccess = (env.VITE_PUBLIC_ACCESS ?? "").trim() === "true";
  if (missing.length === 0 && !publicAccess) return { kind: "auth0", domain, clientId, audience };
  if (missing.length === REQUIRED.length && publicAccess) return { kind: "public" };
  return { kind: "misconfigured", missing: publicAccess ? ["VITE_PUBLIC_ACCESS or the Auth0 settings, not both"] : missing };
}
