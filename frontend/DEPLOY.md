# Deploying this UI to the Vultr box

For whoever owns deploy/infra (per `docs/STATUS.md`, that's Teammate 1 — systemd, Caddy, `.env`, DNS).

## What this is

A React frontend for AnHydra, replacing the inline `PAGE` string in
`app/main.py`. It calls the **existing** `POST /score` and `GET /health` with
no backend changes required — the response type in `src/types.ts` mirrors
`ScoreResponse` field for field.

## What changes on the server

Nothing in `src/tardiscreen/`. Only what serves HTML at `/`.

### Build (on a laptop, not the server)

```bash
npm install
npm run build          # emits dist/ — plain static files, no Node needed to serve
```

### Option A — Caddy serves the build (recommended)

Keeps the frontend and the API independent: a UI deploy cannot break scoring.

```
64.177.42.245 {
    handle /score* {
        reverse_proxy localhost:8000
    }
    handle /health* {
        reverse_proxy localhost:8000
    }
    handle {
        root * /var/www/tardiscreen
        try_files {path} /index.html
        file_server
    }
}
```

```bash
ssh root@64.177.42.245 'mkdir -p /var/www/tardiscreen'
scp -r dist/* root@64.177.42.245:/var/www/tardiscreen/
ssh root@64.177.42.245 'systemctl reload caddy'
```

`app/main.py`'s `index()` route then just stops being reached. Leave it in
place as a fallback, or delete it in a separate commit.

### Option B — FastAPI serves the build

One process, but `git pull` on the server now has to carry built assets.

```python
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DIST = Path(__file__).resolve().parent.parent / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        return FileResponse(DIST / "index.html")
```

This must go **after** `/score` and `/health` are registered, or the catch-all
swallows them. Add `dist/` to the deploy step; it is gitignored by default here.

### Stage it first

Deploy to a second path before replacing `/`, so the working demo survives a
mistake:

```
handle /v2* {
    uri strip_prefix /v2
    root * /var/www/tardiscreen-v2
    try_files {path} /index.html
    file_server
}
```

## The blocker, as of 2026-10-17 11:30 ET

`POST /score` on the live box returns **503**:

```
Model not trained yet — run `python -m tardiscreen.model` to write
data/models.joblib, then reload.
```

`docs/STATUS.md` records `data/models.joblib` as existing and working on the
server, so this is a discrepancy worth chasing before anything else. The
likely cause is that `data/` is gitignored, so a deploy from a fresh clone
brings no `models.joblib` — it has to be copied up or regenerated on the box.
Note that `docs/STATUS.md` also says nobody but the data owner runs the
dataset scripts on the server, so regenerating is the data owner's call, not a
deploy step.

Until that is fixed, this UI will correctly show the 503 as an error and no
score — by design, matching the backend's rule that a fabricated number is
worse than no number.

## One small backend request (optional, 3 lines)

`explain()` returns either the Gemini readout or the offline template, and the
response doesn't say which. Adding the source to `ScoreResponse` lets the UI
label it honestly instead of generically:

```python
class ScoreResponse(BaseModel):
    ...
    explanation_source: Literal["gemini", "template"] = "template"
```

`explain()` already knows which path it took. Not a blocker; the UI just says
"generated from the feature contributions" without it.
