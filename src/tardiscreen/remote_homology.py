"""Where does the language model beat alignment? Split the test set by how much homology exists.

Owner: Model. Needs BLAST+ and a trained dataset:
    python -m tardiscreen.remote_homology

BLAST scores 0.981 on the real task against ESM-2's 0.990 — about one standard deviation apart, so
the embeddings cannot currently be claimed to beat alignment. That headline average hides the
question that matters: BLAST is strong when a close homolog exists and degrades when one does not,
which is exactly the regime a pretrained model is supposed to cover.

So this scores both methods on the SAME held-out sequences, then bins those sequences by how much
alignment signal they had (best bitscore to any training sequence) and reports accuracy per bin.

If ESM-2 wins in the low-bitscore bins, the honest claim becomes "equivalent on close homologs, and
the model holds up on remote ones" — which is both a real contribution and the case that matters in
use, since a novel sequence from an unsequenced organism has no close relatives on file. If it does
not win there, the honest claim is that the two methods are interchangeable here.
"""

from __future__ import annotations

import numpy as np

from .blast_baseline import _blast_fold, _require_blast
from .evaluate import DATA_DIR, TASKS, _classifier, _load, _matrix, cluster_split_folds

# Bitscore bins. ~50 is around the weak-but-real threshold for a short protein; 200+ is an
# unmistakable match. The lowest bin is where a language model has to earn its place.
BINS = [(0.0, 50.0, "none/very weak"), (50.0, 100.0, "weak"),
        (100.0, 200.0, "moderate"), (200.0, np.inf, "strong")]


def _auc(y, scores) -> float | None:
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y)
    return float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None


def collect(df, emb, task: str = "real"):
    """Out-of-fold BLAST scores, ESM-2 probabilities and best bitscores over one cluster split."""
    pos_label, neg_label = TASKS[task]
    sub = df[df["label"].isin([pos_label, neg_label])]
    if task == "real" and "in_matched_set" in sub.columns:
        sub = sub[sub["in_matched_set"].astype(str).str.lower().isin(("true", "1"))]
    sub = sub.reset_index(drop=True)

    y = (sub["label"] == pos_label).astype(int).to_numpy()
    groups = sub["cluster_id"].to_numpy()
    ids, seqs = sub["sequence_id"].tolist(), sub["sequence"].tolist()
    X = _matrix(sub, emb, "esm2")

    blast = np.full(len(y), np.nan)
    esm = np.full(len(y), np.nan)
    bits = np.full(len(y), np.nan)

    for fold, (tr, te) in enumerate(cluster_split_folds(y, groups), 1):
        b_scores, b_bits = _blast_fold([ids[i] for i in tr], [seqs[i] for i in tr], y[tr],
                                       [ids[i] for i in te], [seqs[i] for i in te],
                                       with_bits=True)
        blast[te], bits[te] = b_scores, b_bits

        clf = _classifier().fit(X[tr], y[tr])
        esm[te] = clf.predict_proba(X[te])[:, 1]
        print(f"    fold {fold}: {len(te)} held-out sequences scored by both methods")

    return y, blast, esm, bits


def report(y, blast, esm, bits):
    print("\n" + "=" * 78)
    print("ACCURACY BY HOW MUCH ALIGNMENT SIGNAL EXISTS")
    print("=" * 78)
    print(f"  overall: BLAST {_auc(y, blast):.3f}   ESM-2 {_auc(y, esm):.3f}   (n={len(y)})\n")
    print(f"  {'bitscore bin':>16} {'n':>6} {'%pos':>6} {'BLAST':>8} {'ESM-2':>8}  {'diff':>7}")

    for lo, hi, name in BINS:
        mask = (bits >= lo) & (bits < hi)
        n = int(mask.sum())
        if n < 20:
            print(f"  {name:>16} {n:>6}   (too few to score)")
            continue
        a_blast, a_esm = _auc(y[mask], blast[mask]), _auc(y[mask], esm[mask])
        if a_blast is None or a_esm is None:
            print(f"  {name:>16} {n:>6}   (only one class in this bin)")
            continue
        print(f"  {name:>16} {n:>6} {y[mask].mean():>5.0%} {a_blast:>8.3f} {a_esm:>8.3f}  "
              f"{a_esm - a_blast:>+7.3f}")

    weak = bits < 100.0
    if weak.sum() >= 20 and _auc(y[weak], blast[weak]) is not None:
        d = _auc(y[weak], esm[weak]) - _auc(y[weak], blast[weak])
        print(f"\n  remote-homology regime (bitscore < 100, n={int(weak.sum())}): "
              f"ESM-2 {d:+.3f} vs BLAST")
        if d > 0.03:
            print("  -> the model holds up where alignment degrades. That is the claim worth"
                  "\n     making, and it is the case a novel sequence actually presents.")
        elif d < -0.03:
            print("  -> alignment wins even on remote homologs; the embeddings are not adding"
                  "\n     anything here. Report that.")
        else:
            print("  -> the two methods are interchangeable on this data, including on remote"
                  "\n     homologs. Honest conclusion: use whichever is convenient.")


def main():
    import pandas as pd

    _require_blast()
    df, emb = _load()
    y, blast, esm, bits = collect(df, emb)
    report(y, blast, esm, bits)

    out = DATA_DIR / "remote_homology.csv"
    pd.DataFrame({"label": y, "blast_score": blast, "esm2_score": esm,
                  "best_bitscore": bits}).to_csv(out, index=False)
    print(f"\n[remote] wrote {out}")


if __name__ == "__main__":
    main()
