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
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tardiscreen.explain import explain
from tardiscreen.features import AA, clean_sequence, compute_features
from tardiscreen.model import MODELS_PATH, predict, load_bundle
from app.auth import KeyCache, TokenVerifier, authenticated_user
from app.database import UserStore, database_engine
from app.logging_safety import install_redaction
from app.settings import Settings

PAGE_PATH = Path(__file__).resolve().parent / "static" / "index.html"

MIN_LENGTH = 20          # below this, composition/disorder signals are meaningless
MAX_LENGTH = 1022        # ESM-2 token budget: 1024 minus BOS/EOS; never silently truncate

@asynccontextmanager
async def lifespan(application):
    install_redaction()
    settings = Settings.from_env()
    application.state.settings = settings
    engine = None
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        if not settings.anonymous:
            engine = database_engine(settings.database_url)
            application.state.users = UserStore(engine)
            application.state.verifier = TokenVerifier(settings, KeyCache(settings.issuer, client))
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()


class ConfiguredCORS:
    """Read validated startup origins without validating secrets during module import."""
    def __init__(self, app):
        self.app = app
        self.middleware = None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            settings = getattr(scope["app"].state, "settings", None)
            if settings is not None:
                if self.middleware is None:
                    self.middleware = CORSMiddleware(self.app, allow_origins=list(settings.cors_origins),
                        allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
                return await self.middleware(scope, receive, send)
        return await self.app(scope, receive, send)


app = FastAPI(title="AnHydra", lifespan=lifespan,
              description="Score a protein sequence for desiccation-protective family character.")
app.add_middleware(ConfiguredCORS)


class UserResponse(BaseModel):
    id: UUID
    display_name: str | None
    email: str | None
    email_verified: bool
    created_at: datetime


@app.get("/me", response_model=UserResponse)
def me(user=Depends(authenticated_user)):
    return user


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
def score(req: ScoreRequest, user=Depends(authenticated_user)) -> ScoreResponse:
    """Score one sequence with the trained ESM-2 model."""
    seq = parse_sequence(req.sequence)
    if not MODELS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet — run `python -m tardiscreen.model` to write "
                   "data/models.joblib, then reload.",
        )
    try:
        pred = predict(seq)
    except Exception as exc:
        logging.getLogger(__name__).error("Scoring unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Scoring is unavailable. Ask the operator to check the model and encoder runtime.") from exc
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
    """Liveness and artifact presence only; use /ready and a score for readiness."""
    return {"status": "ok", "model_trained": MODELS_PATH.exists()}


@app.get("/ready")
def ready() -> dict:
    """Validate the model and installed runtime without downloading encoder weights."""
    from importlib.util import find_spec

    try:
        load_bundle()
        if any(find_spec(name) is None for name in ("torch", "transformers")):
            raise ValueError("Missing encoder runtime")
    except Exception as exc:
        logging.getLogger(__name__).warning("Readiness unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Model or encoder runtime unavailable.") from exc
    return {"status": "ok", "inference_verified": False}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """The results page. Read from disk per request so an edit shows up on reload in dev;
    under systemd the checkout is a read-only mount, so this is a cheap cached read either way."""
    return PAGE_PATH.read_text(encoding="utf-8")
