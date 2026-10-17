# AnHydra — frontend

A React frontend for AnHydra, in the "field guide" direction: warm paper,
forest green and ochre, a serif for the editorial voice and a geometric sans
for anything mechanical.

It connects to this repository's authenticated FastAPI backend through `GET /me`,
`POST /score`, and public `GET /health`. Run the commands below from this branch's
integrated app directory, `frontend/anhydra-frontend`.

```
npm ci
npm test
npm run dev          # http://localhost:5173
```

Copy `.env.example` to `.env.local` and supply the public Auth0 domain, SPA client
ID, and API audience matching the backend. Follow [AUTH.md](AUTH.md) for the signed
claims the tenant must issue. Start the backend from the repository root:

```
python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

Vite proxies `/me`, `/score`, `/health`, and `/ready` to `http://127.0.0.1:8000`.
Leave `VITE_API_BASE` empty to use that proxy. Configure `VITE_PROXY_TARGET` for
another backend; use HTTPS for remote servers.

For anonymous local work, leave the three frontend Auth0 fields empty and set
`VITE_AUTH0_ALLOW_ANONYMOUS=true`. The backend independently requires
`APP_ENV=development` and `AUTH_DEV_ANONYMOUS=true`. For UI-only fixtures, also set
`VITE_USE_MOCK=true`. Production builds reject both flags.

## Deploying

See `DEPLOY.md`. Short version: `npm run build`, then have Caddy serve `dist/`
and proxy `/me`, `/score`, `/health`, and `/ready` to uvicorn.

## The API contract

`src/types.ts` mirrors `ScoreResponse` in `app/main.py` field for field:

| Field | Shown as |
| --- | --- |
| `score` | the determination's number and the measured scale bar |
| `label` | the headline call (`protective` / `other_idp`) |
| `nearest_homolog` | "Nearest protective sequence" card |
| `top_features` | "What drove this call" — signed contribution bars |
| `features` | "Diagnostic characters" — all nine, drivers marked |
| `explanation` | "Field notes" |

If the backend adds a field, add it there first and the compiler will point at
every component that needs updating. A feature added to `features.py` renders
automatically; give it an entry in `src/features.ts` for a proper label and
bar scale.

### Two deliberate omissions

The mockups this was built from showed a confidence interval, class
probabilities, and an alignment table with percent identity and E-values.
`/score` returns none of those, so they are **gone** rather than filled with
plausible numbers. `nearest_homolog` is a cosine neighbour in ESM-2 space, not
an alignment, and the card says so.

### Errors are errors

There is no automatic fallback to fixtures when a request fails. The backend
returns 503 rather than inventing a score, because a fabricated number would
undercut the project; a UI that silently swapped in sample data on failure
would reintroduce exactly that problem. A 503 renders as "Screening is temporarily
unavailable" with the backend message and retry. It may originate from identity
keys, PostgreSQL, or model inference. Fixtures require development mode and
explicit `VITE_USE_MOCK=true`, and are labeled in the UI.

`GET /health` is checked once on load, so "the model isn't loaded" shows up
before anyone pastes a sequence and waits.

## Eval numbers live in `src/evals.ts`

They describe the model, not one sequence, so they are not in the API
response. **Edit that file by hand from `docs/EVALS.md` after each run.**

It currently holds the numbers from `docs/STATUS.md` as of 2026-10-17 — the
pre-rebuild ones, with the confound caveat rendered directly beneath the
table. That pairing is deliberate: 0.987 on the "hard" task shown on its own
is the overclaiming STATUS.md warns about. Replace both the rows and the
`caveat` string once the rebuilt negatives are re-run.

## Layout

```
src/
  types.ts                  the API contract — mirrors app/main.py
  features.ts               labels, formats and bar scales for the nine features
  evals.ts                  the two-tier table — EDIT BY HAND after each eval run
  api/client.ts             POST /score, GET /health, validation
  api/mock.ts               fixtures (opt-in) and the example sequences
  hooks/useScreen.ts        request lifecycle, discards stale responses
  styles/tokens.css         every color, font and spacing value
  styles/app.css            component classes
  components/
    Masthead.tsx            letterhead + entry number
    TardigradeMark.tsx      original line-drawn logo (inline SVG)
    SequenceInput.tsx       textarea, examples, Cmd+Enter to submit
    SpecimenHeader.tsx       scored length + the cleaned residues
    Determination.tsx        the call + score
    ScaleBar.tsx             measured rule with a threshold tick at 0.50
    ClosestRecord.tsx        nearest protective sequence
    FieldNotes.tsx           the plain-language readout
    Drivers.tsx              top 3 contributions, signs intact
    DiagnosticCharacters.tsx all nine features, drivers marked in ochre
    Reliability.tsx          the two-tier eval table + caveat
    Limitations.tsx          the honest-scope callout
    States.tsx               empty / loading / error / banners
```

## Design notes

Four decisions worth keeping if you edit the UI:

- **Ochre marks a feature that drove the call.** Neutral features are grey.
  The color is doing work; don't spend it on decoration.
- **Contributions keep their sign.** A driver arguing *against* a protective
  call is drawn left of centre in a different color. Showing magnitudes alone
  would make an objecting feature look supportive.
- **The sanity eval row is de-emphasised** so the real task reads as the
  headline, and the caveat sits under the table, not in a footnote.
- **The limitations callout sits inside the determination**, not at the bottom
  in small print.

Accessibility: every control is a real `<button>`, `<a>` or labelled
`<textarea>`; the score and feature bars carry readable labels; the shimmer
respects `prefers-reduced-motion`. Text contrast is at or above 4.5:1 on the
paper ground.

## Validation

Frontend auth/client tests, TypeScript checks, and a production build with placeholder
public auth settings pass. The HTTP integration test in `tests/test_frontend_integration.py`
connects the actual clients through Vite to FastAPI and PostgreSQL using controlled
signing keys and a stubbed model. Real Auth0 login and real inference remain separate
deployment checks. See [AUTH.md](AUTH.md) for test commands and tenant requirements.
