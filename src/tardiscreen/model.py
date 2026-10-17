"""The two models: a classifier head on ESM-2 embeddings, and the interpretable biophysical model.

Owner: Model. The embedding classifier supplies the score; the feature model provides auxiliary
biophysical signals. The composition baseline in evaluate.py is the bar to beat.

Train the production models (fit on all data) and save them for the app:
    python -m tardiscreen.model        # writes data/models.joblib
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from .features import FEATURE_NAMES, compute_features
from .artifacts import atomic_destination, load_embeddings

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODELS_PATH = DATA_DIR / "models.joblib"
POSITIVE = "protective"   # the production task: protective vs. everything else


@dataclass
class Prediction:
    score: float                 # uncalibrated classifier score of "protective"
    label: str                   # argmax family call
    top_features: list[tuple[str, float]]   # (feature_name, contribution), for the "why"
    nearest_homolog: str | None = None       # id of nearest known protective sequence


def featurize(sequences: list[str]) -> np.ndarray:
    """(N, F) array of biophysical features, columns == FEATURE_NAMES."""
    return np.asarray([list(compute_features(s).as_dict().values()) for s in sequences],
                      dtype=np.float64)


def _pipeline():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(),
                         LogisticRegression(max_iter=2000, class_weight="balanced"))


def train_embedding_model(X, y):
    """Classifier head on frozen ESM-2 vectors (scaled logistic regression)."""
    return _pipeline().fit(np.asarray(X, dtype=np.float64), np.asarray(y))


def train_feature_model(X, y):
    """Logistic model on the interpretable features — powers the per-feature 'why'."""
    return _pipeline().fit(np.asarray(X, dtype=np.float64), np.asarray(y))


def train(dataset_csv: Path | None = None):
    """Fit the production models on ALL data (protective vs. rest) and save to data/models.joblib.

    Bundles the ESM-2 model (the score), the biophysical model (the 'why'), and the protective
    sequences' embeddings (for nearest-homolog lookup).
    """
    import joblib
    import pandas as pd

    ds = Path(dataset_csv) if dataset_csv else DATA_DIR / "dataset.csv"
    npz = DATA_DIR / "embeddings.npz"
    if not ds.exists() or not npz.exists():
        raise FileNotFoundError("Need data/dataset.csv and data/embeddings.npz — run "
                               "`python -m tardiscreen.data` then `python -m tardiscreen.embed`.")

    df = pd.read_csv(ds, dtype=str).fillna("")
    emb, encoder = load_embeddings(npz, df)

    y = (df["label"] == POSITIVE).astype(int).to_numpy()
    X_esm = np.vstack([emb[sid] for sid in df["sequence_id"]]).astype(np.float64)
    X_bio = featurize(df["sequence"].tolist())

    esm_clf = train_embedding_model(X_esm, y)
    bio_clf = train_feature_model(X_bio, y)

    # Protective embeddings for nearest-homolog lookup (L2-normalized for cosine similarity).
    pos_mask = y == 1
    homolog_X = X_esm[pos_mask]
    homolog_X = homolog_X / (np.linalg.norm(homolog_X, axis=1, keepdims=True) + 1e-9)
    homolog_ids = df.loc[pos_mask, "sequence_id"].tolist()

    bundle = {
        "esm_clf": esm_clf, "bio_clf": bio_clf, "feature_names": FEATURE_NAMES,
        "homolog_X": homolog_X.astype(np.float32), "homolog_ids": homolog_ids,
        "model_name": encoder,
    }
    MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with atomic_destination(MODELS_PATH) as temporary:
        joblib.dump(bundle, temporary)
    print(f"[model] trained on {len(df)} sequences ({int(y.sum())} protective); saved {MODELS_PATH}")
    return MODELS_PATH


@lru_cache(maxsize=1)
def _load_bundle(path_str: str, mtime: int) -> dict:
    """Read models.joblib, cached. `mtime` is part of the key so retraining invalidates the cache."""
    import joblib

    return joblib.load(path_str)


def load_bundle() -> dict:
    """The fitted bundle, read from disk once and reused across requests."""
    if not MODELS_PATH.exists():
        raise FileNotFoundError(f"{MODELS_PATH} not found — run `python -m tardiscreen.model` first.")
    bundle = _load_bundle(str(MODELS_PATH), MODELS_PATH.stat().st_mtime_ns)
    required = {"esm_clf", "bio_clf", "feature_names", "homolog_ids", "homolog_X", "model_name"}
    if not isinstance(bundle, dict) or not required <= bundle.keys() or not bundle["model_name"]:
        raise ValueError("Invalid model bundle; retrain before scoring.")
    if list(bundle["feature_names"]) != FEATURE_NAMES:
        raise ValueError("Model features do not match this app; retrain before scoring.")
    return bundle


def predict(sequence: str) -> Prediction:
    """Score a single sequence for the app. Reuses the cached fitted models + embeds the sequence."""
    bundle = load_bundle()

    model_name = bundle.get("model_name")
    if not model_name:
        raise ValueError("Model bundle has no embedding model name; retrain before scoring.")
    # Load the exact training encoder, even if the serving environment selects another default.
    from .embed import embed_sequences
    vec = embed_sequences([sequence], model_name=model_name)[0].astype(np.float64)
    score = float(bundle["esm_clf"].predict_proba([vec])[0, 1])

    # Per-feature contribution = standardized feature value x logistic coefficient.
    bio = featurize([sequence])[0]
    scaler = bundle["bio_clf"].named_steps["standardscaler"]
    logreg = bundle["bio_clf"].named_steps["logisticregression"]
    contrib = scaler.transform([bio])[0] * logreg.coef_[0]
    top = sorted(zip(bundle["feature_names"], contrib), key=lambda t: abs(t[1]), reverse=True)[:3]
    top_features = [(name, float(c)) for name, c in top]

    # Nearest known protective homolog by cosine similarity.
    nearest = None
    if len(bundle["homolog_ids"]):
        q = vec / (np.linalg.norm(vec) + 1e-9)
        sims = bundle["homolog_X"] @ q
        nearest = bundle["homolog_ids"][int(np.argmax(sims))]

    return Prediction(score=score, label=POSITIVE if score >= 0.5 else "other_idp",
                     top_features=top_features, nearest_homolog=nearest)


__all__ = ["Prediction", "featurize", "train_embedding_model", "train_feature_model", "train",
           "predict", "load_bundle", "FEATURE_NAMES"]


if __name__ == "__main__":
    train()
