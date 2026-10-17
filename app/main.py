"""AnHydra web app — paste a sequence, get a score + a plain-language why.

Owner: App. FastAPI backend; the page itself is app/static/index.html. Deployed on Vultr behind
Caddy at anhydra.work — see deploy/README.md.

Run locally:
    uvicorn app.main:app --reload

Needs data/models.joblib (`python -m tardiscreen.model`). Without it /score returns 503 rather than
inventing a number — a fabricated score would undercut the whole point of the project.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tardiscreen.explain import explain
from tardiscreen.features import AA, clean_sequence, compute_features
from tardiscreen.model import MODELS_PATH, predict

PAGE_PATH = Path(__file__).resolve().parent / "static" / "index.html"

MIN_LENGTH = 20          # below this, composition/disorder signals are meaningless
MAX_LENGTH = 10_000      # guard against someone pasting a whole proteome

app = FastAPI(title="AnHydra",
              description="Score a protein sequence for desiccation-protective family character.")


class ScoreRequest(BaseModel):
    sequence: str


class ScoreResponse(BaseModel):
    score: float
    label: str
    nearest_homolog: str | None
    top_features: list[tuple[str, float]]
    features: dict
    explanation: str


def parse_sequence(raw: str) -> str:
    """Accept raw sequence or FASTA, return a clean one-letter string, or raise 400.

    People paste FASTA straight out of UniProt, so drop '>' header lines rather than treating the
    description as residues.
    """
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    headers = [i for i, line in enumerate(lines) if line.startswith(">")]
    if len(headers) > 1 or (headers and headers[0] != 0):
        raise HTTPException(status_code=400, detail="Submit one sequence or one FASTA record at a time.")
    body = "".join("".join(line.split()) for line in lines if not line.startswith(">"))
    if set(body.upper()) - set(AA):
        raise HTTPException(status_code=400, detail="Use only the 20 standard amino-acid letters.")
    seq = clean_sequence(body)
    if len(seq) < MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least {MIN_LENGTH} amino acids (got {len(seq)} valid residues). "
                   "Paste a protein sequence or a FASTA record.",
        )
    if len(seq) > MAX_LENGTH:
        raise HTTPException(status_code=400,
                            detail=f"Sequence is {len(seq)} residues; the limit is {MAX_LENGTH}.")
    return seq


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    """Score one sequence with the trained ESM-2 model."""
    seq = parse_sequence(req.sequence)
    if not MODELS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet — run `python -m tardiscreen.model` to write "
                   "data/models.joblib, then reload.",
        )
    pred = predict(seq)
    return ScoreResponse(
        score=round(pred.score, 3),
        label=pred.label,
        nearest_homolog=pred.nearest_homolog,
        top_features=[(name, round(value, 4)) for name, value in pred.top_features],
        features=compute_features(seq).as_dict(),
        explanation=explain(pred.score, pred.label, pred.nearest_homolog, pred.top_features),
    )


@app.get("/health")
def health() -> dict:
    """Liveness + whether the app can actually score (useful after a Vultr restart)."""
    return {"status": "ok", "model_trained": MODELS_PATH.exists()}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """The results page. Read from disk per request so an edit shows up on reload in dev;
    under systemd the checkout is a read-only mount, so this is a cheap cached read either way."""
    return PAGE_PATH.read_text(encoding="utf-8")
