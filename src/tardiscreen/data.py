"""Pull and label the training set.

Owner: Data. See docs/DATA_PLAN.md for the tiers and the cluster-split rule — that doc is the spec
for this file.

The goal of this module is one labeled table:
    sequence_id, sequence, label, source, evidence_code, cluster_id

where label ∈ {"protective", "other_idp", "ordered"} and cluster_id comes from CD-HIT.

Run from the repo root:
    pip install -e .          # or: pip install -r requirements.txt
    python -m tardiscreen.data

Sizing note: HaloClass (halophilic-protein predictor) trained on ~28,030 sequences after CD-HIT at
50% identity. Desiccation-protective proteins are far rarer, so we do NOT chase that number — we keep
every positive we find (expect a few hundred to ~2000) and cap each negative tier at ~1.5x the
positives, down-sampling by cluster. We also cluster more strictly (40% identity vs. HaloClass's 50%).
"""

from __future__ import annotations

import csv
import io
import os
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
LABELS = ("protective", "other_idp", "ordered")

# --- knobs ------------------------------------------------------------------------------------------
MIN_LEN, MAX_LEN = 40, 1500            # length filter (aa)
NEG_RATIO = 1.5                        # cap each negative tier at NEG_RATIO x positive count
ORDERED_MAX = 6000                     # generous fetch bound for the ordered tier (balancing trims it)
MIN_PER_LABEL = 150                    # acceptance floor
HTTP_TIMEOUT = 120                     # seconds
PRIORITY = {"protective": 0, "other_idp": 1, "ordered": 2}  # who wins a label conflict

# HaloClass benchmark, for the side-note.
HALOCLASS_N, HALOCLASS_IDENTITY = 28_030, 0.50

# Terms that mark a "disordered" protein as actually desiccation-related — drop it from the negatives.
PROTECTIVE_DROP_TERMS = (
    "desiccation", "anhydrobiosis", "lea", "late embryogenesis",
    "cahs", "sahs", "mahs", "dehydrin", "hydrophilin", "cryoprotect",
)
# UniProt protein-name synonyms for the protective families.
POSITIVE_NAME_TERMS = (
    "CAHS", '"cytoplasmic abundant heat soluble"', "SAHS", "MAHS", "LEA",
    '"late embryogenesis abundant"', "dehydrin", "hydrophilin",
)

UNIPROT_FIELDS = "accession,sequence,protein_name,protein_existence,reviewed,length"
EXPERIMENTAL = "Evidence at protein level"


def _seed() -> int:
    """The config seed if the project grows one, else 42."""
    try:
        from .config import SEED  # type: ignore
        return int(SEED)
    except Exception:
        return 42


@dataclass
class Record:
    sequence_id: str
    sequence: str
    label: str
    source: str
    evidence_code: str = ""
    cluster_id: str = ""


