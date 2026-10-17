# Backend authentication implementation instructions

## Objective and ownership

Implement FastAPI authentication and PostgreSQL application user storage from [AUTH_DESIGN.md](AUTH_DESIGN.md). Own backend modules, migrations, Python dependencies, backend tests, and backend deployment documentation. Coordinate with the frontend implementer using the contract below. Do not modify the React login flow as part of this assignment.

Auth0 and upstream providers own credentials. Never receive, store, hash, encrypt, log, or return user passwords or password hashes. Do not store login access/refresh tokens in application user tables.

## Shared contract

- Protect `GET /me` and `POST /score` with Auth0 API access tokens in `Authorization: Bearer <access_token>`. Keep `/health` public and preserve the existing `/score` request/success schema.
- `GET /me` provisions/resolves the local account and returns exactly these fields:

```json
{
  "id": "5e3182aa-7b6e-4cb4-b9f2-f88b2ef79a60",
  "display_name": null,
  "email": null,
  "email_verified": false,
  "created_at": "2026-10-17T12:00:00Z"
}
```

- `id` is an internal UUID. Name/email are nullable; timestamp is UTC ISO 8601. Email verification is not itself admission permission.
- Return `{ "detail": "safe user-facing message" }` on failure: 401 for missing/invalid/expired credentials, 403 for disabled or otherwise ineligible users, and 503 for unavailable identity-key or database services. Include `WWW-Authenticate: Bearer` for 401. Do not expose tokens or infrastructure exceptions.
- Frontend and backend must use the same registered API audience. Coordinate any contract change before implementing it.

## Existing files to inspect

- `app/main.py`: currently public `/score`, health/readiness, and static page delivery.
- `requirements.txt`, `pyproject.toml`, existing `tests/`, and environment examples.
- `deploy/` service configuration and deployment guides.
- The frontend already sends tokens; its UI gate currently does not provide API authorization.

Keep ML model behavior and sequence validation unchanged. Inspect deployment mounts before choosing database/network or configuration paths.

## Work to implement

1. Add validated server configuration for environment, Auth0 issuer, API audience, and PostgreSQL connection string. Document stable names such as `AUTH0_ISSUER`, `AUTH0_AUDIENCE`, and `DATABASE_URL`. Fail production startup on missing/invalid security configuration. Permit anonymous local development only through an explicit development-only option that cannot run in production.
2. Use a maintained JWT verification library with cryptographic verification. Restrict accepted signing algorithm to RS256. Load JWKS only from the configured trusted issuer, never token-supplied URLs. Check signature, exact issuer, audience, expiry, required `iss`/`sub`/`aud`/`exp`, and `nbf` when present. Reject ID tokens, wrong-audience tokens, malformed bearer headers, and machine credentials on user routes. Configure an end-user token discriminator/claim policy explicitly rather than depending only on subject naming conventions. Add required scopes only if they are configured in Auth0 and shared with the frontend.
3. Cache signing keys and implement bounded key refresh on an unknown `kid`, with timeouts and refresh throttling. Known invalid credentials return 401. If required trusted keys cannot be obtained because the key service is unavailable, fail closed with 503. Do not fetch keys for every request or accept unverifiable tokens during an outage.
4. Introduce PostgreSQL migrations for `app_users` and `auth_identities`, using the schema in AUTH_DESIGN.md. Choose a maintained database/migration stack consistent with this Python project and document migration commands. Do not automatically create/drop production tables at request time or store production data in the repository.
5. Implement transactional resolution of exact `(issuer, subject)` to internal UUID. Provision on the first accepted authenticated request. Make concurrent first requests converge on one account using the identity primary key; roll back a losing candidate user and load the winner. Do not reassign an existing identity through an upsert. Test with PostgreSQL semantics, not only an in-memory substitute.
6. Enforce `app_users.status` for every protected request, including requests using tokens issued before local disablement. Limit `last_seen_at` writes. Keep contact/profile fields nullable and never make email the identity key or automatically merge duplicate emails.
7. Populate optional profile data only from trusted server-validated sources. API tokens may have no email/name. Start with nullable fields unless a validated OIDC profile response or configured signed namespaced claims is available. Bind any retrieved profile to the authenticated subject. Do not trust a browser-posted email, verification flag, role, or user ID.
8. Centralize an authenticated-user dependency and use it in `/me` and `/score`; future saved records must filter every operation by its internal UUID. Authenticate and check admission before running expensive ML inference. A client-supplied record ID is not an ownership check.
9. Define the admission policy explicitly. Current UI promises Google or verified `.edu` email; Microsoft eligibility is undecided. Keep current intended restrictions until the product owner changes them, but do not trust provider prefixes or email suffixes as university membership proof. If provider identity or institutional membership is required, obtain authoritative signed claims through Auth0 and fail closed when required claims are absent. Share the implemented policy and claim names with frontend/tenant setup.
10. Add request/log redaction and document HTTPS, restricted database credentials, TLS, private networking, encrypted disks/backups, and secret injection. Ensure deployment sandbox/service settings allow the intended database connection. If frontend and API differ in origin, configure exact allowed CORS origins rather than a wildcard. Document how to disable users, migrate, back up, and delete application accounts and associated data.

## Microsoft and Auth0 handoff

The tenant administrator must register the AnHydra API audience, configure the SPA, and enable Google plus the intended Microsoft account types. Personal Microsoft and Entra work/school support can require different connections/configuration. Supply required custom claims/permissions to whoever configures Auth0. Do not put Management API credentials in frontend configuration.

Account linking is deferred. Google and Microsoft identities remain separate even with matching verified emails. Do not implement email-based linking. Any future linking feature must reauthenticate both accounts, preserve the internal UUID, reconcile existing data, handle cross-system failures, and define behavior for previously issued tokens.

## Acceptance and validation

Add meaningful tests for:

- Missing bearer credentials, malformed tokens, invalid signatures/algorithms, wrong issuer/audience, missing required claims, expired tokens, future `nbf`, and machine credentials.
- Signing-key rotation, bounded unknown-key refresh, and key-service failure without anonymous fallback.
- First/repeated/concurrent provisioning, rollback without orphan users, and exact subject comparison.
- Matching emails across providers staying separate, nullable profile data, and rejection of untrusted profile/role inputs.
- Disabled/ineligible users receiving 403 before inference, unavailable database returning a safe failure, and correct `/me` response shape.
- Missing production settings and prohibited production development bypass.
- Ownership isolation when saved-record routes exist; do not add speculative endpoints just to test them.

Run the relevant existing backend regression checks as well as new auth/database checks. Keep automated tests independent of real provider credentials by using controlled signing keys and an isolated test database. Separately record actual tenant integration verification for Google and supported Microsoft account types.

Deliver backend code, migrations, configuration/deployment instructions, validation results, and remaining tenant requirements. Use [AUTH_FRONTEND_INSTRUCTIONS.md](AUTH_FRONTEND_INSTRUCTIONS.md) as the integration counterpart. Do not claim that provider integration is verified solely because unit tests pass.
