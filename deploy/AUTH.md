# Backend authentication operations

The backend protects `GET /me` and `POST /score`. `/health` and `/ready` remain public.
The score payload and successful response are unchanged. `/me` returns only `id`,
`display_name`, `email`, `email_verified`, and UTC `created_at`. Profile fields start
null/false; arbitrary profile claims and browser fields are ignored. No password,
password hash, access token, or refresh token is stored. No account linking exists.

## Configuration and tenant handoff

Set `APP_ENV=production`, `AUTH0_ISSUER` (exact HTTPS issuer with trailing slash),
`AUTH0_AUDIENCE` (registered API identifier, never the SPA client ID),
`AUTH0_CLAIM_NAMESPACE` (HTTPS namespace with trailing slash), and `DATABASE_URL`.
Production requires PostgreSQL `sslmode=verify-full` with a trusted CA, except for a
database on the same machine (`localhost`, `127.0.0.1` or `::1`, with no `host`/`hostaddr`/
`service`/`port` query override), where traffic never leaves the server. Invalid or
missing settings fail startup. `.env` is not loaded implicitly by Python; use
`uvicorn app.main:app --env-file .env` locally. systemd uses `EnvironmentFile`.
Keep production environment files owned by root and mode 0600. Do not commit secrets.

Configure Auth0 to issue RS256 API access tokens. The frontend must request the
same audience. With namespace `https://anhydra.work/claims/`, a trusted Auth0
Post Login Action must set **access-token-only** claims:

| Claim | Allowed value and source |
| --- | --- |
| `https://anhydra.work/claims/token_kind` | `user_access`, only in a successful end-user login flow; never in ID tokens or client-credentials hooks |
| `https://anhydra.work/claims/admission` | `google` for an administrator-allowlisted Google connection validated by Auth0, or `verified_edu` for verified `.edu` contact **and independently confirmed institutional membership** |

Derive eligibility from trusted connection configuration and authoritative institution
assertions or an administrator-controlled membership registry. Do not derive it from
subject prefixes, email suffix alone, browser input, or user-editable metadata.
Fail closed when this evidence is absent. Auth0 must reserve these claims from other
issuance paths. Tokens with `gty=client-credentials` are also rejected. No additional
scopes are required. Missing/wrong token kind gives 401; missing/unknown admission
gives 403. Email verification itself grants no access.

Keep Google admission and institution-verified `.edu` admission. Microsoft has no
blanket admission: an enterprise school identity may qualify through the same
institutional evidence; personal Microsoft access remains denied until a product
policy is approved. Configure Google, Microsoft personal, and Microsoft Entra
connections deliberately; their connection names and supported account types are
tenant-specific. Enable only intended SPA connections and register exact callback,
logout, and web-origin URLs. Keep provider and Management API secrets out of VITE
settings. The backend makes no Management API calls.

No tenant credentials were supplied for this implementation. Before rollout,
verify real Google, hosted email, Microsoft personal and school flows as applicable,
including denial cases, audience, claim issuance, and `/me` then `/score`. Unit tests
with generated signing keys do not establish provider integration. Frontend login
flow changes are owned by `docs/AUTH_FRONTEND_INSTRUCTIONS.md`.

## Database migrations and privileges

### Quick path: PostgreSQL on the app server

For the single Vultr box, `deploy/setup_postgres.sh` does everything below in one step:
installs PostgreSQL (listening on localhost only), creates database `anhydra`, an owner role
`anhydra_migrate` and a runtime role `anhydra_app` with only SELECT/INSERT (+UPDATE on
`app_users`), runs the migrations, checks the runtime role cannot DELETE, and writes the
runtime `DATABASE_URL` into the checkout's `.env` (backing up the old file; mode 0600).
It is safe to re-run; it rotates role passwords and never drops data.

```sh
sudo bash deploy/setup_postgres.sh /root/tardiscreen
systemctl restart tardiscreen
```

### General case (managed or remote PostgreSQL)

Use PostgreSQL 14+ on a private network, encrypted disks and backups, and verified
TLS. Run migrations once before starting the API using a separate migration role:

```sh
python -m pip install -e '.[dev]'
# DATABASE_URL supplied securely using the migration role
python -m alembic upgrade head
python -m alembic current
```

The runtime role needs CONNECT on the database, USAGE on the schema, SELECT/INSERT
on `app_users` and `auth_identities`, and UPDATE on `app_users`. It must not own the
tables, create/drop schemas, or be a superuser. Give deletion rights only to an
administrative maintenance role. The migration has a destructive downgrade; use it
only on disposable databases or after an approved backup/rollback plan.

The identity primary key uses PostgreSQL `C` collation for exact issuer/subject
comparison. Provisioning uses a transaction and savepoint: a losing concurrent
insert rolls back its candidate user before loading the winner at READ COMMITTED.
No upsert can reassign an identity. Same-email users remain separate. Local status
is read on every protected request; last-seen updates occur at most every 15 minutes.

