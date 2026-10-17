# Project status — live working document

Last updated: 2026-10-17. Read this before starting work. It says what is true right now, what is in
flight, and which files are yours.

## The project in one paragraph

TardiScreen scores a protein sequence for CAHS/LEA-like, desiccation-protective character and
explains why. It is a **family / triage classifier, not an efficacy predictor** — it answers "does
this look like the protective families?", never "how well does this protect?". Keep that framing in
every piece of writing; overclaiming is the fastest way to lose credibility with a technical judge.

## Where things stand

| Stage | State |
| --- | --- |
| Data | Built, then found confounded — being rebuilt (see below) |
| Embeddings | Done. ESM-2 `esm2_t12_35M_UR50D`, mean-pooled, frozen, D=480, 4277 sequences |
| Model | Trained. `data/models.joblib` exists on the server and works |
| Evals | Run, then interrogated — numbers below are real but the task was flawed |
| App | Code complete: real scoring, Gemini explanation, results page. **Not deployed** |
| Deploy | Not started |
| Writeup | Not started |

## What happened with the evals (the important part)

The eval uses a **two-tier** design, deliberately:

- `trivial` = protective vs. **ordered** (structured proteins). Expected easy — it is the sanity
  check that the pipeline can learn anything at all.
- `real` = protective vs. **other disordered** proteins. This is the meaningful question, because
  CAHS/LEA are themselves intrinsically disordered — comparing them only to folded proteins just
  re-learns "disordered vs. folded", which is a solved problem.

Results (ROC-AUC, 5-fold cluster-split CV, split by CD-HIT 40% cluster so homologs cannot straddle
train/test):

| task | composition | biophysical | esm2 |
| --- | --- | --- | --- |
| trivial | 0.912 | 0.886 | 0.997 |
| real | 0.872 | 0.851 | **0.987** |

The `real` task was predicted to land at 0.7–0.8. It came back at 0.987. **We treated that as a red
flag rather than a win**, and investigated. Findings, in order:

1. **The validation is sound.** ESM-2 on randomly shuffled labels scores 0.478 / 0.523 — sitting on
   0.50, exactly as it must. No leakage in the cluster-split machinery. Every measured number is
   trustworthy.
2. **Source is confounded.** All positives come from UniProt, all `other_idp` negatives from DisProt.
   In the real task, "is this protective?" and "is this from UniProt?" are the same question. (The
   trivial task draws both classes from UniProt and is clean.)
3. **Length is not the explanation.** Length alone scores 0.770 on the real task (medians 191 vs.
   384 residues). After 1:1 length-matching, length-only drops to 0.514 and ESM-2 **holds at 0.990**.
   The biophysical model falls 0.851 → 0.733, which is the expected behaviour since length is one of
   its nine features — the models each moved the way their construction predicts, so the test has
   teeth.
4. **The negatives are the problem.** DisProt curates disordered *regions inside* proteins, not whole
   disordered proteins. Of 1604 negatives, only 447 reach 30% disorder coverage, 246 reach 50%, 149
   reach 70%. About 1150 sit below 30% — they are folded proteins with a floppy tail. So the "hard"
   task was substantially re-measuring folded-vs-unfolded, i.e. a version of the trivial task.

**This is a dataset design flaw, not a bug.** The code is correct, the labels are correct, the
validation is correct. The negative set just did not mean what it was supposed to mean.

## What is being done about it

Rebuilding the negatives as genuinely, fully disordered, non-protective proteins:

- Sourced from **UniProt** rather than MobiDB, because the positives are UniProt — same source on
  both sides removes the source confound in the same change
- Filtered by disorder coverage computed from UniProt `Region: "Disordered"` annotations
- Protective families excluded (CAHS / LEA / dehydrin / desiccation / anhydrobiosis terms)
- Length-matched to the positives
- Re-clustered with CD-HIT, then only the *new* sequences get embedded (the cache is keyed by
  `sequence_id`, so the existing 4277 are untouched)

One guard worth understanding: filtering negatives on disorder while leaving the positives unfiltered
would let disorder separate the classes *again, backwards* — the model would learn "less disordered
⇒ protective" and return another meaningless high score. So coverage is being measured for the
**positives too**, and if the distributions differ the negatives get matched to them rather than
hard-thresholded.

## Lane ownership — do not cross these

| Area | Files | Owner |
| --- | --- | --- |
| Data + model pipeline | `src/tardiscreen/` | Abdul + Claude |
| Deploy / infra | systemd, Caddy, `.env`, DNS | Teammate 1 |
| Writeup / submission | `README.md`, `docs/` (except this file) | Teammate 2 |

**Nobody but the data owner runs `data.py`, `embed.py`, or `coverage.py` on the server.** They
regenerate `dataset.csv` and `embeddings.npz`; two people running them at once corrupts the run.

`main` moves frequently right now — `git pull` before you start and before every PR.

## Running things

```bash
cd ~/tardiscreen && source .venv/bin/activate

uvicorn app.main:app --reload       # the web app (needs data/models.joblib)
python -m tardiscreen.evaluate      # two-tier table + plots
python -m tardiscreen.diagnose      # the confound checks described above
```

The app returns **503 rather than a fabricated score** if `models.joblib` is missing. That is
deliberate: a made-up number would undercut the entire point of the project.

## Honest framing for the writeup

The story is not "we got 0.99". It is:

> We got 0.987 on the task we had designed to be hard, did not believe it, and went looking. The
> cross-validation held up. Length did not explain it. What did was our negative set: proteins
> labelled "disordered" that are mostly folded. We rebuilt it and re-ran.

That is a stronger submission than a clean number, and it is true. Report the before and after, not
the flattering one.
