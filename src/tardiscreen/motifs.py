"""What did the CNN actually learn? Read the motifs back out of its filters.

Owner: Model. Needs torch:
    python -m tardiscreen.motifs

Each convolution filter is a pattern detector that slides along the sequence, and during training
each one settles on something to look for. This asks every filter what makes it fire hardest, then
reads out the amino-acid patterns it found — the interpretability angle DeepFam (Seo et al. 2018)
was built around.

Filters are ranked by how well their activation separates protective from non-protective sequences,
not by raw strength: a filter that fires loudly on everything explains nothing. The reported motifs
come from the strongest-activating protective sequences for each discriminative filter.

The point is corroboration. The composition analysis found glycine enriched and bulky hydrophobics
depleted; the per-residue AUCs said the same. If filters trained from raw sequence, with no
hand-designed features and no prior biology, converge on Gly/Ser repeats and alternating charges,
then three independent methods agree — which is a much stronger claim than any one of them alone.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from .cnn import DATA_DIR, KERNELS, SEED, _build, _choose_length, _split_val, encode, train_fold
from .evaluate import TASKS, _load
from .features import AA

TOP_FILTERS = 12         # per kernel width, ranked by discriminative power
TOP_SEQUENCES = 40       # strongest-activating positives used to read a filter's motif
MIN_AUC = 0.60           # below this a filter is not separating the classes and says nothing

_INDEX_AA = {i + 1: a for i, a in enumerate(AA)}


def decode(codes) -> str:
    """Integer codes back to letters. '-' marks padding, 'X' a non-standard residue."""
    return "".join(_INDEX_AA.get(int(c), "-" if int(c) == 0 else "X") for c in codes)


def filter_activations(model, X, batch: int = 64):
    """(N, n_filters) pooled activations and (N, n_filters) argmax positions, per kernel block."""
    import torch

    model.eval()
    pooled_blocks, argmax_blocks = [], []
    with torch.no_grad():
        for conv in model.convs:
            pooled, positions = [], []
            for i in range(0, len(X), batch):
                h = model.embed(torch.from_numpy(X[i:i + batch])).transpose(1, 2)
                acts = conv(h)                       # (B, C, L)
                pooled.append(acts.amax(dim=2).numpy())
                positions.append(acts.argmax(dim=2).numpy())
            pooled_blocks.append(np.concatenate(pooled))
            argmax_blocks.append(np.concatenate(positions))
    return pooled_blocks, argmax_blocks


def consensus(kmers: list[str]) -> str:
    """Most common residue at each position — a one-line stand-in for a sequence logo."""
    if not kmers:
        return ""
    width = max(len(k) for k in kmers)
    out = []
    for i in range(width):
        column = [k[i] for k in kmers if len(k) > i and k[i] not in "-X"]
        out.append(Counter(column).most_common(1)[0][0] if column else ".")
    return "".join(out)


def motifs_for_block(X, y, pooled, argmax, width: int):
    """Rank this block's filters by class separation, then read each one's motif."""
    from sklearn.metrics import roc_auc_score

    aucs = np.array([roc_auc_score(y, pooled[:, f]) if len(set(y)) == 2 else 0.5
                     for f in range(pooled.shape[1])])
    order = np.argsort(-aucs)[:TOP_FILTERS]
    half = width // 2
    rows = []

    for f in order:
        if aucs[f] < MIN_AUC:
            continue
        pos_idx = np.flatnonzero(y == 1)
        strongest = pos_idx[np.argsort(-pooled[pos_idx, f])[:TOP_SEQUENCES]]
        kmers = []
        for i in strongest:
            centre = int(argmax[i, f])
            window = X[i, max(0, centre - half): centre + half + 1]
            text = decode(window)
            if text.count("-") <= width // 3:          # mostly padding means nothing was found
                kmers.append(text)
        if not kmers:
            continue
        rows.append(dict(width=width, filter=int(f), auc=float(aucs[f]),
                         consensus=consensus(kmers),
                         examples=" ".join(dict.fromkeys(kmers[:5]))))
    return rows


def main():
    import pandas as pd

    df, _ = _load()
    pos_label, neg_label = TASKS["real"]
    sub = df[df["label"].isin([pos_label, neg_label])]
    if "in_matched_set" in sub.columns:
        sub = sub[sub["in_matched_set"].astype(str).str.lower().isin(("true", "1"))]
    sub = sub.reset_index(drop=True)

    y = (sub["label"] == pos_label).astype(int).to_numpy()
    max_len = _choose_length(sub["sequence"])
    X = np.stack([encode(s, max_len) for s in sub["sequence"]])
    print(f"[motifs] training on all {len(sub)} sequences ({int(y.sum())} protective), "
          f"length {max_len}")

    # One model on everything — this is for reading filters, not for measuring accuracy, so there
    # is no held-out test set. Early stopping still uses clusters held out of training.
    rng = np.random.default_rng(SEED)
    groups = sub["cluster_id"].to_numpy()
    fit_idx, val_idx = _split_val(np.arange(len(y)), groups, rng)
    model, val_auc = train_fold(X, y, fit_idx, val_idx, max_len)
    print(f"[motifs] trained (validation AUC {val_auc:.3f}); reading filters\n")

    pooled_blocks, argmax_blocks = filter_activations(model, X)
    rows = []
    for width, pooled, argmax in zip(KERNELS, pooled_blocks, argmax_blocks):
        block = motifs_for_block(X, y, pooled, argmax, width)
        rows.extend(block)
        print(f"=== kernel width {width} — {len(block)} filters above AUC {MIN_AUC} ===")
        for r in block[:6]:
            print(f"  filter {r['filter']:>3}  AUC {r['auc']:.3f}  consensus {r['consensus']:<10}"
                  f"  e.g. {r['examples']}")
        print()

    if not rows:
        print("[motifs] no filter separated the classes above the threshold.")
        return

    out = pd.DataFrame(rows).sort_values("auc", ascending=False)
    out.to_csv(DATA_DIR / "cnn_motifs.csv", index=False)
    print(f"[motifs] wrote {DATA_DIR / 'cnn_motifs.csv'} ({len(out)} filters)")

    letters = Counter("".join(out["consensus"]).replace(".", ""))
    total = sum(letters.values()) or 1
    top = "  ".join(f"{a}:{n / total:.0%}" for a, n in letters.most_common(8))
    print(f"\n[motifs] residues across all learned motifs: {top}")
    print("  Read: Gly/Ser-rich and charged patterns here mean the network found the CAHS/LEA"
          "\n  signature from raw sequence alone — independent of the composition analysis and of"
          "\n  the hand-designed features, which reported the same thing.")


if __name__ == "__main__":
    main()
