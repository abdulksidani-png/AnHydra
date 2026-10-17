"""Lightweight artifact integrity checks, shared by training and evaluation."""
from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np


def sequence_hash(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()


@contextmanager
def atomic_destination(destination: Path):
    """Keep the previous artifact intact unless writing finishes successfully."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=destination.suffix, delete=False) as f:
        temporary = Path(f.name)
    try:
        yield temporary
        # NamedTemporaryFile starts at 0600 on Unix; preserve existing readable
        # artifact permissions so a root-run retrain does not lock out systemd.
        mode = destination.stat().st_mode & 0o777 if destination.exists() else 0o644
        os.chmod(temporary, mode)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_embeddings(path: Path, frame):
    """Reject incomplete, stale, legacy, or malformed caches before using vectors."""
    message = "Invalid embedding cache; rerun `python -m tardiscreen.embed`."
    required = {"sequence_id", "sequence"}
    if not required <= set(frame.columns) or frame.empty:
        raise ValueError("Dataset must contain sequence_id and sequence rows.")
    dataset_ids = frame["sequence_id"].astype(str)
    if dataset_ids.duplicated().any() or dataset_ids.str.strip().eq("").any():
        raise ValueError("Dataset sequence IDs must be unique and non-empty.")
    with np.load(path, allow_pickle=False) as z:
        if not {"ids", "X", "model", "sequence_hashes"} <= set(z.files):
            raise ValueError(message)
        ids, vectors = z["ids"].astype(str), z["X"]
        hashes, encoder = z["sequence_hashes"].astype(str), z["model"]
        if (ids.ndim != 1 or hashes.shape != ids.shape or vectors.ndim != 2
                or vectors.shape[0] != len(ids) or vectors.shape[1] == 0
                or len(set(ids)) != len(ids) or not np.isfinite(vectors).all()
                or encoder.shape != () or not str(encoder).strip()):
            raise ValueError(message)
        expected = dict(zip(dataset_ids, frame["sequence"].astype(str)))
        cached = dict(zip(ids, hashes))
        if any(cached.get(sid) != sequence_hash(seq) for sid, seq in expected.items()):
            raise ValueError(message)
        return {sid: vectors[i] for i, sid in enumerate(ids) if sid in expected}, str(encoder)
