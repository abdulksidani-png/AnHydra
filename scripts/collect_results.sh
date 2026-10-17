#!/usr/bin/env bash
# Copy the derived result artifacts out of data/ (gitignored) into docs/results/ (committed).
#
# data/ holds raw inputs and caches that must never be committed — dataset.csv, embeddings.npz,
# models.joblib. But the things the experiments PRODUCED are small, derived, and the entire point
# of the repo: without them the README makes claims a reader cannot see.
#
#   bash scripts/collect_results.sh
#
# Reports what it found and what is missing, so a half-finished run is visible rather than silently
# producing a partial results directory.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT="docs/results"
mkdir -p "$OUT"

ARTIFACTS=(
  "results_table.csv"        # the five-model comparison
  "results_table.md"         # same table, README-ready
  "results_auc.png"          # model comparison chart
  "confusion_matrix.png"     # ESM-2, out-of-fold, real task
  "feature_importance.png"   # biophysical coefficients
  "blast_results.csv"        # alignment baseline
  "remote_homology.csv"      # per-sequence BLAST vs ESM-2 by bitscore
  "family_holdout.csv"       # leave-one-family-out
  "cnn_results.csv"          # from-scratch CNN
  "cnn_motifs.csv"           # motifs read out of the CNN filters
  "disorder_coverage.csv"    # coverage per sequence, both classes
  "dataset_summary.md"       # dataset composition
)

found=0
missing=()
for name in "${ARTIFACTS[@]}"; do
  if [[ -f "data/$name" ]]; then
    cp "data/$name" "$OUT/$name"
    printf '  copied  %s (%s)\n' "$name" "$(du -h "data/$name" | cut -f1)"
    found=$((found + 1))
  else
    missing+=("$name")
  fi
done

echo
echo "copied $found artifact(s) into $OUT"
if ((${#missing[@]})); then
  echo "not found (the run that writes it may not have finished):"
  printf '    %s\n' "${missing[@]}"
fi

echo
echo "total size: $(du -sh "$OUT" | cut -f1)"
echo "next: git add docs/results && git commit && git push"
