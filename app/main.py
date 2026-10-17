"""TardiScreen web app — paste a sequence, get a score + a plain-language why.

Owner: App. FastAPI backend with a single clean results page (Easy on the Eyes track). Deploy to
Vultr, point the GoDaddy domain at it.

Run locally:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tardiscreen.explain import explain
from tardiscreen.features import compute_features

app = FastAPI(title="TardiScreen", description="Score a protein sequence for CAHS-like character.")


class ScoreRequest(BaseModel):
    sequence: str


class ScoreResponse(BaseModel):
    score: float
    label: str
    nearest_homolog: str | None
    features: dict
    explanation: str


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    # TODO (app owner): replace with a real, deliberate results page (this is the Easy-on-the-Eyes
    # track). A textarea -> POST /score -> render score + per-feature bars + the explanation.
    return """<!doctype html><html><head><meta charset="utf-8"><title>TardiScreen</title></head>
<body style="font-family:system-ui;max-width:640px;margin:4rem auto;padding:0 1rem">
<h1>TardiScreen</h1>
<p>Paste a protein sequence to screen it for CAHS-like, desiccation-protective character.</p>
<textarea id="seq" rows="6" style="width:100%"></textarea>
<button onclick="go()">Screen</button>
<pre id="out"></pre>
<script>
async function go(){
  const r = await fetch('/score',{method:'POST',headers:{'content-type':'application/json'},
    body:JSON.stringify({sequence:document.getElementById('seq').value})});
  document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
}
</script></body></html>"""


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    """Score one sequence.

    TODO (model + app owners): swap the placeholder below for tardiscreen.model.predict(req.sequence)
    once the models are trained. For now it returns the biophysical features + the offline explanation
    so the UI can be built in parallel with the model.
    """
    feats = compute_features(req.sequence).as_dict()
    top = sorted(feats.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
    placeholder_score = min(1.0, feats["low_complexity"] * 0.5 + feats["fraction_charged"])
    return ScoreResponse(
        score=round(placeholder_score, 3),
        label="protective" if placeholder_score >= 0.5 else "other_idp",
        nearest_homolog=None,
        features=feats,
        explanation=explain(placeholder_score, "protective", None,
                            [(k, float(v)) for k, v in top]),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
