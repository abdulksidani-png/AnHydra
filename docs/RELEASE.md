# Release preparation — October 17, 2026

## Code changes

- Shared cache validation rejects stale sequence hashes, missing rows, duplicate IDs,
  malformed arrays, non-finite vectors, missing encoder names, and unverifiable legacy caches.
- Training and embedding checkpoints write atomically. Dataset construction fails before
  replacing an existing dataset when acceptance fails.
- All comparison scripts use the same required matched-population marker.
- New matching outputs retain partner IDs. Merging keeps complete pairs after clustering,
  writes pair IDs, and rejects old matching files that cannot prove their pairing.
- CNN validation requires both classes in disjoint training/validation clusters. The length
  policy is selected on the inner training partition rather than the full outer dataset.
- Current coverage refresh handles protective and matched-negative rows and preserves the
  prior output on an incomplete response. Fetched negative lengths come from their sequences.
- API and React validation cap sequences at 1,022 residues, the existing ESM-2 token budget
  minus special tokens. The embedding representation and pooling convention are unchanged.
- Offline readouts distinguish signed auxiliary biophysical signals from the ESM score.
  Invalid Gemini timeouts no longer prevent import. Inference failures return an actionable 503.
- `/health` reports liveness and artifact presence. `/ready` validates the bundle and installed
  encoder runtime; it does **not** claim encoder weights loaded or inference verified. A real
  score is still required. React routing must proxy `/ready` to FastAPI.
- The inline page prevents overlapping keyboard submissions. React uses the same length policy,
  a longer inference timeout, current recorded metrics, and more precise scope statements.
- Vite was updated to 6.4.3, compatible with the current plugin. The resulting npm audit
  reported zero vulnerabilities. Development server binding defaults to localhost.
- GitHub CI runs Python regression tests, frontend contract tests/build, dependency audit,
  and shell syntax checks. CI does not deploy or download/train a protein encoder.

## Verification

Run from a clean checkout:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
bash -n scripts/check_site.sh scripts/collect_results.sh
cd frontend
npm ci
npm test
npm run build
npm audit --audit-level=moderate
```

Tests use synthetic data and mocked embedding responses. Passing them does not reproduce the
published protein-model experiments. Torch, encoder weights, and real data/model artifacts were
not available in the release-preparation checkout. Model-consuming legacy caches now need
`python -m tardiscreen.embed`; do not backfill invented hashes. Rerun matching before merging
legacy matched files. Existing compatible model bundles can still be served without retraining.

Local validation: 51 Python tests and four frontend contract tests passed; the production
frontend build, shell syntax, and inline JavaScript syntax checks passed. One upstream
Starlette/httpx deprecation warning remains. GitHub-hosted CI must also pass on the pushed commit.

## Deployment procedure

1. Back up the current server code revision, Caddy configuration, built UI, and model artifact.
   Preserve data and the root-owned `.env`. Record current service status and verify rollback.
2. Update the server checkout to the reviewed release commit. Install backend dependencies
   including the ML extra in its virtualenv, preserving the compatible model and encoder cache.
   Avoid rebuilding datasets or retraining as part of deployment.
3. If deploying React, build with `npm ci && npm test && npm run build` using the intended public
   environment values and `VITE_USE_MOCK=false`. Copy `frontend/dist/` contents to the web root.
   Use `deploy/Caddyfile.react.template`, preserving other sites and the current hostnames.
   `/score`, `/health`, and `/ready` must reach FastAPI; `/ready` must return JSON rather than the SPA.
   The FastAPI-only Caddy templates remain available for the built-in page.
4. Validate Caddy, restart `tardiscreen`, and reload Caddy. Run
   `bash scripts/check_site.sh https://anhydra.work`, and verify the `www` hostname,
   HTTP-to-HTTPS redirects, real JS/CSS responses, both UI examples, and a phone-sized view.
5. Verify the intended explanation source. The smoke script's text heuristic is a convenience,
   not authoritative Gemini provenance. Auth0 is optional UI sign-in only; this backend does
   not enforce bearer-token authorization. The API remains public.
6. If readiness, scoring, or assets fail, restore the previous reviewed code/build/configuration
   and restart/reload the affected services. Do not roll back datasets incidentally.

## Outstanding live-release gate

During preparation the public site returned `/health` with `model_trained: true`, and a synthetic
score request returned `0.991`, `protective`, three contributions, and a nonempty explanation.
The existing `/ready` URL returned HTML, confirming the release route was not active there.
The deployment SSH key `~/.ssh/tardiscreen_vultr` was rejected. No server files or service
configuration were changed. Deploying the fixes requires working operator access, then the
checks above. A passing old-site score is not evidence that these changes have shipped.

## Scientific results remain historical

The committed OOF artifacts contain 529 positives and 520 negatives, not 529 complete pairs.
The original dataset summary is now labeled historical. The related-family holdouts do not
prove absence of all homologs. No release-time change regenerates or retroactively validates
those measurements. Rerun the complete verified pipeline, retain final pair/balance and split
metadata, and publish new results before claiming performance for retrained release models.

Remaining research work includes a stricter homology split, taxonomic controls, calibration,
independent motif validation, and reproducible encoder/data revisions. These are limitations of
the scientific claim, not reasons to silently change the existing trained representation.
