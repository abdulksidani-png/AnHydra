"""The two models: a classifier head on ESM-2 embeddings, and the interpretable biophysical model.

Owner: Model. Keep both — the embedding model is the centerpiece; the feature model is the "why" and
the fallback that runs if embeddings stall. Also keep a composition baseline (in evaluate.py) as the
bar to beat.
"""

from __future__ import annotations

from dataclasses import dataclass

from .features import FEATURE_NAMES, compute_features


@dataclass
class Prediction:
    score: float                 # calibrated probability of "protective"
    label: str                   # argmax family call
    top_features: list[tuple[str, float]]   # (feature_name, contribution), for the "why"
    nearest_homolog: str | None = None       # id of nearest known protective sequence


def featurize(sequences: list[str]):
    """(N, F) array of biophysical features, columns == FEATURE_NAMES."""
    rows = [list(compute_features(s).as_dict().values()) for s in sequences]
    return rows  # TODO: return np.asarray(rows, dtype=float) once numpy is wired in.


def train_embedding_model(X, y):
    """Classifier head on frozen ESM-2 vectors.

    TODO (model owner): logistic regression or a small MLP (sklearn is fine for a weekend). Calibrate
    probabilities (CalibratedClassifierCV) so the app's score means something. Return a fitted model.
    """
    raise NotImplementedError("Model owner: train classifier head on embeddings.")


def train_feature_model(X, y):
    """Gradient-boosted or logistic model on the interpretable features.

    This one powers interpretability — keep it simple enough to extract per-feature importances.
    """
    raise NotImplementedError("Model owner: train the biophysical-feature model.")


def predict(sequence: str) -> Prediction:
    """Score a single sequence for the app. Loads the cached fitted models.

    TODO (model + app owners): embed the sequence, run both models, blend or pick the score, compute
    per-feature contributions for `top_features`, and look up the nearest protective homolog
    (cosine similarity over cached embeddings).
    """
    raise NotImplementedError("Wire embed + models + homolog lookup for single-sequence inference.")


__all__ = ["Prediction", "featurize", "train_embedding_model", "train_feature_model", "predict",
           "FEATURE_NAMES"]
