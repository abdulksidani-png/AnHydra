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


def _merge_fraction(spans: list[tuple[int, int]], seq_len: int) -> float:
    """Fraction of residues covered by at least one span.

    Spans overlap, so merge them before summing — adding raw lengths double-counts and can exceed 1.
    """
    if not spans or seq_len <= 0:
        return 0.0
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        start, end = max(1, start), min(seq_len, end)
        if start > end:
            continue
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    covered = sum(end - start + 1 for start, end in merged)
    return min(covered / seq_len, 1.0)


def disorder_fraction(entry: dict, seq_len: int) -> tuple[float, int]:
    """DisProt entry -> (covered fraction, region count)."""
    spans = [s for s in (_span(r) for r in (entry.get("regions") or [])
                         if isinstance(r, dict)) if s]
    return _merge_fraction(spans, seq_len), len(spans)


def _uniprot_spans(entry: dict) -> list[tuple[int, int]]:
    """Disordered Region features of a UniProt entry, as 1-based inclusive spans.

    UniProt records disorder as features of type "Region" described "Disordered" (from MobiDB-lite),
    so filter on the description — taking every Region would sweep in domains and repeats.
    """
    spans = []
    for feat in entry.get("features", []) or []:
        if not isinstance(feat, dict):
            continue
        if "disorder" not in str(feat.get("description", "")).lower():
            continue
        loc = feat.get("location") or {}
        start = (loc.get("start") or {}).get("value")
        end = (loc.get("end") or {}).get("value")
        if start is None or end is None:
            continue
        try:
            start, end = int(start), int(end)
        except (TypeError, ValueError):
            continue
        spans.append((start, end) if end >= start else (end, start))
    return spans


def fetch_uniprot_coverage(accessions: list[str], chunk: int = 100) -> list[dict]:
    """Disorder coverage for UniProt accessions, fetched in OR'd batches.

    Batched because one request per accession would be ~1000 round trips. Uses the plain search
    endpoint rather than a bulk route so it works across UniProt API versions.
    """
    from .data import _get

    rows, missing = [], 0
    for i in range(0, len(accessions), chunk):
        batch = accessions[i:i + chunk]
        resp = _get("https://rest.uniprot.org/uniprotkb/search",
                    params={"query": " OR ".join(f"accession:{a}" for a in batch),
                            "fields": "accession,length,ft_region",
                            "format": "json", "size": str(chunk)},
                    headers={"Accept": "application/json"})
        if not resp:
            missing += len(batch)
            continue
        try:
            results = resp.json().get("results", [])
        except ValueError:
            missing += len(batch)
            continue
        for entry in results:
            acc = entry.get("primaryAccession", "")
            seq_len = int(entry.get("sequence", {}).get("length")
                          or len(entry.get("sequence", {}).get("value", "")) or 0)
            spans = _uniprot_spans(entry)
            rows.append(dict(sequence_id=acc,
                             disorder_fraction=round(_merge_fraction(spans, seq_len), 4),
                             n_regions=len(spans), length=seq_len))
        print(f"  [uniprot] {min(i + chunk, len(accessions))}/{len(accessions)} accessions")
    if missing:
        print(f"  [uniprot] WARNING: {missing} accessions in failed batches")
    return rows


def _describe(name: str, frac) -> None:
    """One-line distribution summary plus the fraction above each threshold."""
    import numpy as np

    if len(frac) == 0:
        print(f"  {name:>12}: no rows")
        return
    q = np.percentile(frac, [25, 50, 75])
    above = "  ".join(f">={t:.1f}: {float((frac >= t).mean()):.0%}" for t in THRESHOLDS)
    print(f"  {name:>12}: n={len(frac):<5} median {q[1]:.2f}  (IQR {q[0]:.2f}-{q[2]:.2f})   {above}")


