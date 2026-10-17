# Debugging report — October 17, 2026

Reviewed the Python pipeline and FastAPI app, then fetched and fast-forwarded
`main` to `bfc475f` to include the AnHydra frontend. Existing untracked `deploy/`
files were preserved.

## Fixes

- Repaired the frontend lockfile: its Vite version disagreed with package.json,
  causing `npm ci` to fail.
- Installed the src-layout Python package through requirements.txt so the
  documented module and app commands can resolve `tardiscreen`.
- Made frontend and backend validation reject multiple FASTA records and invalid
  residues; indented FASTA headers and whitespace remain supported.
- Prevented keyboard submission while the frontend is already scoring.
- Made prediction use the encoder recorded in the trained bundle, including when
  an environment override selects a different encoder. Bundles without encoder
  provenance now fail explicitly instead of silently using a guessed model.
- Added sequence hashes to embedding caches so changing a sequence under the
  same accession invalidates its vector. Caches with unknown model provenance
  are rejected; legacy caches without hashes are recomputed by the embedding build.
- Applied the matched-population filter to evaluation plots and diagnostics,
  matching the main results table. Missing matching metadata now fails explicitly.
- Rejected invalid or single-class cross-validation folds before fitting models.
- Allowed AUC plotting to handle skipped tasks without a StopIteration crash.
- Clipped disorder coordinates to sequence bounds before merging spans.
- Replaced the DisProt fetcher's substring family filter with the existing
  word-aware matcher so “nuclear” and “cleavage” are retained.
- Made dataset merging replace the previous matched-negative tier on reruns.
- Corrected zero-variance balance reporting and enabled exact matching with a
  single positive.
- Loaded the repository .env for the documented Gemini configuration workflow.
- Excluded entire test clusters from family-holdout training, handled empty
  family fetch results, and kept unclassified positives out of the negative family.

## Verification

- 22 pytest checks passed, including a synthetic training/save/load/predict
  round trip. Encoder execution is mocked; no model weights are downloaded.
- Frontend TypeScript checking and Vite production build passed.
- Python source compilation and `git diff --check` passed.
- The installed Starlette test client emits an httpx deprecation warning; the
  API tests pass.

Run tests from the repository root:

```sh
pip install -e ".[dev]"
python -m pytest -q
cd frontend
npm ci
npm run build
```

## Verification limits

This checkout contains no dataset, embedding cache, or production model bundle.
Real ESM inference, CNN training, CD-HIT/BLAST execution, live source downloads,
Gemini requests, deployment, and browser interaction were not verified. The
historical evaluation numbers were not regenerated. In particular, rerun
family-holdout evaluation and the matched-population plots before presenting
their output as results from this revision. This pass does not establish that
every possible bug has been eliminated.
