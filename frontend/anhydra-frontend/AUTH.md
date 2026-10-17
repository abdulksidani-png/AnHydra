# Frontend authentication

Implements the React side of the auth design: Auth0 Universal Login,
Authorization Code + PKCE, and an access token for the AnHydra API audience
sent as `Authorization: Bearer <token>` on `/me` and `/score`.

## It does not work without the backend

`GET /me` does not exist in `app/main.py` yet. Until the backend counterpart
ships, a fully configured build authenticates with Auth0 and then stops at
"Temporarily unavailable", because `/me` returns 404.

That is the intended failure: the app will not show the screener to someone it
cannot confirm an account for. There is no client-side bypass, by design.

## Environment settings

All are build-time and public. **Never put a client secret or a Management API
credential in a `VITE_` variable** — the bundle is readable by anyone.

| Variable | Required | Notes |
| --- | --- | --- |
| `VITE_AUTH0_DOMAIN` | yes | Tenant domain, e.g. `anhydra.us.auth0.com` |
| `VITE_AUTH0_CLIENT_ID` | yes | SPA client ID |
| `VITE_AUTH0_AUDIENCE` | yes | API identifier; must match the backend's |
| `VITE_AUTH0_DB_CONNECTION` | no | Default `Username-Password-Authentication` |
| `VITE_AUTH0_MICROSOFT_CONNECTION` | no | Exact tenant connection name; unset hides the button |
| `VITE_AUTH0_ALLOW_ANONYMOUS` | no | `true` runs with no sign-in — **development builds only** |

**Partial configuration is a startup failure.** If some but not all of the
three required values are set, the app renders a configuration-error screen
listing what is missing and refuses to run. It does not fall back to an open
screener — that silent downgrade is the thing this check exists to prevent.

`VITE_AUTH0_ALLOW_ANONYMOUS` is honoured only when `import.meta.env.DEV` is
true. `npm run build` sets it false, so the bypass cannot reach production even
if the variable is set in the build environment.

## Auth0 dashboard setup — required before any of this works

In the tenant, for this SPA application:

1. **Application type:** Single Page Application.
2. **Allowed Callback URLs**, **Allowed Logout URLs**, **Allowed Web Origins**:
   the exact origins the app is served from, with no trailing slash:
   - `https://anhydra.work`
   - `http://localhost:5173` for development
3. **APIs → create an API** whose identifier is the value used for
   `VITE_AUTH0_AUDIENCE`. The backend validates tokens against the same
   identifier and the tenant's issuer.
4. **Connections → Social → Google**: enable `google-oauth2` for this
   application, with Google OAuth credentials configured.
5. **Connections → Database**: enable the database connection for this
   application if email sign-in is wanted.
6. **Microsoft:** create the connection, then put its exact name in
   `VITE_AUTH0_MICROSOFT_CONNECTION`. Do not assume one Microsoft social
   connection covers university accounts — which account types work depends on
   how the connection was created. If it is unset the button is omitted.

Refresh tokens are **not** used (see below), so no rotation policy is needed.

## Token storage

The SDK's default in-memory cache. `cacheLocation="localstorage"` and
`useRefreshTokens` were removed deliberately: a token in localStorage is
readable by any script that reaches the page and outlives the tab, which is a
large blast radius for a screening tool.

What it costs: **a full page reload drops the cached token**, and the SDK
silently re-authenticates via a hidden iframe against the Auth0 session cookie.
That works in Chrome and Firefox. In Safari, and in browsers blocking
third-party cookies, the silent call fails and the sign-in page appears again —
one click, because the Auth0 session is still valid.

To change that trade: enable refresh-token rotation in the dashboard, then set
`useRefreshTokens` and `useRefreshTokensFallback={false}` in `src/main.tsx`.
Rotation must be configured on the tenant for this to be safe.

Tokens are never written to React state, browser storage, analytics or logs.
Only the finished `Authorization` header leaves `src/auth/token.ts`.

## States

| Condition | What the person sees |
| --- | --- |
| Config incomplete | Configuration error, listing missing variables |
| Not signed in | Sign-in page with the configured providers |
| Auth0 loading | "Checking your session…" |
| Resolving `/me` | "Loading your account…" |
| `/me` 401 | Session expired, with one explicit "Sign in again" button |
| `/me` 403 | Access denied, with sign-out |
| `/me` 503 / network / 5xx | Temporarily unavailable, with retry and sign-out |
| `/score` 401 | Error banner: session expired, with sign-in |
| `/score` 403 | Error banner: account not allowed |

No state redirects automatically. A 503 in particular never triggers a login
attempt — that would be a redirect loop against a service that is merely down.

## Identity and stale responses

`src/auth/token.ts` keeps an epoch that increments on every provider install
and clear. A token acquired under an old epoch is refused, and `useAccount`
discards any `/me` response whose identity or epoch no longer matches. The
screener is keyed on the account id, so changing identity throws away every
user-scoped piece of state, including a result on screen.

Requests cannot race ahead of the provider: when auth is required and no
provider is installed, the request fails with a transient "still signing you
in" rather than going out unauthenticated and coming back 401.

## Admission policy

The UI makes no claim about who is eligible. The previous sign-in copy
promised `.edu` enforcement and said the backend checked it on every `/score`
call; neither was true, and both are removed. **Signing in successfully does
not mean admitted** — the backend decides, and a refused account gets the
access-denied screen.

If an admission rule is added, update the backend first, then the copy.

## Validation status

Honest accounting, since a build passing is not evidence of login working:

- **Not exercised against Auth0.** No tenant was available, so no provider
  flow — Google, Microsoft or database — has been run end to end.
- **Not exercised against `/me`.** The endpoint does not exist yet.
- **Not typechecked or built here.** This was written in an environment with no
  npm access. Run `npm install && npm run build` before trusting it.

What is verifiable by reading: the config gate, the state machine, the epoch
guards, and the absence of token persistence.

## Handoff to the backend implementer

- API audience: the value of `VITE_AUTH0_AUDIENCE` (agree one and use it on
  both sides).
- Issuer/domain: `https://<VITE_AUTH0_DOMAIN>/`.
- Public origins: `https://anhydra.work`, plus `http://localhost:5173`.
- Admission policy: **unspecified** — currently every authenticated account is
  treated as admitted unless `/me` returns 403. Decide this deliberately.
- `GET /me` must return the documented shape with a UUID `id`, nullable
  `display_name`/`email`, boolean `email_verified`, and `created_at`; and use
  `{"detail": "..."}` for errors, with 401/403/503 distinguished.

Account linking is out of scope. Do not merge profiles by email.
