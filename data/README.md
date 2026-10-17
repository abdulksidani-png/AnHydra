# Local data and model artifacts

Raw inputs and generated arrays/models are gitignored. Run the full staged pipeline
in the root README; `data.py` alone does not generate all artifacts.

| Artifact | Producer |
| --- | --- |
| dataset.csv | data, then merge_dataset |
| disorder_coverage.csv | coverage |
| negative_candidates.csv | build_negatives |
| matched_negatives.csv / matched_positives.csv | match_negatives |
| embeddings.npz | embed (vectors, encoder name, per-sequence hashes) |
| models.joblib | model |
| results_table.csv / figures | evaluate |

Legacy embedding caches without sequence hashes must be rebuilt. Training and
evaluation reject incomplete or stale caches. Never invent hashes for old vectors.
Derived published results are exported separately to `docs/results/`.
