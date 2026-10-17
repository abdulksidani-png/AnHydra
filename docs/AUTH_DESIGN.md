# User storage and Auth0 design

Status: backend authentication and PostgreSQL migrations are implemented. Deployment
still requires migration execution and Auth0 tenant configuration; see
[backend operations](../deploy/AUTH.md). Provider integration is not yet verified.

## Credential boundary

Auth0 owns authentication. Google and Microsoft own their users' passwords; Auth0 owns passwords for an Auth0-managed email/password connection. AnHydra receives tokens and profile claims, never passwords or password hashes. Do not add password, password_hash, encrypted_password, or token columns to the application user tables. Hashing is one-way verification; encryption is reversible storage. Neither operation is needed for passwords in this application.

Use Auth0 Universal Login with Authorization Code + PKCE through the existing React SDK. Request an access token for the AnHydra API audience. ID tokens describe the frontend session; they are not API authorization credentials.

## Storage

Use PostgreSQL for application users, preferences, and saved screenings. Use a private database network, TLS for connections, encrypted disks and backups, a restricted application database role, and secrets supplied through deployment configuration. These controls protect application data without introducing a second credential store.

Proposed initial migration (run through the chosen migration tool):

```sql
CREATE TABLE app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled')),
    display_name TEXT,
    email TEXT,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ
);

CREATE TABLE auth_identities (
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (issuer, subject)
);

CREATE INDEX auth_identities_user_id_idx ON auth_identities(user_id);
```

`issuer` and `subject` come from the validated access token's `iss` and `sub`. Compare subjects exactly; do not parse provider prefixes or lowercase subjects. Configure one expected issuer per environment. An email is optional, mutable display/contact data: it is neither a key nor a unique constraint. Google and Microsoft accounts sharing an email remain separate until explicitly linked. The internal UUID remains the owner key for saved screenings even if a login identity changes.

Any future saved screening table must have `user_id UUID NOT NULL REFERENCES app_users(id)`. Every read, update, and deletion filters by the authenticated internal UUID. A UUID or a user ID supplied by the browser is not proof of ownership.

## API request flow

1. React redirects to Auth0 Universal Login. The user selects Google, Microsoft, or email/password.
2. The SDK completes PKCE and obtains an API access token using the configured audience.
3. React sends `Authorization: Bearer <access_token>` to FastAPI.
4. A shared FastAPI dependency validates the signature against keys from the configured Auth0 JWKS endpoint, restricts the algorithm to RS256, and checks issuer, API audience, expiry, required claims (`iss`, `sub`, `aud`, `exp`), and `nbf` when present. Configure the key URL on the server; never take it from an untrusted token. Cache keys with bounded refresh for key rotation. Reject machine credentials on user-only routes and check route permissions when required.
5. Resolve `(iss, sub)` to `app_users.id`. On the first authenticated request, create both rows in one transaction. Handle concurrent first requests using the identity primary key: on conflict, roll back the candidate user and load the winning identity. Never leave orphan users or remap an existing identity during an upsert.
6. Check local `status` on every authenticated request. Return 403 for disabled users; return 401 for absent, expired, or invalid credentials. Authentication/key-service failures must not fall back to anonymous access.
7. Use the internal UUID for all application work. Update `last_seen_at` at a limited frequency rather than writing on every scoring request.

Add `GET /me` to return the resolved application user, and protect `/score` plus all saved-data endpoints with the same dependency. Keep `/health` public. Production must fail startup if required issuer/audience/database configuration is absent. Development bypasses must be explicit and unavailable in production.

Access tokens may omit name/email. Provision identity first, then populate optional profile fields from a server-validated OIDC profile response bound to the same subject, or deliberately configured signed namespaced claims. Do not trust profile fields or `email_verified` posted by the frontend. Do not use profile metadata as an authorization source. Keep roles/permissions server controlled.

## Google and Microsoft

