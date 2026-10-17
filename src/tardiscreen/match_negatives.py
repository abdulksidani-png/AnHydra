"""Match the candidate negatives to the positives on BOTH disorder coverage and length.

Owner: Data/Model. Run after build_negatives.py:
    python -m tardiscreen.match_negatives

Reads data/negative_candidates.csv (the pool), data/dataset.csv (the positives) and
data/disorder_coverage.csv (per-sequence coverage). Writes data/matched_negatives.csv.

Why matching rather than a threshold: the positives are disordered (median coverage 0.88 among
annotated) and the old negatives were not (0.15), so disorder alone separated the classes and the
model could score 0.987 without learning anything about protection. Hard-thresholding the new
negatives at >=0.7 would leave the classes still differing in coverage, just by less — and if the
negatives ended up MORE disordered than the positives it would invert the confound rather than
remove it. Pairing each positive with a candidate of similar coverage AND similar length makes both
variables uninformative by construction.

Positives with no disorder annotation are excluded: a coverage of 0.00 there means unmeasured, not
ordered, and matching against it would be matching on annotation effort.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_PATH = DATA_DIR / "matched_negatives.csv"

COVERAGE_CALIPER = 0.10          # max |coverage difference| within a pair
LENGTH_CALIPER_FRAC = 0.15       # max |length difference|, as a fraction of the positive's length
LENGTH_CALIPER_MIN = 20          # ...or this many residues, whichever is larger


def _length_caliper(length: float) -> float:
    return max(LENGTH_CALIPER_MIN, LENGTH_CALIPER_FRAC * length)


def match(positives, candidates):
    """Greedy 1:1 pairing on (coverage, length) under calipers on both.

    Positives are matched in order of how hard they are to serve — those with the fewest eligible
    candidates go first, so a scarce positive is not left unmatched because a common one took its
    only partner.
    """
    pos = positives.reset_index(drop=True)
    cand = candidates.reset_index(drop=True)
    cand_cov = cand["disorder_fraction"].to_numpy(float)
    cand_len = cand["length"].to_numpy(float)
    available = np.ones(len(cand), dtype=bool)

    eligible: dict[int, np.ndarray] = {}
    for i, row in pos.iterrows():
        ok = (np.abs(cand_cov - row.disorder_fraction) <= COVERAGE_CALIPER) & \
             (np.abs(cand_len - row.length) <= _length_caliper(row.length))
        eligible[i] = np.flatnonzero(ok)

    pairs = []
    for i in sorted(eligible, key=lambda k: len(eligible[k])):
        options = eligible[i][available[eligible[i]]]
        if options.size == 0:
            continue
        row = pos.loc[i]
        # Among eligible candidates, take the closest in normalized (coverage, length) space.
        d_cov = np.abs(cand_cov[options] - row.disorder_fraction) / COVERAGE_CALIPER
        d_len = np.abs(cand_len[options] - row.length) / _length_caliper(row.length)
        best = options[int(np.argmin(d_cov + d_len))]
        available[best] = False
        pairs.append((i, int(best)))
    return pairs, pos, cand


def _auc(values, labels, groups=None) -> float:
    """Single-variable ROC-AUC — the self-check that a matched variable is now uninformative."""
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(labels, values))


def main():
    import pandas as pd

    cand_path = DATA_DIR / "negative_candidates.csv"
    cov_path = DATA_DIR / "disorder_coverage.csv"
    ds_path = DATA_DIR / "dataset.csv"
    for p in (cand_path, cov_path, ds_path):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found — run the earlier step first.")

    cand = pd.read_csv(cand_path)
    cov = pd.read_csv(cov_path)
    df = pd.read_csv(ds_path, dtype=str).fillna("")

    # Positives, restricted to those with a real disorder measurement.
    pos_cov = cov[(cov.get("label") == "protective") & (cov["n_regions"] > 0)].copy()
    pos = df[df["label"] == "protective"].merge(
        pos_cov[["sequence_id", "disorder_fraction", "n_regions"]], on="sequence_id")
    pos["length"] = pos["sequence"].str.len()
    print(f"[match] positives: {len(pos)} with a disorder annotation "
          f"({int((cov.get('label') == 'protective').sum()) - len(pos)} unannotated, excluded)")
    print(f"[match] candidate pool: {len(cand)}")

    sources = set(cand.get("annotation_source", pd.Series(dtype=str)).dropna())
    if sources and sources != {"uniprot_region"}:
        print(f"[match] NOTE: candidates measured by {sorted(sources)}, positives by UniProt "
              "Region.\n        Different rulers for the same quantity — treat the matched"
              " coverage as approximate,\n        or re-measure the positives through the same"
              " route before trusting it.")

    pairs, pos, cand = match(pos, cand)
    if not pairs:
        print("[match] no pairs within the calipers. Widen them or enlarge the pool.")
        return

    pos_idx = [p for p, _ in pairs]
    cand_idx = [c for _, c in pairs]
    matched_pos = pos.loc[pos_idx]
    matched_neg = cand.loc[cand_idx]

    print(f"\n[match] paired {len(pairs)} of {len(pos)} positives "
          f"({len(pos) - len(pairs)} had no partner within the calipers)")
    print(f"  coverage: positives median {matched_pos['disorder_fraction'].median():.2f}  vs "
          f"negatives {matched_neg['disorder_fraction'].median():.2f}")
    print(f"  length:   positives median {matched_pos['length'].median():.0f}  vs "
          f"negatives {matched_neg['length'].median():.0f}")

    # Self-check: on the matched set, neither matched variable should separate the classes.
    labels = np.r_[np.ones(len(matched_pos)), np.zeros(len(matched_neg))]
    cov_vals = np.r_[matched_pos["disorder_fraction"].to_numpy(float),
                     matched_neg["disorder_fraction"].to_numpy(float)]
    len_vals = np.r_[matched_pos["length"].to_numpy(float),
                     matched_neg["length"].to_numpy(float)]
    cov_auc, len_auc = _auc(cov_vals, labels), _auc(len_vals, labels)
    print("\n  SELF-CHECK (both should sit near 0.50):")
    print(f"    coverage-only ROC-AUC: {cov_auc:.3f}")
    print(f"    length-only   ROC-AUC: {len_auc:.3f}")
    worst = max(abs(cov_auc - 0.5), abs(len_auc - 0.5))
    if worst > 0.05:
        print("    -> still some separation. Tighten COVERAGE_CALIPER / LENGTH_CALIPER_FRAC and"
              "\n       rerun; residual drift here reappears as inflated model AUC later.")
    else:
        print("    -> both variables are uninformative on this set, as intended.")

    out = matched_neg.copy()
    out["label"] = "idp_matched"
    out["source"] = "uniprot"
    out.to_csv(OUT_PATH, index=False)
    matched_pos[["sequence_id"]].to_csv(DATA_DIR / "matched_positives.csv", index=False)
    print(f"\n[match] wrote {OUT_PATH} ({len(out)} negatives) and matched_positives.csv")
    print("  Next: merge into dataset.csv, re-cluster with CD-HIT, embed only the new sequences,"
          "\n  then re-run evaluate. Nothing has been merged yet.")


if __name__ == "__main__":
    main()
