# Frontend authentication implementation instructions

## Objective and ownership

Implement the React side of the architecture in [AUTH_DESIGN.md](AUTH_DESIGN.md). Own changes under `frontend/`, including configuration examples and frontend documentation. Coordinate API changes with the backend implementer using the contract below. Do not implement a password form, password hashing, database storage, or Auth0 Management API calls in the browser.

This is an implementation brief, not a claim that these features already exist.

## Shared contract

- Use Auth0 Universal Login, Authorization Code + PKCE, and an access token requested for the configured AnHydra API audience.
- Send `Authorization: Bearer <access_token>` to `GET /me`, `POST /score`, and future private endpoints. Never use an ID token as an API credential.
- `GET /me` returns HTTP 200 with this shape (example values):

```json
{
  "id": "5e3182aa-7b6e-4cb4-b9f2-f88b2ef79a60",
  "display_name": null,
  "email": null,
  "email_verified": false,
  "created_at": "2026-10-17T12:00:00Z"
}
```

- `id` is the application's UUID, not the Auth0 subject. Names and emails are nullable. `email_verified` describes the stored contact email, not application access permission.
- Errors use FastAPI's `{ "detail": "safe user-facing message" }` shape. HTTP 401 means authentication is absent or invalid; 403 means the authenticated user is denied; 503 means a required service is unavailable. A 503 must not trigger a login loop.
- `/health` stays public. The `/score` success/request shapes remain unchanged.
- Production uses the same API audience on both sides. The backend independently validates all credentials and permissions.

## Existing files to inspect

- `src/main.tsx`: Auth0Provider; currently uses refresh tokens and localStorage.
- `src/auth/config.ts`: domain, client ID, audience, Google and database connections.
- `src/App.tsx`: AuthGate, redirects, and access-token provider lifecycle.
- `src/components/SignIn.tsx`: Google/email chooser and `.edu` policy copy.
- `src/api/client.ts`: token provider and authenticated `/score` requests.
- `src/vite-env.d.ts`, frontend env examples, `README.md`, and `DEPLOY.md`.

Preserve existing unrelated changes and scoring behavior.

## Work to implement

1. Make production configuration explicit. Require domain, client ID, and API audience; partial configuration must show a configuration failure rather than silently allowing the screener. Any anonymous development mode must require an explicit development-only setting. Check both production build configuration and runtime UI handling.
2. Retain the Auth0 React SDK redirect flow. Request `openid profile email` and the API audience. Configure exact callback/logout origins in deployment instructions. Domain, client ID, audience, and connection names are public settings; client secrets and Management API credentials never belong in `VITE_*`.
3. Add Microsoft login with a configurable connection name. The name must match a tenant-configured connection; do not assume that one Microsoft social connection supports university accounts. Support Google through the existing `google-oauth2` connection and email/password through Auth0's hosted database connection. If Microsoft is unconfigured, omit that button and document why. Universal Login may instead expose all enabled providers, provided the final interaction and configuration are documented consistently.
4. Keep the existing admission policy until the product owner changes it. Do not infer that every Microsoft account is eligible. Align UI copy with backend admission rules; avoid promising `.edu` enforcement until it exists. Provider success alone does not imply application admission.
5. Prefer the SDK's in-memory token cache. Remove localStorage persistence for the initial design. Document reload/renewal behavior and any Auth0 refresh-token rotation requirements if refresh tokens remain enabled. Do not copy tokens into React persistence, analytics, logs, or custom browser storage.
6. Add a typed authenticated `/me` client using the same token acquisition mechanism as `/score`. After Auth0 authenticates, resolve the application account before showing protected app content. Show loading while resolving; show retry for temporary backend failure. Handle null profile fields without displaying `undefined`.
7. Clear application user state and any user-scoped cached results on logout or identity change. Ensure pending `/me` responses for an old identity cannot populate the new session. Keep requests from racing ahead before the token provider is installed; clean up that provider on logout/unmount.
8. Handle 401 with a clear session-expired/relogin path, 403 with an access-denied state, and 503 with a retryable availability message. Avoid automatic redirect loops. Do not show raw token contents or detailed internal exceptions.
9. Update the inaccurate SignIn comment that currently claims backend authorization already exists. Document required Auth0 dashboard changes and all introduced environment settings.

## Configuration handoff

Provide the backend implementer the API audience, expected issuer/domain, intended public origins, and the selected admission policy. Obtain the exact configured Microsoft connection name from tenant setup. Auth0 dashboard work includes enabling connections for this SPA, provider OAuth credentials, exact callbacks/logout URLs/web origins, and refresh-token policy if used. Do not invent tenant IDs or production credentials.

Account linking is outside this release. Never merge profiles by email or add a browser-only linking flow.

## Acceptance and validation

- Google, configured Microsoft account types, and hosted email login reach `/me` with API access tokens.
- Protected content waits for successful `/me`; 401, 403, and 503 have distinct usable states.
- Missing production auth settings cannot expose the application through the development bypass.
- Logout/identity changes clear account state; stale requests cannot restore it.
- No passwords, secrets, or persisted tokens appear in frontend storage or logs.
- Run the existing frontend test suite and TypeScript/build checks. Add focused coverage for changed auth lifecycle/error behavior where practical; do not write tests that merely repeat configuration literals.
- Record which provider flows were actually exercised against Auth0 and which remain dependent on tenant configuration. A successful build alone does not verify login.

Deliver frontend changes, configuration/deployment instructions, validation results, and any tenant setup still required. Use [AUTH_BACKEND_INSTRUCTIONS.md](AUTH_BACKEND_INSTRUCTIONS.md) as the integration counterpart.
