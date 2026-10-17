"""Probe candidate sources for fully-disordered, non-protective negatives. Read-only.

Owner: Data. Run on a host with network access:
    python -m tardiscreen.probe_sources

The DisProt negatives turned out to be mostly folded proteins carrying a disordered region (only 246
of 1604 reach 50% disorder coverage), so the "real" task partly re-measured folded-vs-unfolded. The
replacement negatives should be (a) genuinely disordered end to end and (b) ideally from UniProt, the
same source as the positives, which removes the source confound in the same change.

This probe does not download a dataset. It tries each candidate query, reports whether it works and
what the response actually looks like, so the real fetcher can be written against facts instead of
guesses. Nothing here is written to disk.
"""

from __future__ import annotations

import json

UNIPROT = "https://rest.uniprot.org/uniprotkb/search"

# UniProt stores disorder as Region features whose description is "Disordered" (from MobiDB-lite).
# Query syntax for feature search has changed across releases, so try several spellings.
CANDIDATES = [
    ("uniprot: ft_region disordered, reviewed", UNIPROT, {
        "query": "(ft_region:disordered) AND (reviewed:true)",
        "fields": "accession,length,ft_region,protein_name",
        "format": "json", "size": "3"}),
    ("uniprot: annotation type region + disordered text", UNIPROT, {
        "query": '(annotation:(type:region "Disordered")) AND (reviewed:true)',
        "fields": "accession,length,ft_region,protein_name",
        "format": "json", "size": "3"}),
    ("uniprot: plain keyword, reviewed", UNIPROT, {
        "query": "disordered AND (reviewed:true)",
        "fields": "accession,length,ft_region,protein_name",
        "format": "json", "size": "3"}),
    ("mobidb: curated disorder, human", "https://mobidb.org/api/download", {
        "ncbi_taxon_id": "9606", "format": "json", "limit": "3"}),
]


def _summarize_uniprot(payload: dict) -> None:
    """Report whether the returned entries actually carry usable Disordered regions."""
    results = payload.get("results", [])
    print(f"    entries returned: {len(results)}")
    if not results:
        return
    entry = results[0]
    print(f"    entry keys: {sorted(entry)[:10]}")
    feats = entry.get("features", [])
    print(f"    features on first entry: {len(feats)}")
    kinds = {f.get("type") for f in feats if isinstance(f, dict)}
    print(f"    feature types: {sorted(k for k in kinds if k)[:8]}")
    for f in feats:
        if not isinstance(f, dict):
            continue
        desc = str(f.get("description", ""))
        if "disorder" in desc.lower() or str(f.get("type", "")).lower() == "region":
            loc = f.get("location", {})
            start = (loc.get("start") or {}).get("value")
            end = (loc.get("end") or {}).get("value")
            print(f"    sample region -> type={f.get('type')!r} desc={desc!r} "
                  f"start={start} end={end}")
            break
    else:
        print("    NOTE: no region-like feature found on the first entry.")


def main():
    from .data import _get

    print("Probing candidate sources for fully-disordered negatives.\n")
    for name, url, params in CANDIDATES:
        print(f"[{name}]")
        print(f"  {url}  params={ {k: v for k, v in params.items() if k != 'fields'} }")
        resp = _get(url, params=params, headers={"Accept": "application/json"}, tries=2)
        if not resp:
            print("  -> FAILED (no 200 response)\n")
            continue
        try:
            payload = resp.json()
        except ValueError:
            print(f"  -> non-JSON response, first 200 chars: {resp.text[:200]!r}\n")
            continue

        total = resp.headers.get("x-total-results")
        print(f"  -> OK. x-total-results: {total}")
        if isinstance(payload, dict) and "results" in payload:
            _summarize_uniprot(payload)
        else:
            entries = payload if isinstance(payload, list) else [payload]
            print(f"    top-level: {type(payload).__name__}, {len(entries)} entries")
            if entries and isinstance(entries[0], dict):
                print(f"    entry keys: {sorted(entries[0])[:14]}")
                disorder_keys = [k for k in entries[0] if "disorder" in k.lower()]
                print(f"    disorder-ish keys: {disorder_keys[:6]}")
                if disorder_keys:
                    val = entries[0][disorder_keys[0]]
                    print(f"    sample value: {json.dumps(val)[:200]}")
        print()

    print("Paste this whole output back. The winning query becomes the new negative pull:\n"
          "  reviewed, disorder coverage >= 0.7, protective terms excluded, length-matched to the\n"
          "  positives. Same source as the positives also removes the source confound.")


if __name__ == "__main__":
    main()
