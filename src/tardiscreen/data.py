"""Pull and label the training set.

Owner: Data. See docs/DATA_PLAN.md for the tiers and the cluster-split rule — that doc is the spec
for this file.

The goal of this module is one labeled table:
    sequence_id, sequence, label, source, evidence_code, cluster_id

where label ∈ {"protective", "other_idp", "ordered"} and cluster_id comes from CD-HIT.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
LABELS = ("protective", "other_idp", "ordered")


@dataclass
class Record:
    sequence_id: str
    sequence: str
    label: str
    source: str
    evidence_code: str = ""
    cluster_id: str = ""


def fetch_positives() -> list[Record]:
    """CAHS/SAHS/MAHS + LEA + other anhydrobiosis IDPs from UniProt.

    TODO: query UniProt's REST API. Prefer experimental evidence codes over keyword-only hits
    (filter on `existence` / evidence). Example starting query:
        (keyword:"Stress response") AND (protein families like CAHS/LEA) AND reviewed:true
    Record the evidence_code per entry so the README can report label provenance honestly.
    """
    raise NotImplementedError("Data owner: implement UniProt pull (see docs/DATA_PLAN.md).")


def fetch_hard_negatives() -> list[Record]:
    """Other disordered proteins that are NOT desiccation-protective, from DisProt / MobiDB.

    This is the whole game — "among disordered proteins, which protect?" Pull a comparable number to
    the positives. TODO: DisProt + MobiDB API pulls.
    """
    raise NotImplementedError("Data owner: implement DisProt/MobiDB pull.")


def fetch_sanity_negatives() -> list[Record]:
    """Ordered globular proteins — the easy control tier. Keep, don't lead with."""
    raise NotImplementedError("Data owner: implement ordered-globular control pull.")


def cluster_sequences(records: list[Record], identity: float = 0.4) -> list[Record]:
    """Assign cluster_id with CD-HIT at `identity` (30-40%).

    TODO: write a FASTA, shell out to `cd-hit -c {identity} -n 2`, parse the .clstr file, and set
    cluster_id on each record. No cluster may later appear in both train and test.
    """
    raise NotImplementedError("Data owner: run CD-HIT and map cluster ids.")


def write_table(records: list[Record], path: Path | None = None) -> Path:
    path = path or DATA_DIR / "dataset.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sequence_id", "sequence", "label", "source", "evidence_code", "cluster_id"])
        for r in records:
            w.writerow([r.sequence_id, r.sequence, r.label, r.source, r.evidence_code, r.cluster_id])
    return path


def build() -> Path:
    records = fetch_positives() + fetch_hard_negatives() + fetch_sanity_negatives()
    records = cluster_sequences(records)
    return write_table(records)


if __name__ == "__main__":
    out = build()
    print(f"Wrote dataset to {out}")
