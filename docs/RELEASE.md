# Release checks

Use the [deployment guide](../deploy/README.md) for the intended interface and
Caddy configuration, and [backend authentication operations](../deploy/AUTH.md)
for account setup, migrations, tenant claims, and the documented scoring behavior
during database outages. Match these instructions to the code revision being
deployed; historical test counts and server observations do not establish its
current readiness.

## Before deployment

1. Record the release commit and run its [CI checks](../.github/workflows/ci.yml).
   CI defines which frontend directories are tested. Use the selected frontend's
   README and deployment instructions for its build and public environment settings.
2. Back up the current server revision, Caddy configuration, built UI, and model
   artifact. Preserve the server environment and encoder cache. Verify rollback.
3. Confirm the intended authentication policy and frontend/backend configuration
   with the deployment owner. Do not infer API access policy from whether the UI
   displays a login button. Verify real login and denial flows when using Auth0.
4. Preserve compatible datasets, embeddings, and model artifacts. Do not run the
   training pipeline or change representations as part of routine deployment.

## Acceptance and rollback

Follow the deployment guide to validate Caddy and update services. Verify HTTPS,
redirects, real JS/CSS assets, the selected UI's examples, and a phone-sized view.
`/health` reports liveness and artifact presence; `/ready` validates the bundle and
encoder runtime but does not establish successful inference. Require a real score
using the configured access policy. An offline explanation does not verify Gemini.

The deployment guide also describes `scripts/check_site.sh`; inspect its
expectations against the selected release's authentication policy before using
it as an acceptance gate. An unauthenticated smoke request cannot validate a
protected scoring endpoint.

If acceptance fails, restore the previous reviewed code, UI build, and server
configuration, then restart or reload the affected services. Do not roll back
datasets incidentally.

## Scientific results

The committed evaluation artifacts are historical measurements, not outputs
regenerated for every release. They contain 529 positives and 520 negatives,
rather than 529 complete pairs. See [METHODS.md](METHODS.md) and
[results/dataset_summary.md](results/dataset_summary.md) for dataset stages and
limitations. Related-family holdouts do not prove absence of all homologs.

Before publishing metrics for a retrained model, retain verified inputs, final
pair/balance diagnostics, dataset and encoder revisions, split metadata, and the
code revision. Passing software tests does not reproduce the protein experiments.