# ---------------------------------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------------------------------
def _get(url: str, params: dict | None = None, *, headers: dict | None = None, tries: int = 4):
    """GET with a few retries. Returns the response or None (never raises for the caller)."""
    for i in range(tries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
            if resp.status_code == 200:
                return resp
            print(f"[http] {url} -> {resp.status_code} (attempt {i + 1}/{tries})")
        except requests.RequestException as exc:
            print(f"[http] {url} failed: {exc} (attempt {i + 1}/{tries})")
        if i < tries - 1:
            import time
            time.sleep(2 ** i)
    return None


def _parse_uniprot_tsv(text: str) -> list[dict]:
    """Parse UniProt TSV (header line + tab-separated rows) into dicts."""
    rows: list[dict] = []
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for row in reader:
        rows.append(row)
    return rows


def _uniprot_fetch(query: str, *, max_records: int | None = None) -> list[dict]:
    """Fetch UniProtKB rows for `query`.

    max_records=None streams the full result set (use for small queries like the positives).
    A number uses the paginated search endpoint and stops once that many rows are collected
    (use to bound a large tier like the ordered controls).
    """
    if max_records is None:
        resp = _get(
            "https://rest.uniprot.org/uniprotkb/stream",
            params={"query": query, "format": "tsv", "fields": UNIPROT_FIELDS},
        )
        return _parse_uniprot_tsv(resp.text) if resp else []

    rows: list[dict] = []
    url = "https://rest.uniprot.org/uniprotkb/search"
    params: dict | None = {
        "query": query, "format": "tsv", "fields": UNIPROT_FIELDS,
        "size": str(min(500, max_records)),
    }
    while url and len(rows) < max_records:
        resp = _get(url, params=params)
        if not resp:
            break
        rows.extend(_parse_uniprot_tsv(resp.text))
        # UniProt paginates with a Link: <...>; rel="next" header.
        nxt = resp.links.get("next", {}).get("url")
        url, params = nxt, None
    return rows[:max_records]


def _row_to_record(row: dict, label: str) -> Record:
    return Record(
        sequence_id=(row.get("Entry") or row.get("accession") or "").strip(),
        sequence=(row.get("Sequence") or row.get("sequence") or "").strip(),
        label=label,
        source="uniprot",
        evidence_code=(row.get("Protein existence") or row.get("protein_existence") or "").strip(),
    )


# ---------------------------------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------------------------------
def fetch_positives() -> list[Record]:
    """Protective IDPs (CAHS/SAHS/MAHS, LEA, dehydrins, hydrophilins, anhydrobiosis) from UniProt.

    We keep every hit (these proteins are rare) and sort entries with experimental evidence first, so
    the honest-provenance share is easy to report. Evidence comes from UniProt's `protein_existence`.
    """
    name_q = " OR ".join(f"protein_name:{t}" for t in POSITIVE_NAME_TERMS)
    # A free-text/keyword net over all of UniProtKB returns ~59k mostly computationally-annotated
    # hits (existence 3=homology / 4=predicted) — training on those just reproduces UniProt's own
    # pipeline. Keep curated Swiss-Prot (reviewed:true) OR entries with real experimental support
    # (existence:1 = evidence at protein level, existence:2 = transcript level). reviewed:true alone
    # gave only ~102; this adds experimentally-backed TrEMBL without the predicted-homology noise.
    query = f"(({name_q}) OR keyword:anhydrobiosis) AND (reviewed:true OR existence:1 OR existence:2)"
    rows = _uniprot_fetch(query)
    records = [_row_to_record(r, "protective") for r in rows]
    records = [r for r in records if r.sequence_id and r.sequence]
    # Experimental ("Evidence at protein level") first — these are the most trustworthy labels.
    records.sort(key=lambda r: 0 if r.evidence_code == EXPERIMENTAL else 1)

    if not records:
        print("[positives] WARNING: UniProt returned no protective sequences.")
        print("            Would change: drop `AND reviewed:true` to include TrEMBL, add taxon terms "
              "(taxonomy_name:Tardigrada OR Rotifera OR Nematoda), or broaden to family:LEA / "
              "family:CAHS.")
    else:
        n_exp = sum(r.evidence_code == EXPERIMENTAL for r in records)
        print(f"[positives] {len(records)} sequences ({n_exp} with experimental evidence) from UniProt")
    return records


def _disprot_text_blob(entry: dict) -> str:
    """Everything about a DisProt entry we can scan for protective-family hints."""
    parts = [str(entry.get("name", "")), str(entry.get("organism", "")),
             str(entry.get("ncbi_taxon_name", ""))]
    for region in entry.get("regions", []) or []:
        if isinstance(region, dict):
            parts.append(str(region.get("term_name", "")))
            parts.append(str(region.get("term_namespace", "")))
    for feat in entry.get("features", []) or []:
        if isinstance(feat, dict):
            parts.append(str(feat.get("name", "")))
    return " ".join(parts).lower()


def fetch_hard_negatives() -> list[Record]:
    """Disordered proteins that are NOT desiccation-protective, from DisProt.

    This is the group that makes the project meaningful: "among disordered proteins, which protect?"
    We drop any entry whose name/organism/annotations mention a protective family or desiccation.
    """
    from .build_negatives import _is_protective_name

    resp = _get(
        "https://disprot.org/api/search",
        params={"release": "current", "show_ambiguous": "true", "show_obsolete": "false",
                "format": "json"},
        headers={"Accept": "application/json"},
    )
    if not resp:
        print("[hard_neg] WARNING: DisProt returned nothing.")
        print("           Would change: retry https://disprot.org/api/search without the release "
              "pin, or fall back to MobiDB (https://mobidb.org/api/download?proteome=... or "
              "?ncbi_taxon_id=9606&format=json) filtered to curated-disorder entries.")
        return []

    try:
        payload = resp.json()
    except ValueError:
        print("[hard_neg] WARNING: DisProt response was not JSON."); return []
    entries = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        print("[hard_neg] WARNING: unexpected DisProt JSON shape."); return []

    records, dropped = [], 0
    for e in entries:
        seq = (e.get("sequence") or "").strip()
        sid = (e.get("acc") or e.get("disprot_id") or "").strip()
        if not seq or not sid:
            continue
        if _is_protective_name(_disprot_text_blob(e)):
            dropped += 1
            continue
        records.append(Record(sequence_id=sid, sequence=seq, label="other_idp",
                              source="disprot", evidence_code="disprot-curated"))

    if not records:
        print("[hard_neg] WARNING: no disordered negatives survived filtering.")
        print("           Would change: loosen the drop-term list or add MobiDB as a second source.")
    else:
        print(f"[hard_neg] {len(records)} disordered negatives from DisProt "
              f"({dropped} dropped as protective-related)")
    return records


def fetch_sanity_negatives() -> list[Record]:
    """Ordered globular proteins — the easy control tier. Keep, don't lead with.

    UniProt reviewed entries that have a 3D structure, excluding anything named like a protective
    family. Bounded by ORDERED_MAX; the balancing step trims it to ~1.5x the positives.
    """
    exclude = " OR ".join(f"protein_name:{t}" for t in POSITIVE_NAME_TERMS)
    query = f"(structure_3d:true AND reviewed:true) NOT ({exclude})"
    rows = _uniprot_fetch(query, max_records=ORDERED_MAX)
    records = [_row_to_record(r, "ordered") for r in rows]
    records = [r for r in records if r.sequence_id and r.sequence]

    if not records:
        print("[ordered] WARNING: UniProt returned no ordered controls.")
        print("          Would change: relax to (structure_3d:true) without reviewed:true, or use "
              "(xref:pdb AND reviewed:true).")
    else:
        print(f"[ordered] {len(records)} ordered controls from UniProt (bound {ORDERED_MAX})")
    return records


# ---------------------------------------------------------------------------------------------------
# Clustering + cleaning + balancing  (all cleaning/merging/dedup happens here, in pandas)
# ---------------------------------------------------------------------------------------------------
_STD_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _clean_seq(seq: str) -> str:
    return "".join(c for c in str(seq).upper() if c in _STD_AA)


def _kmers(seq: str, k: int = 3) -> set[str]:
    return {seq[i:i + k] for i in range(len(seq) - k + 1)} if len(seq) >= k else {seq}


def _greedy_cluster(seqs: dict[str, str], identity: float) -> dict[str, str]:
    """Dependency-free fallback: greedy k-mer containment clustering. Provisional, not CD-HIT."""
    reps: list[tuple[set[str], str]] = []
    mapping: dict[str, str] = {}
    cid = 0
    for sid, seq in sorted(seqs.items(), key=lambda kv: len(kv[1]), reverse=True):
        ks = _kmers(seq)
        assigned = None
        for rset, rc in reps:
            denom = min(len(ks), len(rset)) or 1
            if len(ks & rset) / denom >= identity:
                assigned = rc
                break
        if assigned is None:
            assigned = f"c{cid}"
            reps.append((ks, assigned))
            cid += 1
        mapping[sid] = assigned
    return mapping


def _parse_clstr(path: Path) -> dict[str, str]:
    mapping, current = {}, None
    with path.open() as f:
        for line in f:
            if line.startswith(">"):
                current = "c" + line.split()[-1]
            elif ">" in line:
                sid = line.split(">", 1)[1].split("...")[0].strip()
                if current is not None:
                    mapping[sid] = current
    return mapping


def _cdhit_cluster(seqs: dict[str, str], identity: float) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        fasta = Path(tmp) / "in.fasta"
        out = Path(tmp) / "out"
        with fasta.open("w") as f:
            for sid, seq in seqs.items():
                f.write(f">{sid}\n{seq}\n")
        cmd = ["cd-hit", "-i", str(fasta), "-o", str(out),
               "-c", str(identity), "-n", "2", "-d", "0", "-M", "0", "-T", "0"]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return _parse_clstr(out.with_suffix(".clstr") if out.suffix else Path(str(out) + ".clstr"))


def _cluster_ids(seqs: dict[str, str], identity: float) -> dict[str, str]:
    if shutil.which("cd-hit"):
        try:
            mapping = _cdhit_cluster(seqs, identity)
            if mapping:
                print(f"[cluster] CD-HIT at {identity:.0%} identity -> "
                      f"{len(set(mapping.values()))} clusters")
                return mapping
            print("[cluster] CD-HIT produced no clusters; using greedy fallback.")
        except (subprocess.CalledProcessError, OSError) as exc:
            print(f"[cluster] CD-HIT failed ({exc}); using greedy fallback.")
    else:
        print("[cluster] cd-hit not on PATH — using greedy k-mer clustering.")
    mapping = _greedy_cluster(seqs, identity)
    print(f"[cluster] PROVISIONAL greedy clustering -> {len(set(mapping.values()))} clusters "
          f"(install cd-hit for a real result)")
    return mapping


def cluster_sequences(records: list[Record], identity: float = 0.4) -> list[Record]:
    """Clean, dedup, cluster (CD-HIT at `identity`, 40% by default), resolve label conflicts, and
    balance the negatives — returning records that all carry a non-empty, single-label cluster_id.

    See docs/DATA_PLAN.md. Everything here is done in pandas; each step reports how many rows it drops.
    """
    if not records:
        print("[cluster] no records to process.")
        return records

    df = pd.DataFrame([r.__dict__ for r in records])

    # 1. Normalize sequences; drop empty / non-standard-only.
    n = len(df)
    df["sequence"] = df["sequence"].map(_clean_seq)
    df = df[df["sequence"].str.len() > 0]
    print(f"[clean] dropped {n - len(df)} empty / non-standard-residue sequences")

    # 2. Length filter.
    n = len(df)
    lengths = df["sequence"].str.len()
    df = df[(lengths >= MIN_LEN) & (lengths <= MAX_LEN)]
    print(f"[clean] dropped {n - len(df)} sequences outside {MIN_LEN}-{MAX_LEN} aa")

    # 3. A positive identical to any negative sequence is suspect — drop the positive.
    neg_seqs = set(df.loc[df["label"] != "protective", "sequence"])
    suspect = (df["label"] == "protective") & (df["sequence"].isin(neg_seqs))
    print(f"[clean] dropped {int(suspect.sum())} positives identical to a negative sequence")
    df = df[~suspect]

    # 4. Deduplicate: exact sequence, then sequence_id. Keep the higher-priority label on conflicts.
    df["_prio"] = df["label"].map(PRIORITY).fillna(max(PRIORITY.values()) + 1)
    df = df.sort_values(["_prio", "sequence_id"])
    n = len(df)
    df = df.drop_duplicates(subset="sequence", keep="first")
    print(f"[clean] dropped {n - len(df)} exact-duplicate sequences")
    n = len(df)
    df = df.drop_duplicates(subset="sequence_id", keep="first")
    print(f"[clean] dropped {n - len(df)} duplicate sequence_ids")

    if df.empty:
        print("[cluster] nothing left after cleaning.")
        return []

    # 5. Cluster everything together (so homologs across tiers share a cluster).
    mapping = _cluster_ids(dict(zip(df["sequence_id"], df["sequence"])), identity)
    df["cluster_id"] = df["sequence_id"].map(mapping)
    # Guarantee every record has a cluster_id (singletons for any the clusterer missed).
    missing = df["cluster_id"].isna()
    if missing.any():
        for i, idx in enumerate(df.index[missing]):
            df.at[idx, "cluster_id"] = f"solo{i}"
        print(f"[cluster] assigned {int(missing.sum())} singleton cluster_ids")

    # 6. A cluster that spans labels is a cross-tier homolog — keep the highest-priority label in it,
    #    drop the rest, so no cluster_id spans two labels (and homologs can't leak across the split).
    keep_label = (df.sort_values("_prio").groupby("cluster_id")["label"].first())
    df["_keep"] = df["cluster_id"].map(keep_label)
    spanning = df["label"] != df["_keep"]
    if spanning.any():
        print(f"[cluster] dropped {int(spanning.sum())} records in label-spanning clusters "
              f"(kept the higher-priority label per cluster)")
    df = df[~spanning].drop(columns=["_keep"])

    # 7. Balance: cap each negative tier at ~NEG_RATIO x positives, down-sampling by whole clusters.
    pos = df[df["label"] == "protective"]
    if pos.empty:
        print("[balance] WARNING: no positives — skipping down-sampling so the shortfall is visible.")
    else:
        cap = round(NEG_RATIO * len(pos))
        rng = random.Random(_seed())
        keep_idx = list(pos.index)
        # Derive the negative tiers from the data: hardcoding them silently drops any label not
        # listed (a new negative tier would vanish here with no message).
        neg_labels = [l for l in df["label"].unique() if l != "protective"]
        for lbl in neg_labels:
            sub = df[df["label"] == lbl]
            if len(sub) <= cap:
                keep_idx.extend(sub.index)
                continue
            clusters = list(sub["cluster_id"].unique())
            rng.shuffle(clusters)
            chosen, total = [], 0
            for c in clusters:
                members = sub.index[sub["cluster_id"] == c]
                if total + len(members) > cap:
                    continue  # don't split a cluster; skip and try the next
                chosen.extend(members)
                total += len(members)
            keep_idx.extend(chosen)
            print(f"[balance] {lbl}: {len(sub)} -> {total} (cap {cap}, by cluster, seed {_seed()})")
        df = df.loc[keep_idx]

    df = df.drop(columns=["_prio"])
    print(f"[cluster] final: {len(df)} records, {df['cluster_id'].nunique()} clusters")
    return [Record(**row) for row in df[list(Record.__dataclass_fields__)].to_dict("records")]


def write_table(records: list[Record], path: Path | None = None) -> Path:
    path = path or DATA_DIR / "dataset.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sequence_id", "sequence", "label", "source", "evidence_code", "cluster_id"])
        for r in records:
            w.writerow([r.sequence_id, r.sequence, r.label, r.source, r.evidence_code, r.cluster_id])
    return path


