"""Cluster-split cross-validation and the two-tier results table — the AI-track centerpiece.

Owner: Model. See docs/EVALS.md for the exact protocol. The single most important rule: split by
CLUSTER, never by row. A random split leaks homologs across train/test and inflates AUC.

Run from the repo root (after data + embed):
    python -m tardiscreen.evaluate

Writes data/results_table.csv and plots (data/results_auc.png, confusion_matrix.png,
feature_importance.png) for the README.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SEED = 42
N_SPLITS = 5

# The real task's negatives are matched to the positives on disorder coverage and length, so the
# comparison is restricted to the matched pairs (in_matched_set). Including unmatched positives
# would reintroduce the imbalance the matching exists to remove.
TASKS = {
    "trivial": ("protective", "ordered"),       # expect ~0.98 AUC; the sanity check
    "real": ("protective", "idp_matched"),      # the hard one: matched disordered negatives
}
MATCHED_ONLY = ("real",)
MODELS = ("composition", "biophysical", "esm2")


@dataclass
class Result:
    task: str
    model: str
    roc_auc: float
    pr_auc: float
    roc_auc_std: float
    pr_auc_std: float


def composition_vector(sequence: str):
    """20-d amino-acid composition — the baseline to beat."""
    from .features import AA, clean_sequence

    s = clean_sequence(sequence)
    n = len(s) or 1
    return [s.count(a) / n for a in AA]


# ---------------------------------------------------------------------------------------------------
# Data loading + feature matrices
# ---------------------------------------------------------------------------------------------------
def _load():
    """Return (df, emb) where df has rows that have an embedding, and emb maps id -> vector."""
    import pandas as pd

    ds = DATA_DIR / "dataset.csv"
    npz = DATA_DIR / "embeddings.npz"
    if not ds.exists():
        raise FileNotFoundError(f"{ds} not found — run `python -m tardiscreen.data` first.")
    if not npz.exists():
        raise FileNotFoundError(f"{npz} not found — run `python -m tardiscreen.embed` first.")

    df = pd.read_csv(ds, dtype=str).fillna("")
    z = np.load(npz, allow_pickle=False)
    ids = z["ids"].astype(str)
    X = z["X"]
    emb = {sid: X[i] for i, sid in enumerate(ids)}

    before = len(df)
    df = df[df["sequence_id"].isin(emb)].reset_index(drop=True)
    if len(df) < before:
        print(f"[eval] note: {before - len(df)} rows had no embedding and were dropped "
              f"(rerun embed if that's unexpected).")
    return df, emb


def _matrix(df_sub, emb, model: str) -> np.ndarray:
    from .features import FEATURE_NAMES, compute_features

    if model == "composition":
        return np.asarray([composition_vector(s) for s in df_sub["sequence"]], dtype=np.float64)
    if model == "biophysical":
        rows = [list(compute_features(s).as_dict().values()) for s in df_sub["sequence"]]
        return np.asarray(rows, dtype=np.float64)
    if model == "esm2":
        return np.vstack([emb[sid] for sid in df_sub["sequence_id"]]).astype(np.float64)
    raise ValueError(f"unknown model {model}")


def _classifier():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )


def cluster_split_folds(y, groups, n_splits: int = N_SPLITS):
    """Yield (train_idx, test_idx) with no cluster in both sides, balancing labels across folds.

    Uses StratifiedGroupKFold so each fold keeps both classes AND never splits a cluster — the
    correct protocol for homolog-rich protein data. Since our clusters are label-pure, a plain
    GroupKFold could leave a fold with only one class; stratifying avoids that.
    """
    from sklearn.model_selection import StratifiedGroupKFold

    y = np.asarray(y)
    groups = np.asarray(groups)
    n_pos_groups = len(set(groups[y == 1]))
    n_neg_groups = len(set(groups[y == 0]))
    k = max(2, min(n_splits, n_pos_groups, n_neg_groups))
    sgkf = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=SEED)
    yield from sgkf.split(np.zeros(len(y)), y, groups)


def _cv_scores(Xmat, y, groups):
    """Cluster-split CV. Returns (roc_mean, roc_std, pr_mean, pr_std, oof_proba)."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    y = np.asarray(y)
    rocs, prs = [], []
    oof = np.full(len(y), np.nan)
    for tr, te in cluster_split_folds(y, groups):
        clf = _classifier()
        clf.fit(Xmat[tr], y[tr])
        p = clf.predict_proba(Xmat[te])[:, 1]
        oof[te] = p
        if len(set(y[te])) == 2:
            rocs.append(roc_auc_score(y[te], p))
            prs.append(average_precision_score(y[te], p))
    return (float(np.mean(rocs)), float(np.std(rocs)),
            float(np.mean(prs)), float(np.std(prs)), oof)


