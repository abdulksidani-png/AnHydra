"""Pick the site's three example sequences from the training data and print them as JSON.

Run from the repository root on a machine that has data/dataset.csv and data/families.csv:

    .venv/bin/python scripts/pick_examples.py

Picks one dehydrin, one CAHS protein and one non-protective protein, each 80 to 250 residues of
standard amino acids so it is accepted by /score and fits the residue map. The pick is the
middle entry by accession, so rerunning on the same data gives the same three.
"""
import json
from pathlib import Path
import sys

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AA = set("ACDEFGHIKLMNPQRSTVWY")


def main() -> int:
    dataset, families = DATA_DIR / "dataset.csv", DATA_DIR / "families.csv"
    for path in (dataset, families):
        if not path.exists():
            print(f"Missing {path}; it is needed to choose examples.", file=sys.stderr)
            return 1
    df = pd.read_csv(dataset, dtype=str).merge(
        pd.read_csv(families, dtype=str)[["sequence_id", "protein_name", "family"]],
        on="sequence_id", how="left")
    df = df[df["sequence"].str.len().between(80, 250) & df["sequence"].map(lambda s: set(s) <= AA)]
    protective = df["label"] == "protective"
    picks = [("dehydrin", "Dehydrin", protective & (df["family"] == "dehydrin")),
             ("cahs", "CAHS", protective & (df["family"] == "CAHS")),
             ("negative", "Not protective", ~protective)]
    out = []
    for key, label, mask in picks:
        rows = df[mask].sort_values("sequence_id")
        if rows.empty:
            print(f"No {label} sequence of 80 to 250 residues in the dataset.", file=sys.stderr)
            return 1
        row = rows.iloc[len(rows) // 2]
        out.append(dict(id=key, label=label, accession=row["sequence_id"],
                        name=row["protein_name"] if isinstance(row["protein_name"], str) else "",
                        seq=row["sequence"]))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