def build() -> Path:
    records = fetch_positives() + fetch_hard_negatives() + fetch_sanity_negatives()
    records = cluster_sequences(records)
    return write_table(records)


# ---------------------------------------------------------------------------------------------------
# Summary + acceptance checks (run after build; build() itself is unchanged)
# ---------------------------------------------------------------------------------------------------
def _write_summary(df: pd.DataFrame, path: Path) -> Path:
    lines = ["# Dataset summary", ""]
    lines.append(f"Total sequences: **{len(df)}**, in **{df['cluster_id'].nunique()}** clusters.")
    lines.append("")
    lines.append("| label | sequences | clusters | len min | len median | len max |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for lbl in LABELS:
        sub = df[df["label"] == lbl]
        if sub.empty:
            lines.append(f"| {lbl} | 0 | 0 | — | — | — |")
            continue
        ln = sub["sequence"].str.len()
        lines.append(f"| {lbl} | {len(sub)} | {sub['cluster_id'].nunique()} | "
                     f"{int(ln.min())} | {int(ln.median())} | {int(ln.max())} |")

    pos = df[df["label"] == "protective"]
    pct_exp = 100 * (pos["evidence_code"] == EXPERIMENTAL).mean() if len(pos) else 0.0
    lines += ["", f"Positives with experimental evidence "
                  f"(`{EXPERIMENTAL}`): **{pct_exp:.1f}%**.", ""]
    lines.append(f"> Benchmark: HaloClass trained on {HALOCLASS_N:,} sequences after CD-HIT at "
                 f"{HALOCLASS_IDENTITY:.0%}. Desiccation proteins are far rarer, so our N is "
                 f"intentionally small and we cluster more strictly (40%).")
    path.write_text("\n".join(lines) + "\n")
    return path


def _acceptance_checks(df: pd.DataFrame) -> bool:
    print("\n=== acceptance checks ===")
    ok = True

    for lbl in LABELS:
        count = int((df["label"] == lbl).sum())
        status = "OK" if count >= MIN_PER_LABEL else "LOW"
        print(f"  [{status}] {lbl}: {count} (floor {MIN_PER_LABEL})")
        if count < MIN_PER_LABEL:
            ok = False
            if lbl == "protective":
                print("    -> loosen fetch_positives: drop `AND reviewed:true` to include TrEMBL, "
                      "add taxon terms (taxonomy_name:Tardigrada OR Rotifera OR Nematoda), or add "
                      "family:LEA / family:CAHS to raise recall.")

    multi = df.groupby("sequence_id")["label"].nunique()
    bad_ids = multi[multi > 1]
    print(f"  [{'OK' if bad_ids.empty else 'FAIL'}] sequence_ids under exactly one label "
          f"({len(bad_ids)} violations)")
    ok = ok and bad_ids.empty

    empty_clusters = int(df["cluster_id"].fillna("").eq("").sum())
    print(f"  [{'OK' if empty_clusters == 0 else 'FAIL'}] every record has a cluster_id "
          f"({empty_clusters} missing)")
    ok = ok and empty_clusters == 0

    span = df.groupby("cluster_id")["label"].nunique()
    bad_clusters = span[span > 1]
    print(f"  [{'OK' if bad_clusters.empty else 'FAIL'}] no cluster_id spans two labels "
          f"({len(bad_clusters)} violations)")
    ok = ok and bad_clusters.empty

    print(f"  side-note: our N={len(df)} @ 40% identity vs. HaloClass {HALOCLASS_N:,} @ "
          f"{HALOCLASS_IDENTITY:.0%}.")
    print("=========================\n")
    return ok


if __name__ == "__main__":
    out = build()
    print(f"Wrote dataset to {out}")
    df = pd.read_csv(out, dtype=str).fillna("")
    if df.empty:
        print("Dataset is empty — see the per-source warnings above before running checks.")
    else:
        summary = _write_summary(df, DATA_DIR / "dataset_summary.md")
        print(f"Wrote summary to {summary}")
        _acceptance_checks(df)
