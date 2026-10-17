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


def length_matched_eval(df, emb):
    """Re-run the real task on a length-matched subset — the decisive test of the length artifact.

    Greedily pairs each positive with the nearest-length unused negative, giving a 1:1 set whose
    length distributions nearly coincide. Whatever AUC survives here cannot be explained by length.
    Uses the cached embeddings, so this costs seconds rather than another embedding run.
    """
    print("\n" + "=" * 78)
    print("5. LENGTH-MATCHED REAL TASK — what survives when length can't help?")
    print("=" * 78)

    sub, y, _ = _task_frame(df, "real")
    lengths = np.asarray([len(s) for s in sub["sequence"]], dtype=float)
    pos_idx = np.flatnonzero(y == 1)
    neg_idx = list(np.flatnonzero(y == 0))

    # Match longest positives first: they're the scarcest to pair against. A caliper rejects pairs
    # that aren't genuinely close — without it, a positive with no near partner still gets matched
    # to a far one and the distributions stay separated, which would fake the whole test.
    pairs: list[int] = []
    unmatched = 0
    for p in sorted(pos_idx, key=lambda i: -lengths[i]):
        if not neg_idx:
            unmatched += 1
            continue
        best = min(neg_idx, key=lambda n: abs(lengths[n] - lengths[p]))
        if abs(lengths[best] - lengths[p]) > max(20.0, 0.15 * lengths[p]):
            unmatched += 1          # no negative of comparable length exists; drop the positive
            continue
        neg_idx.remove(best)
        pairs.extend((p, best))

    if len(pairs) < 40:
        print(f"  too few matched pairs ({len(pairs) // 2}) — the length distributions barely "
              "overlap,\n  which is itself the finding: the classes are nearly separable by length "
              "alone.")
        return

    keep = np.asarray(sorted(pairs))
    matched = sub.iloc[keep].reset_index(drop=True)
    y_m = y[keep]
    groups_m = matched["cluster_id"].to_numpy()
    len_m = lengths[keep]

    print(f"  matched set: {len(matched)} sequences ({int(y_m.sum())} protective), "
          f"median length {np.median(len_m[y_m == 1]):.0f} (pos) vs "
          f"{np.median(len_m[y_m == 0]):.0f} (neg)")
    print(f"  dropped {unmatched} positives with no length-comparable negative "
          f"(caliper: 15% or 20 residues)")
    roc_before, _, _, _, _ = _cv_scores(lengths.reshape(-1, 1), y, sub["cluster_id"].to_numpy())
    roc_len, roc_len_s, _, _, _ = _cv_scores(len_m.reshape(-1, 1), y_m, groups_m)
    print(f"  length-only ROC-AUC {roc_before:.3f} unmatched -> {roc_len:.3f}±{roc_len_s:.3f} "
          "matched\n  (that is the knob being turned off; the closer to 0.50, the better the "
          "match)\n")

    for model in ("composition", "biophysical", "esm2"):
        roc, roc_s, pr, pr_s, _ = _cv_scores(_matrix(matched, emb, model), y_m, groups_m)
        print(f"    {model:>12}: ROC-AUC {roc:.3f}±{roc_s:.3f}  PR-AUC {pr:.3f}±{pr_s:.3f}")
    print("\n  Read: compare these against the unmatched table. What holds up is compositional"
          "\n  biology; what drops was length. Report both numbers, not the flattering one.")


def main():
    df, emb = _load()
    print(f"[diagnose] {len(df)} sequences with embeddings; "
          f"labels: {dict(df['label'].value_counts())}")
    check_source_confound(df)
    check_length(df)
    check_shuffled_control(df, emb)
    check_residues(df)
    length_matched_eval(df, emb)
    print("\n" + "=" * 78)
    print("Interpretation: the 'trivial' task shares a source across classes, so it is the clean"
          "\ncomparison. The 'real' task does not. Any check above that scores high on 'real' but"
          "\nlow on 'trivial' is measuring the database, not the biology.")
    print("=" * 78)


if __name__ == "__main__":
    main()
