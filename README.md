# TardiScreen

**Paste a protein sequence → get a desiccation-protection score + a plain-language "why."**

TardiScreen is a machine-learning screening tool that scores any amino-acid sequence for
**CAHS-like, desiccation-protective character** and explains the biophysical signatures behind
the score. It's built as a triage aid for biopreservation research — prioritizing which sequences
are worth expressing and testing in the lab (stabilizing vaccines, clotting factors, and reagents
without a cold chain).

Built for **SwampHacks XII** (Oct 16–18, 2026, Reitz Union, University of Florida).

> **Honest framing (read this first):** TardiScreen is a **family / character classifier and triage
> tool**, not a validated efficacy predictor. It classifies whether a sequence belongs to the
> protective families (CAHS / LEA / other anhydrobiosis proteins) and surfaces its signatures — it
> does **not** claim to predict how *much* a protein protects. See [Honest limitations](#honest-limitations).

---

## The pipeline

| 1 · Data | 2 · Embed | 3 · Model | 4 · Explain | 5 · App |
| --- | --- | --- | --- | --- |
| Protective IDPs (CAHS/LEA) vs. *other* IDPs — the hard, real question | ESM-2 protein language model → sequence vectors (small model, CPU) | Classifier head + a parallel interpretable biophysical model | Feature importance + Gemini plain-language readout | Clean web UI on a real domain, hosted on Vultr |

The two-model design is deliberate: the ESM-2 embedding model is the centerpiece, and the
interpretable biophysical-features model is both the "why" **and** a fallback that still runs if the
embedding pipeline stalls.

---

## Why "protective vs. other disordered" is the whole game

"Is this protein disordered?" is trivial — composition alone solves it (expect ≈0.98 AUC).
"Among disordered proteins, which ones *protect*?" is the question a lab actually has, and it's
genuinely hard (expect ≈0.7–0.8 AUC). **We report both tasks** — that contrast is a better result
than either number alone, and it's where ESM-2 can beat a plain composition baseline.

---

## Repo layout

```
tardiscreen/
├── README.md               ← you are here
├── CONTRIBUTING.md         ← team roles + workflow (read before you start)
├── requirements.txt
├── docs/
│   ├── GAME_PLAN.md        ← the full weekend timeline
│   ├── DATA_PLAN.md        ← where the data comes from + the cluster-split rule
│   └── EVALS.md            ← the evaluation protocol (our AI-track centerpiece)
├── data/                   ← raw/processed data lives here (gitignored, see data/README.md)
├── src/tardiscreen/
│   ├── data.py             ← pull + label UniProt / DisProt / MobiDB sequences
│   ├── features.py         ← interpretable biophysical features  (implemented)
│   ├── embed.py            ← ESM-2 embeddings
│   ├── model.py            ← classifier head + feature model
│   ├── evaluate.py         ← cluster-split CV, ROC/PR-AUC, confusion matrix
│   └── explain.py          ← Gemini plain-language "why this score"
├── app/
│   └── main.py             ← FastAPI: sequence in → score + explanation out
└── notebooks/              ← scratch / exploration
```

## Quick start

```bash
# 1. Python 3.10+ recommended
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Pull and label the data (see docs/DATA_PLAN.md)
python -m tardiscreen.data

# 3. Compute embeddings + features
python -m tardiscreen.embed
python -m tardiscreen.features

# 4. Train + evaluate (cluster-split CV)
python -m tardiscreen.evaluate

# 5. Run the app locally
uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` for the explanation feature.

## Sponsor stack (what we're opting into)

- **Vultr** — host the app, point the domain at it (no GPU needed; ESM-2 small embeds on CPU).
- **Gemini API** — generates the plain-language "why this score" readout.
- **GoDaddy Registry** — demo on a real `tardiscreen.*` domain.
- **DEV Writing** — the end-of-weekend write-up.

Tracks we're targeting: **Most Creative Use of AI**, **Overall / Hack of the Year**, **Easy on the Eyes**.

## Honest limitations

- **No large efficacy dataset exists.** We classify family membership and surface signatures; we do
  not predict protection *strength*.
- **The model learns family signatures, not proven function.** Sequence similarity to CAHS/LEA
  correlates with — but doesn't equal — real protective function. Output = "prioritize these for wet-lab testing."
- **Labels are heterogeneous.** CAHS, LEA, and others protect via different mechanisms (gelation,
  vitrification, membrane support). One score flattens that; we show per-feature breakdowns to compensate.
- **Some labels may themselves be predictions.** We prefer UniProt entries with **experimental
  evidence codes** over keyword-only annotations, and say so.

## References

Keep real CAHS / anhydrobiosis literature (Nature, Wiley, Frontiers, PubMed) cited here before
submission — citing real sources strengthens both the AI and Overall judging. _(Add links as you go.)_

## License

MIT — see [LICENSE](LICENSE).
