"""Add sequence hashes to an existing embeddings.npz instead of recomputing it.

Embedding caches now carry a sha256 per sequence, so that reusing an accession for a different
sequence invalidates its vector. A cache written before that change has no hashes and is discarded
wholesale — correct by default, but it would re-embed every sequence.

That recompute is avoidable when the cache provably matches the dataset: the embed run's own
acceptance checks require the cached ids to be an exact permutation of dataset.csv, and dataset.csv
has not been rewritten since. This re-checks that invariant and, only if it holds, writes the hashes
of the sequences now in dataset.csv into the cache.

    python scripts/backfill_embedding_hashes.py

Refuses to touch anything if the ids do not match exactly — in that case the honest move is to
re-embed. The original file is copied to embeddings.prev.npz first.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


def _sequence_hash(sequence: str) -> str:
    """Must stay identical to embed._sequence_hash. Inlined so this script does not import torch."""
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE, BACKUP = DATA / "embeddings.npz", DATA / "embeddings.prev.npz"


def main() -> int:
    if not CACHE.exists():
        print(f"{CACHE} not found — nothing to migrate.")
        return 1
    z = np.load(CACHE, allow_pickle=False)
    if "sequence_hashes" in z:
        print("cache already carries sequence hashes; nothing to do.")
        return 0

    df = pd.read_csv(DATA / "dataset.csv", dtype=str).fillna("")
    seq_by_id = dict(zip(df["sequence_id"], df["sequence"]))
    ids = z["ids"].astype(str)

    missing = set(df["sequence_id"]) - set(ids)
    extra = set(ids) - set(df["sequence_id"])
    if missing or extra or len(ids) != len(set(ids)):
        print(f"REFUSING: cache does not match dataset.csv exactly "
              f"(missing {len(missing)}, extra {len(extra)}, "
              f"dupes {len(ids) - len(set(ids))}).")
        print("Re-embed instead: python -m tardiscreen.embed")
        return 1

    hashes = np.array([_sequence_hash(seq_by_id[sid]) for sid in ids], dtype=object).astype(str)
    shutil.copy2(CACHE, BACKUP)
    np.savez(CACHE, ids=ids, X=z["X"], model=z["model"], sequence_hashes=hashes)
    print(f"backed up to {BACKUP}")
    print(f"wrote {len(ids)} sequence hashes into {CACHE} — the cache will now be reused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
