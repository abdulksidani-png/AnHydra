"""ESM-2 sequence embeddings.

Owner: Model. Small ESM-2 (35M-150M params) embeds ~2k sequences on CPU in minutes — no GPU needed.
Freeze the embeddings (mean-pool over residues) and cache them; do NOT fine-tune over the weekend.
"""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_MODEL = "facebook/esm2_t12_35M_UR50D"  # small + CPU-friendly; bump to 150M if time allows.


def embed_sequences(sequences: list[str], model_name: str = DEFAULT_MODEL):
    """Return an (N, D) float array of mean-pooled ESM-2 embeddings.

    TODO (model owner):
        from transformers import AutoTokenizer, AutoModel
        import torch
        tok = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).eval()
        # batch, truncate long sequences, mean-pool last_hidden_state over the attention mask,
        # run under torch.no_grad(), move to CPU, stack.
    Cache the result to data/embeddings.npy keyed by sequence_id so you only pay for it once.
    """
    raise NotImplementedError("Model owner: implement ESM-2 embedding (see docstring).")


def build(dataset_csv: Path | None = None):
    """Load the dataset, embed every sequence, cache to data/embeddings.npy."""
    raise NotImplementedError("Model owner: wire dataset -> embed_sequences -> cache.")


if __name__ == "__main__":
    build()
