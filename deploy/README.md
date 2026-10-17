# TardiScreen deployment

Follow [AUTH.md](AUTH.md) before rollout: configure Auth0 signed admission claims,
provision PostgreSQL, run migrations, and inject production settings. `/score` and
`/me` require eligible users' API access tokens; `/health` stays public.

Release validation and deployment gates are in [RELEASE.md](../docs/RELEASE.md).
The restored React frontend is optional: use `Caddyfile.react.template` when
serving its build, and proxy `/me` and `/ready` alongside `/score` and `/health`.
The existing `Caddyfile.template` and `Caddyfile.anhydra` serve the FastAPI page.
Do not replace a live React site's configuration with the FastAPI-only variant
unless deliberately switching interfaces.

## AnHydra domain configuration

The current app serves its page from `app/static/index.html` through FastAPI.
Proxy all requests to `127.0.0.1:8000`; no separate frontend build or static
web root is required. The retired `frontend/dist/` build should not be deployed.

Back up `/etc/caddy/Caddyfile`, then incorporate `deploy/Caddyfile.anhydra`,
preserving unrelated sites and replacing the old IP-only block. Confirm the
DNS records for `anhydra.work` and `www.anhydra.work` point to this server
before applying the configuration. Validate with
`caddy validate --config /etc/caddy/Caddyfile` before `systemctl reload caddy`.
Caddy manages domain HTTPS automatically. The IP address remains available
over HTTP. Restore the backup if validation or serving fails.

After updating the server checkout, restart `tardiscreen` and verify `/`,
`/health`, and a real `/score` request. Run `bash scripts/check_site.sh` for
the demo checks, and verify HTTP-to-HTTPS redirection for both hostnames.
These are deployment instructions, not confirmation of a live server update.

Replace every `@@...@@` token with the verified absolute checkout path and
registered domain. The service uses a dynamic non-root account and a read-only
mount of the checkout at `/srv/tardiscreen`. It has its own writable Hugging Face
cache at `/var/cache/tardiscreen/huggingface`. Do not change ownership of the
active dataset or model files. Systemd reads the optional checkout `.env` before
starting the app; restart the service after changing that environment file.

## Verified deployment, October 17, 2026

- Host: `64.177.42.245`, checkout `/root/tardiscreen`, revision `26c3a12`.
- Installed Caddy from its official stable Ubuntu repository.
- Installed `/etc/systemd/system/tardiscreen.service` using this template with
  `@@APP_DIR@@=/root/tardiscreen`; enabled and running as a dynamic non-root user.
- Caddy configuration currently uses `http://64.177.42.245` as its site address,
  pending a registered domain. Original configuration is backed up at
  `/etc/caddy/Caddyfile.pre-tardiscreen`.
- Both services enabled; app restart tested. Firewall allows 22, 80, and 443.
  Uvicorn listens only on localhost port 8000.
- Copied the existing Hugging Face cache into the app's separate cache directory.
- Public home page returned HTTP 200 from the deployment computer.
- Public `/health` returned `{"status":"ok","model_trained":false}`.
- `/score` returned HTTP 503 as expected because `data/models.joblib` is absent.
- Pending: data owner supplies the model, Gemini key and live API verification,
  domain/DNS/HTTPS, successful scoring, and phone check over cellular data.

The earlier direct server
check found it missing. No data pipeline commands were run during deployment.

## Before installation

- Coordinate the checkout update with Abdul while the dataset rebuild is active.
  Never run `data.py`, `embed.py`, or `coverage.py`; deployment needs no retraining.
- Confirm the checkout contains `data/models.joblib`, `.venv/bin/uvicorn`, and
  an installed `tardiscreen` package with its ML dependencies.
- Put `GEMINI_API_KEY` in the checkout's `.env` using a server-side editor.
  Optionally set `GEMINI_MODEL=gemini-3.5-flash-lite`. Restrict `.env` to mode 600,
  owned by root so systemd can load it without exposing it to other accounts.
  Never print or commit its contents.
- At your DNS provider, set the chosen hostname's A record to `64.177.42.245`.
  Remove conflicting records for that hostname, including stale AAAA records.
  Only add a www alias if it will also be included in the Caddy configuration.
- Confirm inbound TCP 80 and 443 are allowed by the Vultr firewall and host
  firewall. Preserve SSH access; port 8000 should stay private.

## Install and start

1. Render `tardiscreen.service.template` and install it as
   `/etc/systemd/system/tardiscreen.service`. Run `systemd-analyze verify` on
   that file, then `systemctl daemon-reload` and
   `systemctl enable --now tardiscreen`.
2. Check `curl --fail http://127.0.0.1:8000/health`. Expect
   `{"status":"ok","model_trained":true}`. This is a readiness check for the
   artifact's presence; a successful score is still required.
3. Install Caddy using its official Ubuntu installation instructions. Inspect
   existing Caddy configuration first and preserve other hosted sites. Render
   the domain block and incorporate it into `/etc/caddy/Caddyfile`.
4. Run `caddy validate --config /etc/caddy/Caddyfile`, then enable/start Caddy
   or reload it if already running. Caddy obtains HTTPS certificates once DNS
   and public ports reach this server.

## Acceptance checks

- Confirm both services are enabled and active. Restart the app service and
  repeat the health request to check that it starts independently of SSH.
- Verify public HTTPS `/` and `/health`, and HTTP-to-HTTPS redirection.
- Submit a known demo sequence to `/score`; check the family score, features,
  and explanation. First inference may load the ESM model and take longer.
- Verify Gemini separately using the service environment and the same request
  schema as `src/tardiscreen/explain.py`: require a successful API response and
  nonempty candidate text. An explanation alone does not prove Gemini worked,
  because the app intentionally provides an offline fallback. Never log the key.
- On a phone with Wi-Fi disabled, open the domain's `/health` and submit a
  sequence. Record this as pending until a teammate actually performs it.

## Troubleshooting and rollback

Inspect `systemctl status tardiscreen caddy` and service journals without
printing secrets. Missing model artifacts must be handled by the data owner.
Back up any existing service and Caddy configuration before replacing it.
If deployment fails, restore those configurations, validate Caddy, reload
systemd, and restart/reload the affected services. Do not roll back or replace
dataset files as part of an infrastructure rollback.
