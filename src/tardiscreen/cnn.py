"""A small DeepFam-style 1D CNN on raw sequence — the from-scratch row of the comparison.

Owner: Model. Needs torch:
    python -m tardiscreen.cnn

Architecture follows DeepFam (Seo et al., Bioinformatics 2018, PMC6022622): an alignment-free
text-CNN over encoded sequence — parallel convolutions of several widths, global max-pool, one fully
connected layer. Global max-pooling is what makes it alignment-free: a motif is detected wherever it
occurs, and variable-length sequences need no alignment to compare. ProtCNN (Bileschi et al., Nature
Biotechnology 2021) is the more powerful descendant, but it was trained on millions of sequences; at
~840 training sequences per fold its residual stack would only overfit, so it is the lineage here,
not the implementation.

This is NOT expected to beat ESM-2. It sees only this dataset, while ESM-2 brings representations
learned from millions of proteins. If it lands below, that gap is the finding: pretrained
representations beat from-scratch learning when labels are scarce. It runs under the same
cluster-split folds as every other row, or the comparison would not be fair.
"""

from __future__ import annotations

import numpy as np

from .evaluate import task_subset

from .evaluate import DATA_DIR, N_SPLITS, SEED, TASKS, _load, cluster_split_folds
from .features import AA

PAD, UNK = 0, 21
VOCAB = len(AA) + 2
MAX_LEN = 512                # global max-pool handles the rest; see _choose_length()
EMBED_DIM = 32
CHANNELS = 128
KERNELS = (3, 5, 7, 9)       # several widths so short and long motifs both have a detector
DROPOUT = 0.5                # heavy, deliberately: ~840 training sequences is the whole constraint
EPOCHS, PATIENCE, BATCH = 60, 8, 32
LR, WEIGHT_DECAY = 1e-3, 1e-4
VAL_CLUSTER_FRAC = 0.15

_AA_INDEX = {a: i + 1 for i, a in enumerate(AA)}


def encode(seq: str, max_len: int) -> np.ndarray:
    """Sequence -> fixed-length integer codes. 0 pads, 21 marks a non-standard residue."""
    codes = [_AA_INDEX.get(c, UNK) for c in seq.upper()[:max_len]]
    return np.array(codes + [PAD] * (max_len - len(codes)), dtype=np.int64)


def _choose_length(seqs) -> int:
    """95th-percentile length, capped. Padding everything to the longest wastes compute on padding."""
    return int(min(MAX_LEN, max(64, np.percentile([len(s) for s in seqs], 95))))


def _build(max_len: int):
    import torch
    from torch import nn

    class DeepFamSmall(nn.Module):
        def __init__(self):
            super().__init__()
            self.embed = nn.Embedding(VOCAB, EMBED_DIM, padding_idx=PAD)
            self.convs = nn.ModuleList([
                nn.Sequential(nn.Conv1d(EMBED_DIM, CHANNELS, k, padding=k // 2),
                              nn.BatchNorm1d(CHANNELS), nn.ReLU())
                for k in KERNELS])
            self.drop = nn.Dropout(DROPOUT)
            self.fc = nn.Linear(CHANNELS * len(KERNELS), 1)

        def forward(self, x):
            h = self.embed(x).transpose(1, 2)                  # (B, EMBED_DIM, L)
            pooled = [conv(h).amax(dim=2) for conv in self.convs]  # global max-pool over length
            return self.fc(self.drop(torch.cat(pooled, dim=1))).squeeze(1)

    return DeepFamSmall()


def _split_val(train_idx, groups, rng, y):
    """Choose whole validation clusters while preserving both classes on each side."""
    from sklearn.model_selection import GroupShuffleSplit

    train_idx = np.asarray(train_idx)
    groups, y = np.asarray(groups), np.asarray(y)
    n_clusters = len(np.unique(groups[train_idx]))
    if n_clusters < 4:
        raise ValueError("CNN validation requires at least four independent clusters.")
    n_validation = max(2, int(np.ceil(n_clusters * VAL_CLUSTER_FRAC)))
    splitter = GroupShuffleSplit(n_splits=256, test_size=n_validation,
                                 random_state=int(rng.integers(0, 2**31 - 1)))
    for fit, val in splitter.split(train_idx, y[train_idx], groups[train_idx]):
        if set(y[train_idx[fit]]) == {0, 1} and set(y[train_idx[val]]) == {0, 1}:
            return train_idx[fit], train_idx[val]
    raise ValueError("Cannot form cluster-disjoint CNN training/validation with both classes.")


def train_fold(X, y, train_idx, val_idx, max_len: int, verbose: bool = False):
    """Train one fold with class-balanced loss and early stopping on validation AUC."""
    import torch
    from sklearn.metrics import roc_auc_score
    from torch import nn

    if set(y[train_idx]) != {0, 1} or set(y[val_idx]) != {0, 1}:
        raise ValueError("CNN training and validation must both contain both classes.")
    torch.manual_seed(SEED)
    model = _build(max_len)
    n_pos = max(int(y[train_idx].sum()), 1)
    n_neg = max(len(train_idx) - n_pos, 1)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(n_neg / n_pos, dtype=torch.float32))
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    Xtr = torch.from_numpy(X[train_idx])
    ytr = torch.from_numpy(y[train_idx].astype(np.float32))
    Xva = torch.from_numpy(X[val_idx])
    yva = y[val_idx]

    best_auc, best_state, since_best = -1.0, None, 0
    for epoch in range(EPOCHS):
        model.train()
        order = torch.randperm(len(Xtr))
        for i in range(0, len(order), BATCH):
            batch = order[i:i + BATCH]
            opt.zero_grad()
            loss_fn(model(Xtr[batch]), ytr[batch]).backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            val_scores = torch.sigmoid(model(Xva)).numpy()
        auc = roc_auc_score(yva, val_scores) if len(set(yva)) == 2 else 0.5
        if auc > best_auc:
            best_auc, since_best = auc, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            since_best += 1
            if since_best >= PATIENCE:
                break
        if verbose and epoch % 10 == 0:
            print(f"      epoch {epoch:>3}: val AUC {auc:.3f}")

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_auc


