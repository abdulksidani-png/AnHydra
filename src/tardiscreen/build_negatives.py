"""Build a candidate pool of genuinely disordered, non-protective negatives.

Owner: Data. Run on a host with network access:
    python -m tardiscreen.build_negatives

Why this exists: the DisProt negatives are mostly folded proteins carrying a disordered region
(median disorder coverage 0.15), while the protective positives are disordered end to end (median
0.88 among annotated). So the "real" task was largely folded-vs-unfolded. These candidates replace
them with proteins that are actually disordered, taken from UniProt — the same source as the
positives, which removes the source confound in the same change.

This writes a CANDIDATE POOL only (data/negative_candidates.csv). Nothing is added to dataset.csv
here: the pool still has to be matched to the positives on disorder coverage AND length, which is a
separate step. Writing the pool first makes that matching inspectable instead of hidden inside a
download.

Two annotation routes, tried in order, because UniProt's feature-query syntax has moved across
releases:
  1. UniProt Region/"Disordered" features (MobiDB-lite derived) — single source, simplest.
  2. MobiDB's own API, which serves JSONL with a precomputed `content_fraction` per protein.
MobiDB accessions ARE UniProt accessions, so route 2 does not reintroduce the source confound; it
only changes which annotation layer measures disorder.
"""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_PATH = DATA_DIR / "negative_candidates.csv"

UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"
MOBIDB_DOWNLOAD = "https://mobidb.org/api/download"

# Tried in order; the first that returns entries carrying real Disordered regions wins.
UNIPROT_QUERIES = (
    "(ft_region:disordered) AND (reviewed:true)",
    '(annotation:(type:region "Disordered")) AND (reviewed:true)',
    "(cc_domain:disordered) AND (reviewed:true)",
)
# A spread of well-annotated model organisms, so the negatives aren't one lineage's quirks.
MOBIDB_TAXA = ("9606", "10090", "7227", "6239", "3702", "559292",
               "7955", "8355", "9913", "9823", "4577", "39947", "224308", "83333")

MIN_COVERAGE = 0.40      # pool floor; the matching step narrows this to the positives' shape
TARGET_USABLE = 2000     # candidates at >=0.60 coverage needed before skipping the MobiDB route
PAGE_SIZE = 500
MAX_PAGES = 60          # fully-disordered proteins are rare; a shallow slice misses them


# Short acronyms must match as whole words: a bare "lea" substring also hits "nuclear", "cleavage",
# "release" and "leader", which would silently discard a large share of ordinary disordered proteins
# (many IDPs are nuclear). Spelled-out family names are matched as phrases, since the acronym alone
# misses an entry titled "Cytoplasmic abundant heat soluble protein 1".
ACRONYM_TERMS = ("lea", "cahs", "sahs", "mahs")
PHRASE_TERMS = (
    "desiccation", "anhydrobiosis", "late embryogenesis", "dehydrin", "hydrophilin",
    "cryoprotect", "cytoplasmic abundant heat soluble", "secretory abundant heat soluble",
    "mitochondrial abundant heat soluble", "anhydrin", "tardigrade",
)


def _is_protective_name(text: str) -> bool:
    """True if the name/organism looks like a desiccation-protective family."""
    import re

    low = text.lower()
    if any(phrase in low for phrase in PHRASE_TERMS):
        return True
    return any(re.search(rf"\b{acr}\b", low) for acr in ACRONYM_TERMS)


# ---------------------------------------------------------------------------------------------
# Route 1: UniProt Region/"Disordered" features
# ---------------------------------------------------------------------------------------------
def _uniprot_page(resp) -> list[dict]:
    from .coverage import _merge_fraction, _uniprot_spans
    from .data import MAX_LEN, MIN_LEN

    rows = []
    for entry in resp.json().get("results", []):
        acc = entry.get("primaryAccession", "")
        seq = (entry.get("sequence") or {}).get("value", "")
        if not acc or not seq or not (MIN_LEN <= len(seq) <= MAX_LEN):
            continue
        name = ((entry.get("proteinDescription") or {}).get("recommendedName") or {})
        name_text = str(name.get("fullName", {}).get("value", "")) + " " + str(
            (entry.get("organism") or {}).get("scientificName", ""))
        if _is_protective_name(name_text):
            continue
        spans = _uniprot_spans(entry)
        if not spans:
            continue                      # no annotation means unmeasured, not ordered
        frac = _merge_fraction(spans, len(seq))
        if frac < MIN_COVERAGE:
            continue                      # a short disordered stretch in a folded protein
        rows.append(dict(sequence_id=acc, sequence=seq, disorder_fraction=round(frac, 4),
                         n_regions=len(spans), length=len(seq),
                         annotation_source="uniprot_region"))
    return rows


