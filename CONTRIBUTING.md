# Contributing

Keep `main` deployable. Use a branch per task, make focused commits, and open a
pull request for teammate review before merging.

Coordinate changes with the relevant owner in [TEAM.md](TEAM.md), especially
while frontend work is in progress. Preserve unrelated work and check branch
ancestry before retiring a branch. A branch name or an old commit date does not
establish that its work has been merged.

Only the data owner regenerates datasets, embeddings, or trained models. Routine
deployment and documentation changes do not require retraining.

## Development

Follow the [README](README.md) for setup and the staged data pipeline. Copy
`.env.example` to `.env` for local settings. Keep secrets, local environments,
generated datasets, and model caches out of Git.

Run the checks relevant to your changes. The [CI workflow](.github/workflows/ci.yml)
defines the backend suite and frontend test/build matrix. Each frontend's
`package.json` and README define its commands; coordinate which app is being
deployed with the frontend owner.

## Review and release

- Keep changes scoped and describe their behavior and validation in the PR.
- Preserve the distinction between family classification and measured protective
  efficacy. Recorded scientific results and limitations live in
  [docs/METHODS.md](docs/METHODS.md) and [docs/results/](docs/results/).
- Follow [release checks](docs/RELEASE.md) and [deployment documentation](deploy/README.md)
  before deploying. Passing mocked tests does not verify a live model or login flow.
