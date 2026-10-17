"""BLAST homology-transfer baseline — the comparison a biologist will ask for first.

Owner: Model. Needs NCBI BLAST+ (`apt install ncbi-blast+`):
    python -m tardiscreen.blast_baseline

The question this answers: does a 1990s alignment search do as well as a protein language model? If
BLAST matches ESM-2, the embeddings are not earning their place. If it does not, we can say the
embeddings capture something alignment misses — a claim we currently have no evidence for either way.

Method (standard homology transfer): for each cluster-split fold, build a BLAST database from the
TRAINING sequences only, query the held-out sequences against it, and score each query by how much
better it hits the positives than the negatives:

    score = best_bitscore_to_positives / (best_bitscore_to_positives + best_bitscore_to_negatives)

0.5 when a query hits neither class. Bitscores rather than E-values because E-values depend on
database size, which changes between folds.

Building the database from training sequences only is what keeps this honest. A database built from
all sequences would contain each query's own cluster-mates and return a meaningless ~1.0.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .evaluate import DATA_DIR, TASKS, _load, cluster_split_folds

EVALUE = 10.0            # permissive: a weak hit is still evidence, and the score weighs by bitscore
MAX_TARGETS = 50


def _require_blast() -> None:
    missing = [t for t in ("makeblastdb", "blastp") if not shutil.which(t)]
    if missing:
        raise RuntimeError(
            f"BLAST+ not found ({', '.join(missing)}). Install with: apt install ncbi-blast+")


def _write_fasta(path: Path, ids, seqs) -> None:
    with path.open("w") as fh:
        for sid, seq in zip(ids, seqs):
            fh.write(f">{sid}\n{seq}\n")


def parse_hits(tabular: str) -> dict[str, list[tuple[str, float]]]:
    """Parse `blastp -outfmt 6` into {query: [(subject, bitscore), ...]}.

    Format 6 columns: qaccver saccver pident length mismatch gapopen qstart qend sstart send
    evalue bitscore — bitscore is the last field.
    """
    hits: dict[str, list[tuple[str, float]]] = {}
    for line in tabular.splitlines():
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        try:
            bits = float(parts[11])
        except ValueError:
            continue
        hits.setdefault(parts[0], []).append((parts[1], bits))
    return hits


def score_from_hits(hits: dict[str, list[tuple[str, float]]], query_ids: list[str],
                    positive_ids: set[str]) -> np.ndarray:
    """Per-query score in [0, 1]: how much better it hits positives than negatives."""
    scores = np.full(len(query_ids), 0.5)
    for i, qid in enumerate(query_ids):
        best_pos = best_neg = 0.0
        for subject, bits in hits.get(qid, []):
            if subject in positive_ids:
                best_pos = max(best_pos, bits)
            else:
                best_neg = max(best_neg, bits)
        total = best_pos + best_neg
        if total > 0:
            scores[i] = best_pos / total
    return scores


def _blast_fold(train_ids, train_seqs, train_y, test_ids, test_seqs) -> np.ndarray:
    """Database from the training fold, query the test fold, return per-query scores."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_fasta, q_fasta = tmp / "train.fasta", tmp / "test.fasta"
        _write_fasta(db_fasta, train_ids, train_seqs)
        _write_fasta(q_fasta, test_ids, test_seqs)

        subprocess.run(["makeblastdb", "-in", str(db_fasta), "-dbtype", "prot",
                        "-out", str(tmp / "db")],
                       check=True, capture_output=True, text=True)
        proc = subprocess.run(
            ["blastp", "-query", str(q_fasta), "-db", str(tmp / "db"), "-outfmt", "6",
             "-evalue", str(EVALUE), "-max_target_seqs", str(MAX_TARGETS), "-num_threads", "4"],
            check=True, capture_output=True, text=True)

    positives = {sid for sid, lab in zip(train_ids, train_y) if lab == 1}
    return score_from_hits(parse_hits(proc.stdout), list(test_ids), positives)


def blast_cv(sub, y, groups):
    """Out-of-fold BLAST scores over the same cluster split the other models use."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    ids = sub["sequence_id"].tolist()
    seqs = sub["sequence"].tolist()
    y = np.asarray(y)
    oof = np.full(len(y), np.nan)
    rocs, prs = [], []

    for fold, (tr, te) in enumerate(cluster_split_folds(y, groups), 1):
        scores = _blast_fold([ids[i] for i in tr], [seqs[i] for i in tr], y[tr],
                             [ids[i] for i in te], [seqs[i] for i in te])
        oof[te] = scores
        if len(set(y[te])) == 2:
            rocs.append(roc_auc_score(y[te], scores))
            prs.append(average_precision_score(y[te], scores))
        print(f"    fold {fold}: {len(te)} queries against {len(tr)} training sequences")

    return (float(np.mean(rocs)), float(np.std(rocs)),
            float(np.mean(prs)), float(np.std(prs)), oof)


def main():
    import pandas as pd

    _require_blast()
    df, _ = _load()
    rows = []

    for task, (pos_label, neg_label) in TASKS.items():
        sub = df[df["label"].isin([pos_label, neg_label])]
        if task == "real" and "in_matched_set" in sub.columns:
            sub = sub[sub["in_matched_set"].astype(str).str.lower().isin(("true", "1"))]
        sub = sub.reset_index(drop=True)
        if sub.empty or sub["label"].nunique() < 2:
            print(f"[blast] task '{task}': skipped (missing a class)")
            continue

        y = (sub["label"] == pos_label).astype(int).to_numpy()
        groups = sub["cluster_id"].to_numpy()
        print(f"\n[blast] task '{task}': {pos_label}({int(y.sum())}) vs "
              f"{neg_label}({int((1 - y).sum())})")
        roc, roc_s, pr, pr_s, oof = blast_cv(sub, y, groups)
        print(f"    {'blast':>12}: ROC-AUC {roc:.3f}±{roc_s:.3f}  PR-AUC {pr:.3f}±{pr_s:.3f}")
        hit_rate = float((~np.isnan(oof) & (oof != 0.5)).mean())
        print(f"    queries with any hit: {hit_rate:.0%}")
        rows.append(dict(task=task, model="blast", roc_auc=roc, pr_auc=pr,
                         roc_auc_std=roc_s, pr_auc_std=pr_s, hit_rate=hit_rate))

    if rows:
        out = DATA_DIR / "blast_results.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"\n[blast] wrote {out}")
        print("  Read against the ESM-2 row in results_table.md. If BLAST matches it, the model is"
              "\n  doing what alignment already did; if it trails, the embeddings add something"
              "\n  alignment cannot see. Either way it is the baseline reviewers ask for.")


if __name__ == "__main__":
    main()
