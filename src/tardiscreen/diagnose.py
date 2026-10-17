"""Interrogate the eval result: how much of the 'real' task is biology vs. dataset artifact?

Owner: Model. Run this after evaluate.py when a number looks too good:
    python -m tardiscreen.diagnose

The real task (protective vs. other_idp) draws its positives from UniProt and its negatives from
DisProt, so label and source are perfectly confounded. Anything that differs between the two
databases — length, curation bias, which proteins get deposited — is learnable and would look
exactly like biological signal. These checks put a number on that.

Each check is reported next to the full-model ROC-AUC so the comparison is explicit.
"""

from __future__ import annotations

import numpy as np

from .evaluate import DATA_DIR, SEED, TASKS, _cv_scores, _load, _matrix, composition_vector
from .features import AA


def _task_frame(df, task: str):
    """Rows + labels + clusters for one task from TASKS."""
    pos_label, neg_label = TASKS[task]
    sub = df[df["label"].isin([pos_label, neg_label])].reset_index(drop=True)
    y = (sub["label"] == pos_label).astype(int).to_numpy()
    return sub, y, sub["cluster_id"].to_numpy()


def check_source_confound(df):
    """Cross-tabulate label against source. A clean task has both sources on both sides."""
    print("\n" + "=" * 78)
    print("1. SOURCE CONFOUND — does label give away the database?")
    print("=" * 78)
    table = df.groupby(["label", "source"]).size().unstack(fill_value=0)
    print(table.to_string())

    for task in TASKS:
        pos_label, neg_label = TASKS[task]
        pos_src = set(df.loc[df["label"] == pos_label, "source"])
        neg_src = set(df.loc[df["label"] == neg_label, "source"])
        shared = pos_src & neg_src
        verdict = ("CLEAN — both classes share a source" if shared
                   else "CONFOUNDED — source alone separates the classes")
        print(f"  {task:>8}: {pos_label}{sorted(pos_src)} vs {neg_label}{sorted(neg_src)} -> {verdict}")


def check_length(df):
    """Length is the crudest database artifact. If length alone scores high, that's not biology."""
    print("\n" + "=" * 78)
    print("2. LENGTH — can sequence length alone do the job?")
    print("=" * 78)
    for task in TASKS:
        sub, y, groups = _task_frame(df, task)
        lengths = np.asarray([len(s) for s in sub["sequence"]], dtype=np.float64)
        pos, neg = lengths[y == 1], lengths[y == 0]
        roc, roc_s, _, _, _ = _cv_scores(lengths.reshape(-1, 1), y, groups)
        print(f"  {task:>8}: median length {np.median(pos):6.0f} (pos) vs {np.median(neg):6.0f} (neg)"
              f"   length-only ROC-AUC {roc:.3f}±{roc_s:.3f}")
    print("  Read: an AUC well above 0.5 here means a single trivial number carries much of the"
          "\n  signal the big model is given credit for.")


def check_shuffled_control(df, emb):
    """Negative control: shuffle labels within the split. Anything above ~0.5 means a broken CV."""
    print("\n" + "=" * 78)
    print("3. SHUFFLED-LABEL CONTROL — is the evaluation itself sound?")
    print("=" * 78)
    rng = np.random.default_rng(SEED)
    for task in TASKS:
        sub, y, groups = _task_frame(df, task)
        shuffled = rng.permutation(y)
        roc, roc_s, _, _, _ = _cv_scores(_matrix(sub, emb, "esm2"), shuffled, groups)
        flag = "OK" if abs(roc - 0.5) < 0.1 else "CHECK"
        print(f"  {task:>8}: ESM-2 on shuffled labels ROC-AUC {roc:.3f}±{roc_s:.3f}  [{flag}]")
    print("  Read: this must sit near 0.50. Clearly ABOVE 0.5 means the cluster split is leaking"
          "\n  and every other number is inflated. Wandering below 0.5 is just noise on small"
          "\n  cluster counts — it is deviation upward that matters.")


def check_residues(df):
    """Which amino acids drive the composition baseline? Tells you if it's the expected biology."""
    print("\n" + "=" * 78)
    print("4. PER-RESIDUE SIGNAL — which letters separate the classes?")
    print("=" * 78)
    from sklearn.metrics import roc_auc_score

    for task in TASKS:
        sub, y, _ = _task_frame(df, task)
        comp = np.asarray([composition_vector(s) for s in sub["sequence"]])
        aucs = [(AA[i], roc_auc_score(y, comp[:, i])) for i in range(len(AA))]
        top = sorted(aucs, key=lambda t: abs(t[1] - 0.5), reverse=True)[:6]
        print(f"  {task:>8}: " + "  ".join(f"{a}={v:.2f}" for a, v in top))
    print("  Read: Gly/Ser/His/charged residues enriched in the positives is the expected CAHS/LEA"
          "\n  signature. Anything else leading is worth explaining.")


def main():
    df, emb = _load()
    print(f"[diagnose] {len(df)} sequences with embeddings; "
          f"labels: {dict(df['label'].value_counts())}")
    check_source_confound(df)
    check_length(df)
    check_shuffled_control(df, emb)
    check_residues(df)
    print("\n" + "=" * 78)
    print("Interpretation: the 'trivial' task shares a source across classes, so it is the clean"
          "\ncomparison. The 'real' task does not. Any check above that scores high on 'real' but"
          "\nlow on 'trivial' is measuring the database, not the biology.")
    print("=" * 78)


if __name__ == "__main__":
    main()
