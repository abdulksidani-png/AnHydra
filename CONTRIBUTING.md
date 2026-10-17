# Contributing / Team playbook

Short, so everyone can read it in two minutes.

## Roles (assign Friday night)

- **Data** — UniProt / DisProt / MobiDB pulls, labeling, CD-HIT clustering. Owns `src/tardiscreen/data.py`.
- **Model** — ESM-2 embeddings, classifier head, feature model, evals. Owns `embed.py`, `model.py`, `evaluate.py`.
- **App** — FastAPI backend + the results UI + Vultr deploy + domain. Owns `app/`.
- **Writeup** — README, DEV post, Devpost, honest-limitations section, citations, demo recording.

(2-person team: Data+Model is one person, App+Writeup the other. Swap as needed.)

## Ground rules from the hacker guide

- ⚠️ **Write every line of code *after* hacking officially begins** (treat Fri ~8:30 PM as the safe
  start — starting early is the explicit disqualification clause). The project must be new.
- Public data and a pretrained model (ESM-2) are allowed.
- Keep a **public repo** — the AI track requires it and judges read the code.

## Workflow

- `main` stays deployable. Branch per task: `data/pull-uniprot`, `model/cluster-split`, `app/results-page`.
- Small, frequent commits with clear messages. Open a PR, get a quick 👍 from one teammate, merge.
- Don't commit data or secrets — `data/` and `.env` are gitignored.

## Definition of done (per track)

- **AI track:** two-tier eval table (trivial ≈0.98 vs. real ≈0.7–0.8), model comparison
  (ESM vs. biophysical vs. composition baseline), confusion matrix, feature importance — all in the README.
- **Easy on the Eyes:** the results page is clean, legible, and deliberate.
- **Overall:** working end-to-end demo on the real domain + a crisp 2–3 min pitch.

## Environment

```bash
cp .env.example .env     # add GEMINI_API_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
