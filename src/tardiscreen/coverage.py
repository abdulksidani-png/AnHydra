"""How disordered is each DisProt negative, really?

Owner: Model/Data. Run from the repo root (needs network access to disprot.org):
    python -m tardiscreen.coverage

The negatives in dataset.csv come from DisProt, which curates disordered REGIONS inside proteins —
not whole disordered proteins. An entry whose regions cover 7% of its length is a folded protein with
a floppy tail; one at 90% is genuinely unstructured. Lumping both together turns the "real" task back
into folded-vs-unfolded, which is what the trivial task already measures.

data.py reads the region annotations for their names and discards their coordinates, so the coverage
is recoverable from the same API call with no re-embedding: this writes
data/disorder_coverage.csv (sequence_id, disorder_fraction, n_regions, length) and reports how many
negatives survive at each threshold. evaluate.py can then filter on it.
"""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_PATH = DATA_DIR / "disorder_coverage.csv"

# DisProt has used different key spellings across releases; accept any of them per region.
START_KEYS = ("start", "start_pos", "begin", "from")
END_KEYS = ("end", "end_pos", "finish", "to")
THRESHOLDS = (0.3, 0.5, 0.7, 0.8, 0.9)


def _span(region: dict) -> tuple[int, int] | None:
    """(start, end) as 1-based inclusive ints, or None if this region has no usable coordinates."""
    start = next((region[k] for k in START_KEYS if region.get(k) not in (None, "")), None)
    end = next((region[k] for k in END_KEYS if region.get(k) not in (None, "")), None)
    if start is None or end is None:
        return None
    try:
        start, end = int(start), int(end)
    except (TypeError, ValueError):
        return None
    return (start, end) if end >= start else (end, start)


def disorder_fraction(entry: dict, seq_len: int) -> tuple[float, int]:
    """Fraction of residues covered by at least one annotated region, and the region count.

    Regions overlap, so merge them before summing — adding raw lengths would double-count and can
    exceed 1.0.
    """
    spans = [s for s in (_span(r) for r in (entry.get("regions") or [])
                         if isinstance(r, dict)) if s]
    if not spans or seq_len <= 0:
        return 0.0, len(spans)

    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    covered = sum(end - start + 1 for start, end in merged)
    return min(covered / seq_len, 1.0), len(spans)


def main():
    import pandas as pd

    from .data import _get

    ds = DATA_DIR / "dataset.csv"
    if not ds.exists():
        raise FileNotFoundError(f"{ds} not found — run `python -m tardiscreen.data` first.")
    df = pd.read_csv(ds, dtype=str).fillna("")
    wanted = set(df.loc[df["label"] == "other_idp", "sequence_id"])
    print(f"[coverage] {len(wanted)} DisProt negatives in dataset.csv")

    resp = _get("https://disprot.org/api/search",
                params={"release": "current", "show_ambiguous": "true",
                        "show_obsolete": "false", "format": "json"},
                headers={"Accept": "application/json"})
    if not resp:
        print("[coverage] DisProt returned nothing — cannot compute coverage.")
        return
    payload = resp.json()
    entries = payload.get("data", payload) if isinstance(payload, dict) else payload
    print(f"[coverage] DisProt returned {len(entries)} entries")

    rows, no_coords = [], 0
    for e in entries:
        sid = (e.get("acc") or e.get("disprot_id") or "").strip()
        if sid not in wanted:
            continue
        seq = (e.get("sequence") or "").strip()
        frac, n_regions = disorder_fraction(e, len(seq))
        if n_regions == 0:
            no_coords += 1
        rows.append(dict(sequence_id=sid, disorder_fraction=round(frac, 4),
                         n_regions=n_regions, length=len(seq)))

    if not rows:
        print("[coverage] matched no entries — accession format may differ from dataset.csv.")
        return

    out = pd.DataFrame(rows)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"[coverage] wrote {OUT_PATH} ({len(out)} rows, {len(wanted) - len(out)} unmatched)")

    if no_coords:
        sample = next((r for r in (entries[0].get("regions") or []) if isinstance(r, dict)), {})
        print(f"[coverage] WARNING: {no_coords} entries had regions with no readable coordinates.")
        print(f"           A region looks like: {sorted(sample)[:12]}")
        print("           If that list has no start/end-like key, tell Claude the key names.")

    frac = out["disorder_fraction"]
    print(f"\n[coverage] disorder fraction: median {frac.median():.2f}  mean {frac.mean():.2f}")
    print("  histogram (fraction of the protein that is annotated disordered):")
    for lo in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        n = int(((frac >= lo) & (frac < lo + 0.1)).sum())
        print(f"    {lo:.1f}-{lo + 0.1:.1f}  {'#' * min(n // 10, 60):<60} {n}")

    print("\n  negatives surviving each threshold (positives for comparison: "
          f"{int((df['label'] == 'protective').sum())}):")
    for t in THRESHOLDS:
        print(f"    >= {t:.1f} disordered: {int((frac >= t).sum()):>5}")
    print("\n  Read: a threshold that leaves a few hundred genuinely-disordered negatives gives the"
          "\n  honest task. These sequences are already embedded, so re-evaluating costs seconds.")


if __name__ == "__main__":
    main()