def cnn_cv(sub, y, groups, verbose: bool = False):
    """Cluster-split CV, the same folds every other model uses."""
    import torch
    from sklearn.metrics import average_precision_score, roc_auc_score

    y = np.asarray(y)
    rng = np.random.default_rng(SEED)

    rocs, prs, oof = [], [], np.full(len(y), np.nan)
    for fold, (tr, te) in enumerate(cluster_split_folds(y, groups, N_SPLITS), 1):
        tr_fit, tr_val = _split_val(tr, groups, rng, y)
        max_len = _choose_length(sub.iloc[tr_fit]["sequence"])
        X = np.stack([encode(s, max_len) for s in sub["sequence"]])
        model, val_auc = train_fold(X, y, tr_fit, tr_val, max_len, verbose)
        model.eval()
        with torch.no_grad():
            scores = torch.sigmoid(model(torch.from_numpy(X[te]))).numpy()
        oof[te] = scores
        if len(set(y[te])) == 2:
            rocs.append(roc_auc_score(y[te], scores))
            prs.append(average_precision_score(y[te], scores))
        print(f"    fold {fold}: train {len(tr_fit)} / val {len(tr_val)} / test {len(te)}  "
              f"val AUC {val_auc:.3f}  test AUC {rocs[-1] if rocs else float('nan'):.3f}")

    return (float(np.mean(rocs)), float(np.std(rocs)),
            float(np.mean(prs)), float(np.std(prs)), oof)


def main():
    import pandas as pd

    df, _ = _load()
    rows = []
    for task, (pos_label, neg_label) in TASKS.items():
        sub = task_subset(df, task)
        if sub.empty or sub["label"].nunique() < 2:
            print(f"[cnn] task '{task}': skipped (missing a class)")
            continue

        y = (sub["label"] == pos_label).astype(int).to_numpy()
        print(f"\n[cnn] task '{task}': {pos_label}({int(y.sum())}) vs {neg_label}"
              f"({int((1 - y).sum())})")
        roc, roc_s, pr, pr_s, _ = cnn_cv(sub, y, sub["cluster_id"].to_numpy())
        print(f"    {'cnn':>12}: ROC-AUC {roc:.3f}±{roc_s:.3f}  PR-AUC {pr:.3f}±{pr_s:.3f}")
        rows.append(dict(task=task, model="cnn", roc_auc=roc, pr_auc=pr,
                         roc_auc_std=roc_s, pr_auc_std=pr_s))

    if rows:
        out = DATA_DIR / "cnn_results.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"\n[cnn] wrote {out}")
        print("  Read against ESM-2. Below it means pretrained representations beat from-scratch"
              "\n  learning at this sample size — the expected result, and worth reporting as one.")


if __name__ == "__main__":
    main()