## Deployment and operational controls

The service's read-only repository bind mount is compatible with a network database;
do not put PostgreSQL files inside the checkout. `PrivateTmp` and `ProtectSystem`
do not block outgoing TCP. Allow DNS and HTTPS to the configured issuer and private
TCP to the database. Put the CA in `/etc/anhydra`, readable by the dynamic service
user; avoid home-directory CA paths hidden by `ProtectHome`. The service default is
production, and its environment file must retain `APP_ENV=production` and
`AUTH_DEV_ANONYMOUS=false`. Never deploy a development environment file.

Use Caddy HTTPS and the React proxy template, including `/me`. Set `CORS_ORIGINS`
only for separate frontend origins (exact HTTPS origins, no wildcard). Keep the API
bound to loopback behind the proxy, configure a restrictive frontend CSP, and apply
edge request/body/concurrency limits and scoring rate limits for the deployment's
capacity. These capacity controls are operational requirements, not built-in quotas.
For `scripts/check_site.sh`, supply `AUTH_HEADER_FILE` pointing to a temporary,
mode-0600 file containing `Authorization: Bearer <eligible API access token>`.
Remove it after the check. The token is read by curl from the file, not passed in
process arguments. Without it the scoring smoke check works only in explicit
anonymous development mode. The legacy FastAPI static page has no Auth0 login
flow; use the React frontend for authenticated deployments.

Uvicorn access logging is disabled in the service to avoid query-string leakage.
The Python log filter strips access-log queries and redacts bearer JWTs and database
URLs. Do not enable HTTP header/body tracing, SQL parameter logging, or identity
payload logging in proxies/APM. Never log Authorization, cookies, or credentials;
redaction is defense in depth, not permission to log them. Authentication and DB
errors return safe 401/403/503 messages, without infrastructure exceptions.

Signing keys are fetched only from the configured issuer's JWKS URL, with a 5-second
HTTP timeout, no redirects, a 1-hour cache lifetime, and at most one refresh per
30 seconds per worker. Unknown keys after a successful fetch give 401; unavailable
required keys give 503. Fresh known keys remain usable during an outage; expired
keys do not. Rotation can take up to 30 seconds to become visible. Never retry an
unverifiable token as anonymous. DB connection, pool, statement, and lock waits are
bounded to 5 seconds. `/health` is liveness, not a claim of Auth0/DB readiness.

If PostgreSQL is unreachable, `/me` returns 503, but `/score` still serves requests whose
token passed full verification (signature, issuer, audience, expiry, token kind and
admission), logging `Account store unavailable` instead. Trade-off: an account disabled in
the database can still score until the database answers again. A disabled account is
refused normally whenever the database is up. Unverified or ineligible requests are refused
during an outage exactly as before.

Disable an account immediately for subsequent requests with a parameterized admin
operation equivalent to:

```sql
UPDATE app_users SET status='disabled', updated_at=now() WHERE id=:user_id;
```

Separately revoke Auth0 sessions/refresh tokens if appropriate. Already running
requests may finish; logout does not revoke an issued access token. To delete an
account, disable it first, revoke/block its Auth0 identity, then delete `app_users`
by internal UUID using the maintenance role (identity rows cascade). Without
blocking upstream login, a deleted identity can provision a fresh account. Future
saved tables must reference the UUID and implement an explicit deletion policy and
owner-filtered queries. Plan Auth0 deletion separately. Retain encrypted backups
only for the organization's documented retention period; track deletions to reapply
after restoration. Use scheduled `pg_dump`/managed snapshots and test restores in an
isolated database before migrations. Keep backup credentials and artifacts outside
the repository.

## Local development and tests

Anonymous local scoring requires both `APP_ENV=development` and
`AUTH_DEV_ANONYMOUS=true`. It returns a fixed synthetic `/me` UUID, does not contact
Auth0 or PostgreSQL, and is forbidden for production/test environments. Bind such
servers only to loopback. Prefer normal authentication for integration development.

```sh
python -m pytest -q
# For real PostgreSQL provisioning/concurrency tests, supply a disposable database:
TEST_DATABASE_URL=postgresql+psycopg://test_role:password@localhost/test_db python -m pytest -q tests/test_auth_postgres.py
```

The PostgreSQL tests create and drop uniquely named schemas only. They skip explicitly
without `TEST_DATABASE_URL`. CI supplies PostgreSQL 16 and runs them with the whole
backend suite on Python 3.10 and 3.12. No real provider credentials are used.

Validation on 2026-10-17: 106 backend tests passed locally on Python 3.12 with
a disposable PostgreSQL 16.14 cluster, including migrations, six simultaneous
first requests, orphan rollback, exact identity comparisons, disabled users,
last-seen throttling, and cascading identity deletion. The full ML regression
suite was included. Google/Microsoft/Auth0 tenant flows remain unverified.
