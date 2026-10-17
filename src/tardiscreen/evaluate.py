"""Cluster-split cross-validation and the two-tier results table — the AI-track centerpiece.

Owner: Model. See docs/EVALS.md for the exact protocol. The single most important rule: split by
CLUSTER, never by row. A random split leaks homologs across train/test and inflates AUC.
"""

from __future__ import annotations

from dataclasses import dataclass

TASKS = {
    "trivial": ("protective", "ordered"),       # expect ~0.98 AUC
    "real": ("protective", "other_idp"),        # the hard one, expect ~0.7-0.8
}
MODELS = ("composition", "biophysical", "esm2")


@dataclass
class Result:
    task: str
    model: str
    roc_auc: float
    pr_auc: float
    roc_auc_std: float
    pr_auc_std: float


def cluster_split_folds(cluster_ids, n_splits: int = 5):
    """Yield (train_idx, test_idx) with no cluster in both sides.

    TODO: sklearn.model_selection.GroupKFold(n_splits).split(X, y, groups=cluster_ids).
    """
    raise NotImplementedError("Model owner: implement GroupKFold over cluster ids.")


def composition_vector(sequence: str):
    """20-d amino-acid composition — the baseline to beat."""
    from .features import AA, clean_sequence

    s = clean_sequence(sequence)
    n = len(s) or 1
    return [s.count(a) / n for a in AA]


def evaluate_all() -> list[Result]:
    """Run every (task, model) pair under cluster-split CV and return the results table.

    TODO (model owner): load dataset + cached embeddings/features, loop TASKS × MODELS, fit on each
    train fold, score ROC-AUC and PR-AUC on each test fold, aggregate mean ± std. Print the table and
    save it (and a confusion matrix + feature-importance plot) to data/ for the README.
    """
    raise NotImplementedError("Model owner: implement the full eval loop (see docs/EVALS.md).")


if __name__ == "__main__":
    for r in evaluate_all():
        print(f"{r.task:>8} {r.model:>12}  ROC-AUC {r.roc_auc:.3f}±{r.roc_auc_std:.3f}")