def fetch_via_uniprot() -> list[dict]:
    """Paginate a UniProt feature query. Returns [] if no query shape yields annotated entries."""
    from .data import _get

    for query in UNIPROT_QUERIES:
        print(f"[neg] trying UniProt query: {query}")
        resp = _get(UNIPROT_SEARCH,
                    params={"query": query,
                            "fields": "accession,sequence,length,ft_region,protein_name,organism_name",
                            "format": "json", "size": str(PAGE_SIZE)},
                    headers={"Accept": "application/json"}, tries=2)
        if not resp:
            print("    no response")
            continue
        total = resp.headers.get("x-total-results")
        try:
            rows = _uniprot_page(resp)
        except ValueError:
            print("    non-JSON response")
            continue
        print(f"    x-total-results={total}, usable on page 1: {len(rows)}")
        if not rows:
            continue

        # This query works — keep paging it.
        pages = 1
        while pages < MAX_PAGES:
            nxt = (resp.links.get("next") or {}).get("url")
            if not nxt:
                break
            resp = _get(nxt, headers={"Accept": "application/json"}, tries=2)
            if not resp:
                break
            try:
                rows.extend(_uniprot_page(resp))
            except ValueError:
                break
            pages += 1
            print(f"    page {pages}: {len(rows)} candidates so far")
        return rows

    print("[neg] no UniProt feature query returned annotated entries — falling back to MobiDB.")
    return []


# ---------------------------------------------------------------------------------------------
# Route 2: MobiDB (JSONL, precomputed content_fraction)
# ---------------------------------------------------------------------------------------------
def _best_fraction(record: dict) -> tuple[float, int]:
    """Pick a disorder fraction from a MobiDB record, preferring curated over predicted.

    MobiDB exposes several disorder layers as 'curated-disorder-*' / 'prediction-disorder-*' keys,
    each an object with content_fraction and regions. mobidb_lite is the consensus predictor and is
    what UniProt's own Region/"Disordered" annotations derive from, so it is the closest match to
    how the positives were measured.
    """
    preferred = ("curated-disorder-merge", "prediction-disorder-mobidb_lite",
                 "prediction-disorder-th_50")
    keys = preferred + tuple(k for k in record
                             if k.startswith(("curated-disorder", "prediction-disorder")))
    for key in keys:
        layer = record.get(key)
        if isinstance(layer, dict) and layer.get("content_fraction") is not None:
            try:
                return float(layer["content_fraction"]), len(layer.get("regions") or [])
            except (TypeError, ValueError):
                continue
    return 0.0, 0


def fetch_via_mobidb() -> list[dict]:
    """Stream MobiDB JSONL per taxon. Sequences are fetched from UniProt afterwards by accession."""
    import json

    from .data import _get

    rows: dict[str, dict] = {}
    for taxon in MOBIDB_TAXA:
        resp = _get(MOBIDB_DOWNLOAD, params={"ncbi_taxon_id": taxon, "format": "json"}, tries=2)
        if not resp:
            print(f"  [mobidb] taxon {taxon}: no response")
            continue
        kept = 0
        for line in resp.text.splitlines():          # JSONL: one record per line
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            acc = str(rec.get("acc", ""))
            if not acc or "-" in acc:                # skip isoform accessions
                continue
            frac, n_regions = _best_fraction(rec)
            if frac < MIN_COVERAGE:
                continue
            rows[acc] = dict(sequence_id=acc, sequence="", disorder_fraction=round(frac, 4),
                             n_regions=n_regions, length=int(rec.get("length") or 0),
                             annotation_source="mobidb")
            kept += 1
        print(f"  [mobidb] taxon {taxon}: {kept} above {MIN_COVERAGE} coverage")
    return list(rows.values())


