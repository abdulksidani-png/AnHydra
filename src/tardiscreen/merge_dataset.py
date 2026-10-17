"""Merge the matched negatives into dataset.csv and re-cluster. This is the step that rewrites data.

Owner: Data. Run after build_negatives.py and match_negatives.py:
    python -m tardiscreen.merge_dataset

What it does:
  - keeps the protective positives and the ordered controls
  - DROPS the old DisProt `other_idp` negatives (median disorder coverage 0.15 — folded proteins
    carrying a floppy region, which is what made the "real" task re-measure folded-vs-unfolded)
  - adds the matched negatives as `idp_matched`
  - re-clusters everything together with CD-HIT so the new sequences get cluster ids on the same
    footing, and any cross-label homolog is resolved by the existing priority rule
  - marks the matched pairs with `in_matched_set` so the evaluation can restrict the hard task to
    them while the trivial task still uses every positive

The previous dataset.csv is copied to dataset.prev.csv first. It is gitignored and took a long pull
to produce, so it is never simply overwritten.

Embeddings are keyed by sequence_id, so only the newly added sequences need embedding afterwards.
"""

from __future__ import annotations

import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATASET = DATA_DIR / "dataset.csv"
BACKUP = DATA_DIR / "dataset.prev.csv"
NEW_LABEL = "idp_matched"
DROP_LABEL = "other_idp"


def main(identity: float = 0.4):
    import pandas as pd

    from .data import PRIORITY, Record, _clean_seq, cluster_sequences

    for p in (DATASET, DATA_DIR / "matched_negatives.csv", DATA_DIR / "matched_positives.csv"):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found — run the earlier step first.")

    df = pd.read_csv(DATASET, dtype=str).fillna("")
    neg = pd.read_csv(DATA_DIR / "matched_negatives.csv")
    matched_pos_ids = set(pd.read_csv(DATA_DIR / "matched_positives.csv",
                                      dtype=str)["sequence_id"])
    print(f"[merge] existing dataset: {dict(df['label'].value_counts())}")
    print(f"[merge] matched negatives: {len(neg)}   matched positives: {len(matched_pos_ids)}")

    keep = df[df["label"] != DROP_LABEL].copy()
    print(f"[merge] dropping {len(df) - len(keep)} old '{DROP_LABEL}' rows")

    # The new negatives, as records in the same shape as the rest of the table.
    new_rows = pd.DataFrame({
        "sequence_id": neg["sequence_id"].astype(str),
        "sequence": neg["sequence"].astype(str).map(_clean_seq),
        "label": NEW_LABEL,
        "source": "uniprot",
        "evidence_code": "disorder-annotated",
        "cluster_id": "",
    })
    new_rows = new_rows[new_rows["sequence"].str.len() > 0]
    combined = pd.concat([keep[new_rows.columns], new_rows], ignore_index=True)

    # Re-cluster everything together. PRIORITY decides cross-label homologs; the new label is a
    # negative tier, so it must rank below protective exactly as the old one did.
    PRIORITY.setdefault(NEW_LABEL, PRIORITY.get(DROP_LABEL, 1))
    records = [Record(sequence_id=r.sequence_id, sequence=r.sequence, label=r.label,
                      source=r.source, evidence_code=r.evidence_code)
               for r in combined.itertuples()]
    print(f"[merge] re-clustering {len(records)} sequences at {identity:.0%} identity "
          "(this is the slow step)")
    clustered = cluster_sequences(records, identity=identity)

    out = pd.DataFrame([r.__dict__ for r in clustered])
    out["in_matched_set"] = ((out["label"] == NEW_LABEL)
                             | out["sequence_id"].isin(matched_pos_ids))

    shutil.copy2(DATASET, BACKUP)
    print(f"[merge] previous dataset backed up to {BACKUP}")
    out.to_csv(DATASET, index=False)

    print(f"\n[merge] wrote {DATASET}: {len(out)} sequences, "
          f"{out['cluster_id'].nunique()} clusters")
    print(f"  labels: {dict(out['label'].value_counts())}")
    in_set = out[out["in_matched_set"]]
    print(f"  matched-pair subset: {len(in_set)} rows "
          f"({dict(in_set['label'].value_counts())}), "
          f"{in_set['cluster_id'].nunique()} clusters")

    missing = out.loc[out["label"] == NEW_LABEL, "sequence_id"]
    print(f"\n  Next: `python -m tardiscreen.embed` — {len(missing)} new sequences need embedding;"
          "\n  everything already in embeddings.npz is reused. Then evaluate.")


if __name__ == "__main__":
    main()
