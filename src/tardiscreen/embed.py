"""ESM-2 sequence embeddings.

Owner: Model. Small ESM-2 (35M-150M params) embeds ~2k sequences on CPU in minutes — no GPU needed.
Freeze the embeddings (mean-pool over residues) and cache them; do NOT fine-tune over the weekend.

Run from the repo root (needs the model stack):
    pip install -e ".[ml]"          # or: pip install -r requirements.txt
    python -m tardiscreen.embed

Override the model without editing code:
    TARDISCREEN_EMBED_MODEL=facebook/esm2_t30_150M_UR50D python -m tardiscreen.embed
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_MODEL = "facebook/esm2_t12_35M_UR50D"  # small + CPU-friendly; bump to 150M if time allows.

# esm2_t30_150M_UR50D matches the HaloClass setup and is more accurate — use it if there's
# time/compute (set TARDISCREEN_EMBED_MODEL, below). The 35M default keeps CPU embedding fast.
BATCH_SIZE = 8
MAX_LENGTH = 1024
CHECKPOINT_EVERY = 256          # re-save the cache every this many newly embedded sequences
CACHE = DATA_DIR / "embeddings.npz"


def _resolve_model(model_name: str = DEFAULT_MODEL) -> str:
    """An explicit non-default arg wins; otherwise honor TARDISCREEN_EMBED_MODEL, else the default."""
    if model_name == DEFAULT_MODEL:
        return os.environ.get("TARDISCREEN_EMBED_MODEL", DEFAULT_MODEL)
    return model_name


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    """Load the tokenizer + model once (CPU). Returns (tokenizer, model, device, hidden_size).

    Cached: the app calls embed_sequences() once per request, and reloading a 35M-param model each
    time would add seconds of latency per score. The batch path loads it once either way.
    """
    device = torch.device("cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()
    return tokenizer, model, device, int(model.config.hidden_size)


def _embed_with(bundle, sequences: list[str], desc: str) -> np.ndarray:
    """Mean-pooled embeddings for `sequences` using an already-loaded model bundle."""
    tokenizer, model, device, hidden_size = bundle
    if not sequences:
        return np.zeros((0, hidden_size), dtype=np.float32)
    chunks: list[np.ndarray] = []
    for start in tqdm(range(0, len(sequences), BATCH_SIZE), desc=desc, unit="batch"):
        batch = [str(s) for s in sequences[start:start + BATCH_SIZE]]
        enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True,
                        max_length=MAX_LENGTH)
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            hidden = model(**enc).last_hidden_state          # (B, L, D)
        mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)  # (B, L, 1)
        summed = (hidden * mask).sum(dim=1)                  # (B, D)
        counts = mask.sum(dim=1).clamp(min=1.0)              # (B, 1), avoid /0
        chunks.append((summed / counts).cpu().numpy().astype(np.float32))
    return np.vstack(chunks).astype(np.float32)


def embed_sequences(sequences: list[str], model_name: str = DEFAULT_MODEL) -> np.ndarray:
    """Return an (N, D) float32 array of mean-pooled ESM-2 embeddings (frozen, CPU).

    Sequences are batched and truncated to MAX_LENGTH; the last hidden state is mean-pooled over the
    attention mask so padding tokens don't count.
    """
    model_name = _resolve_model(model_name)
    return _embed_with(_load_model(model_name), list(sequences),
                       f"embedding ({model_name.split('/')[-1]})")


def _load_cache(model_name: str) -> dict[str, np.ndarray]:
    """Return {sequence_id: vector} from the cache, but only if it was built with this model."""
    if not CACHE.exists():
        return {}
    z = np.load(CACHE, allow_pickle=False)
    cached_model = str(z["model"]) if "model" in z else ""
    if cached_model and cached_model != model_name:
        print(f"[embed] cache was built with {cached_model}, not {model_name} — recomputing all.")
        return {}
    ids = z["ids"].astype(str)
    X = z["X"]
    return {sid: X[i] for i, sid in enumerate(ids)}


def _acceptance_checks(n_rows: int, ids: list[str], X: np.ndarray, dataset_ids: list[str]) -> bool:
    print("\n=== acceptance checks ===")
    ok = True

    shape_ok = X.shape[0] == n_rows and len(ids) == X.shape[0]
    print(f"  [{'OK' if shape_ok else 'FAIL'}] rows match dataset: "
          f"X={X.shape[0]}, ids={len(ids)}, dataset={n_rows}")
    ok = ok and shape_ok

    finite = bool(np.isfinite(X).all()) if X.size else True
    print(f"  [{'OK' if finite else 'FAIL'}] no NaNs/infs in X")
    ok = ok and finite

    perm_ok = sorted(ids) == sorted(dataset_ids) and len(set(ids)) == len(ids)
    missing = set(dataset_ids) - set(ids)
    extra = set(ids) - set(dataset_ids)
    print(f"  [{'OK' if perm_ok else 'FAIL'}] ids are a permutation of dataset.csv "
          f"(missing {len(missing)}, extra {len(extra)}, dupes {len(ids) - len(set(ids))})")
    ok = ok and perm_ok

    print("=========================\n")
    return ok


def _save(cached: dict[str, np.ndarray], model_name: str) -> np.ndarray:
    """Write the cache to embeddings.npz. Order doesn't matter — downstream aligns by id."""
    ids_list = list(cached.keys())
    X = (np.vstack([cached[s] for s in ids_list]).astype(np.float32)
         if ids_list else np.zeros((0, 0), dtype=np.float32))
    np.savez(CACHE, ids=np.array(ids_list, dtype=object).astype(str), X=X, model=np.array(model_name))
    return X