def evaluate_all() -> list[Result]:
    """Run every (task, model) pair under cluster-split CV and return the results table."""
    df, emb = _load()
    results: list[Result] = []
    for task, (pos_label, neg_label) in TASKS.items():
        sub = df[df["label"].isin([pos_label, neg_label])]
        if task in MATCHED_ONLY and "in_matched_set" in sub.columns:
            flag = sub["in_matched_set"].astype(str).str.lower().isin(("true", "1"))
            sub = sub[flag]
        sub = sub.reset_index(drop=True)
        if sub.empty or sub["label"].nunique() < 2:
            print(f"[eval] task '{task}': skipped — needs both {pos_label} and {neg_label} rows.")
            continue
        y = (sub["label"] == pos_label).astype(int).to_numpy()
        groups = sub["cluster_id"].to_numpy()
        print(f"\n[eval] task '{task}': {pos_label}({int(y.sum())}) vs "
              f"{neg_label}({int((1 - y).sum())}), {len(set(groups))} clusters")
        for model in MODELS:
            Xmat = _matrix(sub, emb, model)
            roc, roc_s, pr, pr_s, _ = _cv_scores(Xmat, y, groups)
            results.append(Result(task, model, roc, pr, roc_s, pr_s))
            print(f"    {model:>12}: ROC-AUC {roc:.3f}±{roc_s:.3f}  PR-AUC {pr:.3f}±{pr_s:.3f}")
    return results


# ---------------------------------------------------------------------------------------------------
# Plots + interpretability (the README visuals)
# ---------------------------------------------------------------------------------------------------
def _save_plots(df, emb):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

    from .features import FEATURE_NAMES

    accent = "#2563eb"

    # Confusion matrix + feature importance for the REAL task (protective vs other_idp).
    pos_label, neg_label = TASKS["real"]
    sub = df[df["label"].isin([pos_label, neg_label])].reset_index(drop=True)
    y = (sub["label"] == pos_label).astype(int).to_numpy()
    groups = sub["cluster_id"].to_numpy()

    _, _, _, _, oof_esm = _cv_scores(_matrix(sub, emb, "esm2"), y, groups)
    mask = ~np.isnan(oof_esm)
    cm = confusion_matrix(y[mask], (oof_esm[mask] >= 0.5).astype(int))
    fig, ax = plt.subplots(figsize=(4, 4))
    ConfusionMatrixDisplay(cm, display_labels=[neg_label, pos_label]).plot(
        ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("ESM-2, real task (out-of-fold)")
    fig.tight_layout()
    fig.savefig(DATA_DIR / "confusion_matrix.png", dpi=150)
    plt.close(fig)

    # Feature importance: standardized logistic coefficients of the biophysical model.
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    Xb = _matrix(sub, emb, "biophysical")
    Xs = StandardScaler().fit_transform(Xb)
    coef = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xs, y).coef_[0]
    order = np.argsort(np.abs(coef))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh([FEATURE_NAMES[i] for i in order], coef[order], color=accent)
    ax.axvline(0, color="#64748b", lw=0.8)
    ax.set_title("Biophysical feature importance (real task)")
    ax.set_xlabel("standardized logistic coefficient  (+ → protective)")
    fig.tight_layout()
    fig.savefig(DATA_DIR / "feature_importance.png", dpi=150)
    plt.close(fig)


def _save_auc_plot(results: list[Result]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tasks = list(TASKS)
    hues = {"composition": "#94a3b8", "biophysical": "#60a5fa", "esm2": "#2563eb"}
    x = np.arange(len(tasks))
    width = 0.26
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, model in enumerate(MODELS):
        vals = [next(r.roc_auc for r in results if r.task == t and r.model == model) for t in tasks]
        errs = [next(r.roc_auc_std for r in results if r.task == t and r.model == model) for t in tasks]
        ax.bar(x + (i - 1) * width, vals, width, yerr=errs, capsize=3, label=model, color=hues[model])
    ax.axhline(0.5, color="#94a3b8", ls="--", lw=0.8, label="chance")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{t}\n({TASKS[t][0]} vs {TASKS[t][1]})" for t in tasks])
    ax.set_ylabel("ROC-AUC (cluster-split CV)")
    ax.set_ylim(0.4, 1.0)
    ax.set_title("TardiScreen: trivial vs. real task")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(DATA_DIR / "results_auc.png", dpi=150)
    plt.close(fig)


def _write_table(results: list[Result]):
    import pandas as pd

    rows = [asdict(r) for r in results]
    pd.DataFrame(rows).to_csv(DATA_DIR / "results_table.csv", index=False)

    # A markdown table for the README.
    lines = ["| task | model | ROC-AUC | PR-AUC |", "| --- | --- | --- | --- |"]
    for r in results:
        lines.append(f"| {r.task} | {r.model} | {r.roc_auc:.3f} ± {r.roc_auc_std:.3f} | "
                     f"{r.pr_auc:.3f} ± {r.pr_auc_std:.3f} |")
    (DATA_DIR / "results_table.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    t0 = time.time()
    results = evaluate_all()
    _write_table(results)
    df, emb = _load()
    _save_auc_plot(results)
    _save_plots(df, emb)
    print(f"\n[eval] wrote results_table.csv/.md + plots to {DATA_DIR} in {time.time() - t0:.1f}s")
    # Sanity: the trivial task should beat the real task — that contrast is the story.
    triv = np.mean([r.roc_auc for r in results if r.task == "trivial"])
    real = np.mean([r.roc_auc for r in results if r.task == "real"])
    print(f"[eval] mean ROC-AUC  trivial {triv:.3f}  vs  real {real:.3f}  "
          f"({'expected gap present' if triv > real else 'WARNING: no gap — check the data'})")