def main():
    import pandas as pd

    from .data import _get

    ds = DATA_DIR / "dataset.csv"
    if not ds.exists():
        raise FileNotFoundError(f"{ds} not found — run `python -m tardiscreen.data` first.")
    df = pd.read_csv(ds, dtype=str).fillna("")
    if "idp_matched" in set(df["label"]):
        ids = df.loc[df["label"].isin(["protective", "idp_matched"]), "sequence_id"].tolist()
        rows = fetch_uniprot_coverage(ids)
        if set(r["sequence_id"] for r in rows) != set(ids):
            raise ValueError("Coverage fetch incomplete; previous coverage file preserved.")
        from .artifacts import atomic_destination
        out = pd.DataFrame(rows)
        out["label"] = out["sequence_id"].map(dict(zip(df["sequence_id"], df["label"])))
        out["annotation_source"] = "uniprot_region"
        with atomic_destination(OUT_PATH) as temporary:
            out.to_csv(temporary, index=False)
        print(f"[coverage] refreshed both current classes: {len(out)} rows")
        return
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

    # --- the positives, so filtering negatives on disorder can't invert the confound -------------
    print("\n" + "=" * 78)
    print("POSITIVES — how disordered are the protective proteins themselves?")
    print("=" * 78)
    print("  Filtering negatives on disorder while leaving positives unfiltered would make disorder"
          "\n  separate the classes again, backwards. That needs measuring, not assuming.\n")

    pos_ids = sorted(df.loc[df["label"] == "protective", "sequence_id"])
    pos_rows = fetch_uniprot_coverage(pos_ids)
    if not pos_rows:
        print("  could not fetch positive coverage — leaving the negative file as written.")
        return

    pos = pd.DataFrame(pos_rows)
    out = pd.concat([out.assign(label="other_idp"), pos.assign(label="protective")],
                    ignore_index=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"\n[coverage] rewrote {OUT_PATH} with both classes ({len(out)} rows)")

    print("\n  side by side:")
    _describe("protective", pos["disorder_fraction"].to_numpy())
    _describe("other_idp", frac.to_numpy())

    gap = float(pos["disorder_fraction"].median()) - float(frac.median())
    print(f"\n  median gap (protective - negatives): {gap:+.2f}")
    pos_hi = float((pos["disorder_fraction"] >= 0.7).mean())
    print(f"  positives already >= 0.7 disordered: {pos_hi:.0%}")
    if pos_hi >= 0.8:
        print("  -> positives are themselves mostly disordered: filtering negatives at 0.7 puts"
              "\n     both classes in the same range, so no disorder-matching is needed.")
    else:
        print("  -> a sizable share of positives fall below 0.7. Filtering negatives there would"
              "\n     make the classes differ in disorder, inverting the confound. Match the"
              "\n     negatives to the positives' distribution instead of hard-thresholding.")


def report():
    """Split the written coverage file by whether the entry carries ANY disorder annotation.

    A fraction of 0.0 means two different things: annotated as ordered, or never annotated at all.
    UniProt's MobiDB-lite coverage is incomplete, so conflating them would let a later match on
    coverage become a match on annotation completeness — a fresh artifact replacing the old one.
    Reads the local CSV only; no network.
    """
    import numpy as np
    import pandas as pd

    if not OUT_PATH.exists():
        raise FileNotFoundError(f"{OUT_PATH} not found — run `python -m tardiscreen.coverage` first.")
    cov = pd.read_csv(OUT_PATH)
    if "label" not in cov.columns:
        print("No label column — rerun `python -m tardiscreen.coverage` to include the positives.")
        return

    print("=" * 78)
    print("ANNOTATED vs UNANNOTATED — is a 0.00 coverage real, or just missing data?")
    print("=" * 78)
    for label, grp in cov.groupby("label"):
        unann = grp[grp["n_regions"] == 0]
        ann = grp[grp["n_regions"] > 0]
        print(f"\n  {label}: {len(grp)} total")
        print(f"    no disorder annotation at all : {len(unann):>5}  ({len(unann) / len(grp):.0%})")
        print(f"    has >=1 annotated region      : {len(ann):>5}  ({len(ann) / len(grp):.0%})")
        if len(ann):
            f = ann["disorder_fraction"].to_numpy()
            q = np.percentile(f, [25, 50, 75])
            print(f"    among ANNOTATED only: median {q[1]:.2f} (IQR {q[0]:.2f}-{q[2]:.2f})  "
                  + "  ".join(f">={t:.1f}: {float((f >= t).mean()):.0%}" for t in (0.5, 0.7, 0.9)))

    print("\n  Read: if the unannotated share differs a lot between the classes, coverage is partly"
          "\n  measuring annotation effort, not biology. In that case build the matched sets from"
          "\n  ANNOTATED entries only, in both classes, so 0.00 always means 'measured as ordered'.")


if __name__ == "__main__":
    import sys

    report() if "--report" in sys.argv else main()
