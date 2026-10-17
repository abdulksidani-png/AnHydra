# Frontend and backend authentication

This app connects to FastAPI in this repository. Auth0 Universal Login completes
Authorization Code + PKCE, then `GET /me` resolves the application account before
the screener appears. `/me` and `/score` use one bearer-token provider and API
origin. `/health` is public.

## Matching configuration

| Frontend setting | Backend counterpart / meaning |
| --- | --- |
| `VITE_AUTH0_DOMAIN` | `AUTH0_ISSUER=https://<domain>/` |
| `VITE_AUTH0_CLIENT_ID` | Auth0 SPA application ID, never the API audience |
| `VITE_AUTH0_AUDIENCE` | Exactly `AUTH0_AUDIENCE`, the registered API identifier |
| `VITE_API_BASE` | Empty for same-origin hosting/Vite proxy; otherwise the API HTTPS origin |
| `VITE_PROXY_TARGET` | Development backend, default `http://127.0.0.1:8000` |
| `VITE_AUTH0_DB_CONNECTION` | Default `Username-Password-Authentication` |
| `VITE_AUTH0_MICROSOFT_CONNECTION` | Exact configured connection name; empty hides the button |

All VITE values are public. Never include provider/client secrets, database
credentials, or Management API credentials. Actual tenant settings have not been
supplied for this integration.

Production builds reject missing domain/client ID/audience, anonymous mode, and
fixture scores. Runtime also refuses partial configuration. Anonymous local use
requires all three Auth0 fields empty and `VITE_AUTH0_ALLOW_ANONYMOUS=true`.
The backend independently requires `APP_ENV=development` and
`AUTH_DEV_ANONYMOUS=true`. Frontend settings cannot disable backend authentication.
`VITE_USE_MOCK=true` supplies scoring fixtures only in development; it never
replaces a failed API request automatically.

## Auth0 tenant requirements

Register an RS256 API with the shared audience and a Single Page Application.
Configure exact callback/logout URLs and web origins, including
`http://localhost:5173` for local testing and the actual production HTTPS origin.
Enable Google and intended database/Microsoft connections for the SPA. Microsoft
personal and school accounts may require different connections.

The backend already enforces admission. With
`AUTH0_CLAIM_NAMESPACE=https://anhydra.work/claims/`, a trusted Auth0 Post Login
Action must issue these signed **API access-token-only** claims:

| Claim | Value |
| --- | --- |
| `https://anhydra.work/claims/token_kind` | `user_access` for an end-user flow |
| `https://anhydra.work/claims/admission` | `google` or `verified_edu` |

Google admission requires an administrator-allowlisted Google connection.
`verified_edu` requires both verified `.edu` contact and independently confirmed
institutional membership. Email suffix alone, subject prefixes, and user-editable
metadata are insufficient. Never issue these claims in ID tokens or machine
credentials. Missing token-kind gives 401; absent admission gives 403.
Microsoft has no blanket admission; a school identity can qualify through the
same authoritative institutional policy. The frontend never creates these claims.

[Backend operations](../../../deploy/AUTH.md) defines the authoritative policy,
PostgreSQL migrations, TLS, credentials, and deployment controls.

## State and storage

The Auth0 SDK uses an in-memory cache. Refresh tokens are not enabled. Reload may
require another redirect if silent session renewal is unavailable in the browser.
Tokens are never persisted in localStorage or application user records.

`/me` returns the internal UUID, nullable name/email, email verification flag, and
creation time. Null profiles display as "Signed in". A 401 offers explicit sign-in,
403 shows access denied, and 503 offers retry without a login loop. Scoring 503
can mean database, identity-key, model, or inference unavailability.

Account state is tied to both subject and token-provider generation. Identity
changes hide the old profile immediately. Logout clears the provider and account
gate; late account, token, or score responses cannot restore an old session.
The screener unmounts on account changes, clearing user-scoped results.
No account linking or email-based merging is implemented.

## Validation

Run `npm test` and `npm run build` in this directory. Supply all three public
Auth0 settings for the production build; CI placeholders test compilation only.

After installing frontend and Python dependencies, run from the repository root:

```sh
# TEST_DATABASE_URL must identify a disposable PostgreSQL database.
python -m pytest -q tests/test_frontend_integration.py
```

This executes the actual TypeScript clients through Vite into production FastAPI
route handlers with real PostgreSQL storage. It checks first/repeat `/me`, signed
bearer validation, `/score`, expired tokens, ineligible/disabled users, and public
health. It uses controlled RSA keys and a stubbed prediction, not real Auth0
redirects or ML inference. CI runs it with PostgreSQL.

Google, hosted email, and supported Microsoft logins still require tenant testing.
A successful build and local integration do not establish provider integration.

Local validation on 2026-10-17: 11 frontend tests passed; typecheck and production
build passed with placeholder public auth settings; npm audit reported no known
vulnerabilities. All 107 Python tests passed with PostgreSQL 16.14, including the
frontend HTTP integration test. No production deployment was performed.