def attach_sequences(rows: list[dict], chunk: int = 100) -> list[dict]:
    """Fill in sequences from UniProt for rows that lack them (the MobiDB route)."""
    from .data import MAX_LEN, MIN_LEN, _get

    need = [r for r in rows if not r["sequence"]]
    if not need:
        return rows
    print(f"[neg] fetching {len(need)} sequences from UniProt")
    by_acc = {r["sequence_id"]: r for r in need}
    accs = list(by_acc)
    for i in range(0, len(accs), chunk):
        batch = accs[i:i + chunk]
        resp = _get(UNIPROT_SEARCH,
                    params={"query": " OR ".join(f"accession:{a}" for a in batch),
                            "fields": "accession,sequence,protein_name,organism_name",
                            "format": "json", "size": str(chunk)},
                    headers={"Accept": "application/json"})
        if not resp:
            continue
        try:
            results = resp.json().get("results", [])
        except ValueError:
            continue
        for entry in results:
            row = by_acc.get(entry.get("primaryAccession", ""))
            if not row:
                continue
            name = ((entry.get("proteinDescription") or {}).get("recommendedName") or {})
            text = str(name.get("fullName", {}).get("value", "")) + " " + str(
                (entry.get("organism") or {}).get("scientificName", ""))
            if _is_protective_name(text):
                continue
            row["sequence"] = (entry.get("sequence") or {}).get("value", "")
        print(f"  {min(i + chunk, len(accs))}/{len(accs)} accessions")
    return [r for r in rows if r["sequence"] and MIN_LEN <= len(r["sequence"]) <= MAX_LEN]


def main():
    import sys

    import pandas as pd

    ds = DATA_DIR / "dataset.csv"
    existing = set()
    if ds.exists():
        df = pd.read_csv(ds, dtype=str).fillna("")
        existing = set(df["sequence_id"])
        print(f"[neg] {len(existing)} sequence_ids already in dataset.csv (will be excluded)")

    force_mobidb = "--mobidb" in sys.argv
    rows = [] if force_mobidb else fetch_via_uniprot()
    route = "uniprot_region"
    # Judge the pool by how many candidates are disordered ENOUGH to partner a positive
    # (median coverage 0.88), not by raw count — a big pool of 0.16-coverage proteins is useless.
    usable = sum(1 for r in rows if r["disorder_fraction"] >= 0.60)
    if usable < TARGET_USABLE:
        print(f"[neg] only {usable} candidates at >=0.60 coverage (want {TARGET_USABLE}); "
              "adding MobiDB.")
        rows += fetch_via_mobidb()
        route = "mobidb" if force_mobidb else "mixed"
    rows = attach_sequences(rows)

    # Drop anything already in the dataset (a positive re-found as a negative would be mislabeled).
    seen, deduped = set(), []
    for r in rows:
        if r["sequence_id"] in existing or r["sequence_id"] in seen:
            continue
        seen.add(r["sequence_id"])
        deduped.append(r)

    if not deduped:
        print("[neg] no candidates — paste this output back so the queries can be fixed.")
        return

    out = pd.DataFrame(deduped)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    frac = out["disorder_fraction"]
    print(f"\n[neg] wrote {OUT_PATH}: {len(out)} candidates (route: {route})")
    print(f"  disorder coverage: median {frac.median():.2f} "
          f"(IQR {frac.quantile(.25):.2f}-{frac.quantile(.75):.2f})")
    print(f"  length: median {out['length'].median():.0f}")
    for t in (0.5, 0.7, 0.9):
        print(f"    >= {t:.1f}: {int((frac >= t).sum())}")
    print("\n  Next: match these to the positives on BOTH disorder coverage and length, then merge"
          "\n  and re-cluster. Nothing has been added to dataset.csv yet.")


if __name__ == "__main__":
    main()
