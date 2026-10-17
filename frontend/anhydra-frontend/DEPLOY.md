# Deploy the authenticated frontend

On this branch the integrated app is `frontend/anhydra-frontend`. The older
`frontend/src` app remains separate. Build and deploy this directory's `dist`,
not the parent directory's output.

1. Complete [backend setup](../../../deploy/AUTH.md): PostgreSQL migration,
   production settings, Auth0 API audience, and signed admission claims.
2. Copy `.env.example` to `.env.local` and configure the public Auth0 domain,
   SPA client ID, and audience. Keep `VITE_API_BASE` empty for same-origin hosting
   and both fixture/anonymous flags false. Rebuild when these settings change.
3. Run `npm ci`, `npm test`, and `npm run build` in this directory.
4. Deploy `dist/` to `/var/www/tardiscreen`, retaining the previous build for rollback.
5. Use [the React Caddy template](../../../deploy/Caddyfile.react.template) with
   the HTTPS domain. It proxies `/me`, `/score`, `/health`, and `/ready` before
   the SPA fallback. Validate Caddy configuration before reloading.

The backend stays under systemd; production assets need no Node server. The legacy
FastAPI HTML page has no Auth0 login, so Caddy must serve the React build at `/`.
Register the exact origin in Auth0 callbacks, logout URLs, and web origins.
For separate hosting, set `VITE_API_BASE` and exact backend `CORS_ORIGINS`.
Never send API tokens over public HTTP or use wildcard CORS.

Check `/health` for liveness and `/ready` for model readiness. Complete real provider
sign-in, confirm `/me` returns JSON rather than SPA HTML, then score a known input.
Check 401/403/503 states. `scripts/check_site.sh` accepts a protected temporary
`AUTH_HEADER_FILE`, documented in the backend guide.

Vite's development proxy does not run in `vite preview` or a production static
server. Use Caddy for same-origin API routing; preview alone cannot reach `/me`
and `/score` unless `VITE_API_BASE` was set when building.

Actual tenant logins and production deployment have not been performed by local
integration checks. Keep the previous Caddy configuration and build for rollback.