def build(dataset_csv: Path | None = None):
    """Embed every sequence in data/dataset.csv and cache to data/embeddings.npz.

    The cache holds `ids` (sequence_id) and `X` (N x D) plus the model name; model.py / evaluate.py
    load it and align by sequence_id. Resumable with CHECKPOINTS: it embeds in chunks of
    CHECKPOINT_EVERY and re-saves after each one, so a dropped connection or a server reboot loses at
    most one chunk — rerun and it continues from the last checkpoint instead of starting over.
    """
    import pandas as pd

    dataset_csv = Path(dataset_csv) if dataset_csv else DATA_DIR / "dataset.csv"
    if not dataset_csv.exists():
        raise FileNotFoundError(
            f"{dataset_csv} not found — run `python -m tardiscreen.data` first.")

    df = pd.read_csv(dataset_csv, dtype=str).fillna("")
    ids = df["sequence_id"].tolist()
    id_to_seq = dict(zip(ids, df["sequence"].tolist()))
    n_rows = len(ids)
    if not ids:
        print("[embed] dataset is empty — nothing to embed."); return CACHE

    model_name = _resolve_model()
    cached = _load_cache(model_name)
    cached = {sid: cached[sid] for sid in ids if sid in cached}  # drop stale ids not in dataset
    todo_ids = [sid for sid in ids if sid not in cached]
    print(f"[embed] {n_rows} sequences: {len(cached)} already cached, {len(todo_ids)} to embed "
          f"(model {model_name})")

    t0 = time.time()
    if todo_ids:
        bundle = _load_model(model_name)
        for start in range(0, len(todo_ids), CHECKPOINT_EVERY):
            chunk_ids = todo_ids[start:start + CHECKPOINT_EVERY]
            done_after = min(start + CHECKPOINT_EVERY, len(todo_ids))
            vecs = _embed_with(bundle, [id_to_seq[s] for s in chunk_ids],
                               f"embedding {done_after}/{len(todo_ids)}")
            for sid, vec in zip(chunk_ids, vecs):
                cached[sid] = vec
            _save(cached, model_name)   # checkpoint — safe to interrupt after this
            print(f"[embed] checkpoint saved: {len(cached)}/{n_rows} "
                  f"({time.time() - t0:.0f}s elapsed)")

    X = _save(cached, model_name)
    newly = len(todo_ids)
    print(f"\n[embed] model: {model_name}")
    print(f"[embed] sequences: {n_rows}  |  embedding dim D: {X.shape[1] if X.ndim == 2 else 0}")
    print(f"[embed] newly embedded: {newly}  |  loaded from cache: {n_rows - newly}")
    print(f"[embed] time: {time.time() - t0:.1f}s  |  cache: {CACHE}")

    # Validate the file we just wrote (round-trip) against dataset.csv's own id column.
    reloaded = np.load(CACHE, allow_pickle=False)
    _acceptance_checks(n_rows, reloaded["ids"].astype(str).tolist(), reloaded["X"],
                       df["sequence_id"].tolist())
    return CACHE


if __name__ == "__main__":
    build()
