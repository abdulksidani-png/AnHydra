# Evaluation protocol — the AI-track centerpiece

Judges on the AI track value depth and the ability to explain tradeoffs. This table is the slide.

## What to run

For **each of the two tasks**:

1. **Trivial task** — protective vs. ordered globular (sanity).
2. **Real task** — protective vs. other IDPs (the hard, meaningful one).

...compare **three models**:

| Model | What it is |
| --- | --- |
| Composition baseline | Logistic regression on amino-acid composition only. The bar to beat. |
| Biophysical features | Logistic/GBM on the interpretable features (`features.py`). Also powers the "why." |
| ESM-2 embeddings | Classifier head on frozen ESM-2 vectors (`embed.py` + `model.py`). The centerpiece. |

## Metrics

- **ROC-AUC** and **PR-AUC** (PR-AUC matters if classes are imbalanced).
- **Confusion matrix** at a chosen threshold.
- Report mean ± std across cluster-split CV folds.

## The protocol

- **Cluster-split CV** (see DATA_PLAN.md). No cluster in both train and test. This is non-negotiable.
- Freeze the ESM-2 embeddings once; don't fine-tune over the weekend (CPU, time).
- Keep the threshold choice explicit and justified.

## The result to aim for

| Task | Composition | Biophysical | ESM-2 |
| --- | --- | --- | --- |
| Trivial (vs. ordered) | ~0.98 | ~0.98 | ~0.98 |
| **Real (vs. other IDPs)** | ~0.65 | ~0.72 | **~0.78** |

(Illustrative — fill in your real numbers.) The story: the trivial task is solved by everything; the
real task is hard, and ESM-2 pulls ahead. That contrast is the depth the judges want.

## Interpretability

- **Feature importance** from the biophysical model (permutation importance or GBM gains).
- Per-sequence feature breakdown feeds the Gemini "why" readout and the results page.
