"""TardiScreen web app — paste a sequence, get a score + a plain-language why.

Owner: App. FastAPI backend with a single clean results page (Easy on the Eyes track). Deploy to
Vultr, point the GoDaddy domain at it.

Run locally:
    uvicorn app.main:app --reload

Needs data/models.joblib (`python -m tardiscreen.model`). Without it /score returns 503 rather than
inventing a number — a fabricated score would undercut the whole point of the project.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tardiscreen.explain import explain
from tardiscreen.features import AA, clean_sequence, compute_features
from tardiscreen.model import MODELS_PATH, predict

MIN_LENGTH = 20          # below this, composition/disorder signals are meaningless
MAX_LENGTH = 10_000      # guard against someone pasting a whole proteome

app = FastAPI(title="TardiScreen", description="Score a protein sequence for CAHS-like character.")


class ScoreRequest(BaseModel):
    sequence: str


class ScoreResponse(BaseModel):
    score: float
    label: str
    nearest_homolog: str | None
    top_features: list[tuple[str, float]]
    features: dict
    explanation: str
    # The biophysical model's own probability. `score` is ESM-2's, but `top_features` decompose the
    # biophysical model, so the drivers explain a surrogate. Exposing both lets the UI (and a judge)
    # see whether the surrogate agreed. Optional so an older trained bundle still serializes.
    bio_score: float | None = None
    models_agree: bool | None = None


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
    features = compute_features(seq).as_dict()
    agree = None if pred.bio_score is None else (pred.bio_score >= 0.5) == (pred.score >= 0.5)
    return ScoreResponse(
        score=round(pred.score, 3),
        label=pred.label,
        nearest_homolog=pred.nearest_homolog,
        top_features=[(name, round(value, 4)) for name, value in pred.top_features],
        features=features,
        # Hand the readout the measured values as well as the contributions, so it can't restate a
        # contribution as a quantity, plus the surrogate's score so a disagreement gets declared.
        explanation=explain(pred.score, pred.label, pred.nearest_homolog, pred.top_features,
                            features=features, bio_score=pred.bio_score),
        bio_score=None if pred.bio_score is None else round(pred.bio_score, 3),
        models_agree=agree,
    )


@app.get("/health")
def health() -> dict:
    """Liveness + whether the app can actually score (useful after a Vultr restart)."""
    return {"status": "ok", "model_trained": MODELS_PATH.exists()}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TardiScreen</title>
<style>
  :root {
    --bg: #fbfaf8; --panel: #ffffff; --ink: #1a1a1a; --muted: #6b7280; --line: #e5e3df;
    --accent: #2563eb; --pos: #2563eb; --neg: #b45309; --radius: 10px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14161a; --panel: #1b1e24; --ink: #ecebe8; --muted: #9aa1ab; --line: #2b2f37;
      --accent: #6ea8ff; --pos: #6ea8ff; --neg: #e0a052;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  main { max-width: 720px; margin: 0 auto; padding: 48px 20px 80px; }
  header { margin-bottom: 32px; }
  h1 { font-size: 28px; letter-spacing: -0.02em; margin: 0 0 6px; font-weight: 650; }
  .tagline { color: var(--muted); margin: 0; }
  .panel {
    background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
    padding: 20px; margin-bottom: 20px;
  }
  label { display: block; font-weight: 600; font-size: 14px; margin-bottom: 8px; }
  textarea {
    width: 100%; min-height: 128px; resize: vertical; padding: 12px;
    border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--ink);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; line-height: 1.5;
  }
  textarea:focus { outline: 2px solid var(--accent); outline-offset: 1px; border-color: var(--accent); }
  .row { display: flex; gap: 12px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
  button {
    background: var(--accent); color: #fff; border: 0; border-radius: 8px;
    padding: 10px 18px; font-size: 15px; font-weight: 600; cursor: pointer;
  }
  button:hover:not(:disabled) { filter: brightness(1.08); }
  button:disabled { opacity: 0.55; cursor: progress; }
  .link { background: none; color: var(--accent); padding: 0; font-weight: 500; font-size: 14px; }
  #results[hidden] { display: none; }
  .score-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
  .score-num { font-size: 40px; font-weight: 680; letter-spacing: -0.03em; line-height: 1.1; }
  .call { font-size: 13px; font-weight: 650; padding: 4px 10px; border-radius: 999px;
          border: 1px solid var(--line); color: var(--muted); white-space: nowrap; }
  .meter { height: 8px; background: var(--line); border-radius: 999px; margin: 14px 0 6px;
           overflow: hidden; }
  .meter > span { display: block; height: 100%; background: var(--accent); border-radius: 999px;
                  transition: width 0.4s ease; }
  .scale { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted);
       margin: 0 0 14px; font-weight: 650; }
  .driver { margin-bottom: 12px; }
  .driver-top { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 4px; }
  .driver-name { font-family: ui-monospace, Menlo, monospace; font-size: 13px; }
  .driver-val { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 13px; }
  .bar { height: 6px; background: var(--line); border-radius: 999px; position: relative; }
  .bar > span { position: absolute; top: 0; height: 100%; border-radius: 999px; }
  .bar > span.p { left: 50%; background: var(--pos); }
  .bar > span.n { right: 50%; background: var(--neg); }
  .axis { font-size: 11px; color: var(--muted); display: flex; justify-content: space-between;
          margin-top: 8px; }
  p.explain { margin: 0; }
  dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;
       margin: 0; }
  dt { font-size: 12px; color: var(--muted); font-family: ui-monospace, Menlo, monospace; }
  dd { margin: 2px 0 0; font-variant-numeric: tabular-nums; font-size: 15px; }
  .homolog { font-family: ui-monospace, Menlo, monospace; }
  .note { font-size: 13px; color: var(--muted); border-left: 2px solid var(--line);
          padding-left: 12px; }
  .error { color: var(--neg); font-size: 14px; margin: 12px 0 0; }
  footer { color: var(--muted); font-size: 13px; text-align: center; margin-top: 8px; }
  a { color: var(--accent); }
</style>
</head>
<body>
<main>
  <header>
    <h1>TardiScreen</h1>
    <p class="tagline">Score a protein sequence for CAHS-like, desiccation-protective character.</p>
  </header>

  <div class="panel">
    <label for="seq">Protein sequence <span style="font-weight:400;color:var(--muted)">(raw or FASTA)</span></label>
    <textarea id="seq" spellcheck="false" placeholder="MSGSGSGKEKEKDKDKGSGSGSHGHGSGSEKEKDKDK..."></textarea>
    <div class="row">
      <button id="go">Screen sequence</button>
      <button class="link" id="demo" type="button">Use an example</button>
    </div>
    <p class="error" id="error" hidden></p>
  </div>

  <div id="results" hidden>
    <div class="panel">
      <div class="score-head">
        <div>
          <h2>Protection-family score</h2>
          <div class="score-num" id="score">—</div>
        </div>
        <span class="call" id="call"></span>
      </div>
      <div class="meter"><span id="meter" style="width:0%"></span></div>
      <div class="scale"><span>0 · unlike protective families</span><span>1 · very like them</span></div>
    </div>

    <div class="panel">
      <h2>What drove this score</h2>
      <div id="drivers"></div>
      <div class="axis"><span>← less protective-like</span><span>more protective-like →</span></div>
    </div>

    <div class="panel">
      <h2>Readout</h2>
      <p class="explain" id="explanation"></p>
    </div>

    <div class="panel">
      <h2>Nearest known protective homolog</h2>
      <p class="homolog" id="homolog"></p>
    </div>

    <div class="panel">
      <h2>Biophysical features</h2>
      <dl id="features"></dl>
    </div>

    <p class="note">
      TardiScreen predicts whether a sequence <em>belongs to</em> the desiccation-protective families
      (CAHS / LEA / related anhydrobiosis IDPs). It does <strong>not</strong> predict how much a
      protein protects. Use it to prioritize candidates for wet-lab testing, not as an efficacy claim.
    </p>
  </div>

  <footer>
    <a href="https://github.com/abdulksidani-png/tardiscreen">Source &amp; evaluation methodology</a>
  </footer>
</main>

<script>
const EXAMPLE = "MSGSGSGKEKEKDKDKGSGSGSHGHGSGSEKEKDKDKGSGSGSGHKGHGSGSEKEKDKDKGSGSGSHGHGSGSEKEKDKDKGSGSGSGHKGHGSGS";
const $ = (id) => document.getElementById(id);

$("demo").addEventListener("click", () => { $("seq").value = EXAMPLE; $("seq").focus(); });
$("go").addEventListener("click", run);
$("seq").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run();
});

function showError(message) {
  $("error").textContent = message;
  $("error").hidden = false;
  $("results").hidden = true;
}

async function run() {
  const sequence = $("seq").value.trim();
  $("error").hidden = true;
  if (!sequence) { showError("Paste a sequence first."); return; }

  const button = $("go");
  button.disabled = true;
  button.textContent = "Scoring…";
  try {
    const response = await fetch("/score", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sequence }),
    });
    const data = await response.json();
    if (!response.ok) { showError(data.detail || "Scoring failed."); return; }
    render(data);
  } catch (err) {
    showError("Could not reach the server. Is it still running?");
  } finally {
    button.disabled = false;
    button.textContent = "Screen sequence";
  }
}

function render(data) {
  $("score").textContent = data.score.toFixed(2);
  $("meter").style.width = (data.score * 100).toFixed(1) + "%";
  $("call").textContent = data.label === "protective"
    ? "protective family" : "not protective family";

  // Signed contribution bars, scaled against the largest absolute driver.
  const max = Math.max(...data.top_features.map(([, v]) => Math.abs(v)), 1e-9);
  $("drivers").innerHTML = data.top_features.map(([name, value]) => {
    const width = (Math.abs(value) / max) * 50;
    const side = value >= 0 ? "p" : "n";
    return `<div class="driver">
      <div class="driver-top">
        <span class="driver-name">${name}</span>
        <span class="driver-val">${value >= 0 ? "+" : ""}${value.toFixed(2)}</span>
      </div>
      <div class="bar"><span class="${side}" style="width:${width}%"></span></div>
    </div>`;
  }).join("");

  $("explanation").textContent = data.explanation;
  $("homolog").textContent = data.nearest_homolog
    ? data.nearest_homolog
    : "No close match among the training positives.";
  $("features").innerHTML = Object.entries(data.features).map(([name, value]) =>
    `<div><dt>${name}</dt><dd>${typeof value === "number" ? value.toFixed(3) : value}</dd></div>`
  ).join("");

  $("results").hidden = false;
}
</script>
</body>
</html>"""