- Enable the existing `google-oauth2` connection for the Auth0 SPA application. Configure production Google OAuth credentials and the exact Auth0 callback URL displayed by the connection setup.
- For personal Outlook/Hotmail accounts, use Auth0's Microsoft Account social connection. For university/work Microsoft 365 accounts, configure Microsoft Entra ID through an enterprise connection. If supporting both through an Entra connection, deliberately configure the supported account types and common endpoint according to Auth0's guidance. Confirm tenant restrictions and plan availability before rollout.
- Prefer provider buttons on Universal Login so connection settings stay centralized. The current custom React Google/email chooser can instead gain a Microsoft button whose connection name is configuration, not an assumed provider string.
- Register exact application callback, logout, and allowed web-origin URLs in Auth0. Provider secrets stay in Auth0; no client secret belongs in `VITE_*` settings.
- Existing UI copy allows Google or verified `.edu` email. Decide whether Microsoft permits any account or only eligible university accounts before implementing admission rules. Enforce that policy server-side using verified authoritative claims; an email suffix alone does not prove university membership. Update the UI copy to match.

## Linking accounts

Initially keep provider accounts separate. Later expose an explicit "Link another sign-in method" action requiring fresh authentication of both accounts. Never merge by matching email, even when both providers mark it verified. Run linking through a trusted backend with narrowly scoped Auth0 Management API credentials.

Choose a primary Auth0 account and preserve the target internal UUID. Linking can change which Auth0 subject subsequent logins return. Reconcile the identity mapping and application data through an audited, retryable operation; Auth0 and PostgreSQL cannot share a transaction. If both accounts already own saved data, define and review the merge rules first. Do not leave a secondary subject usable after linking/unlinking without an explicit policy for previously issued tokens. For the initial release, omit linking rather than implement a partial merge.

## Sessions and operational controls

The current React provider persists tokens in localStorage. Prefer the SDK's in-memory cache for the initial SPA implementation; users may need to reauthenticate after reload if session renewal is unavailable. If persistent sessions are required, consider a backend-for-frontend that keeps tokens server-side and uses Secure, HttpOnly, SameSite cookies with CSRF protection. For an SPA that uses refresh tokens, configure Auth0 refresh-token rotation, expiry, and reuse detection. Do not persist tokens in the user database or logs.

Use HTTPS, a restrictive CSP, minimal third-party scripts, rate limits on expensive scoring, and redaction of Authorization headers and tokens from logs. Do not log full identity/profile payloads. Disable a user locally for immediate API denial; separately revoke Auth0 sessions/refresh tokens as appropriate. Logout alone does not invalidate an already issued access token. Define retention and deletion for the local account, saved data, backups, and Auth0 account.

## Current repository gaps and implementation order

1. `frontend/src/auth/config.ts` and `frontend/src/main.tsx` configure Auth0, and `frontend/src/api/client.ts` sends access tokens. The backend now validates API tokens and signed end-user/admission claims, resolves PostgreSQL users, and protects `/me` and `/score`. Frontend lifecycle work remains described separately in `AUTH_FRONTEND_INSTRUCTIONS.md`.
2. Register the API audience and configure backend validation; add meaningful rejection tests before protecting `/score`.
3. Add PostgreSQL migrations, transactional provisioning, local status checks, and `/me`.
4. Configure Google and the required Microsoft account types in Auth0, then update the login chooser and admission copy.
5. Test Google, Microsoft personal, and Microsoft school accounts as applicable; first and repeat login; simultaneous provisioning; matching emails without linking; forged/wrong-audience/expired tokens; disabled users; and access to another user's saved records. Ensure production cannot silently disable authentication.

## References

- [Auth0 API access-token validation](https://github.com/auth0/docs/blob/master/articles/tokens/guides/validate-access-tokens.md)
- [Google social connection](https://developer.auth0.com/resources/labs/authentication/google-social-connection-to-login)
- [Microsoft personal and work/school connection guidance](https://support.auth0.com/center/s/article/Microsoft-Social-Account-Users-Login-Through-Azure-AD-Enterprise-Connection)
- [Auth0 account linking and reauthentication](https://auth0.com/docs/manage-users/user-accounts/user-account-linking/link-user-accounts)
