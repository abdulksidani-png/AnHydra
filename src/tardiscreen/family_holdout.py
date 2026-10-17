"""Leave-one-family-out: can either method recognize a protective family it has never seen?

Owner: Model. Needs BLAST+ and network access on the first run:
    python -m tardiscreen.family_holdout

The stratified comparison showed that "does this protein have a close relative in the training set?"
is almost the entire classifier. Sequences with no alignment hit were 12% positive; sequences with a
hit were 78-85% positive. The positives are a few dense families (CAHS, LEA, dehydrins) whose
members remain related even after a 40% identity split, while the negatives are unrelated singletons.
So BLAST and ESM-2 both score ~0.98 by detecting family density, not protective character.

This removes that advantage. Train on every family except one, test on the held-out family, rotate.
The test family has no relatives in training, so alignment has nothing to match. If the language
model retains signal there, it is responding to protective character itself — which is the actual
scientific claim, and the actual product case: finding protective proteins that belong to no known
family.

Expect much lower numbers than 0.99. That is the point; the question is finally hard.
"""

from __future__ import annotations

import re

import numpy as np

from .blast_baseline import _blast_fold, _require_blast
from .evaluate import DATA_DIR, SEED, _classifier, _load, _matrix

FAMILIES_PATH = DATA_DIR / "families.csv"
MIN_FAMILY = 25          # below this a held-out family cannot support an AUC worth reporting

# Ordered: the first pattern that matches wins, so specific names beat generic ones.
FAMILY_PATTERNS = (
    ("CAHS", r"\bcahs\b|cytoplasmic abundant heat soluble"),
    ("SAHS", r"\bsahs\b|secretory abundant heat soluble"),
    ("MAHS", r"\bmahs\b|mitochondrial abundant heat soluble"),
    ("dehydrin", r"dehydrin"),
    ("LEA", r"\blea\b|late embryogenesis abundant"),
    ("hydrophilin", r"hydrophilin"),
)


def assign_family(name: str) -> str:
    low = name.lower()
    for family, pattern in FAMILY_PATTERNS:
        if re.search(pattern, low):
            return family
    return "other"


def fetch_families(accessions: list[str], chunk: int = 100):
    """Protein names from UniProt -> family labels. Cached to data/families.csv."""
    import pandas as pd

    from .data import _get

    if FAMILIES_PATH.exists():
        cached = pd.read_csv(FAMILIES_PATH, dtype=str)
        if set(accessions) <= set(cached["sequence_id"]):
            print(f"[family] using cached {FAMILIES_PATH}")
            return cached
        print("[family] cache is missing some accessions — refetching")

    rows = []
    for i in range(0, len(accessions), chunk):
        batch = accessions[i:i + chunk]
        resp = _get("https://rest.uniprot.org/uniprotkb/search",
                    params={"query": " OR ".join(f"accession:{a}" for a in batch),
                            "fields": "accession,protein_name", "format": "json",
                            "size": str(chunk)},
                    headers={"Accept": "application/json"})
        if not resp:
            continue
        try:
            results = resp.json().get("results", [])
        except ValueError:
            continue
        for entry in results:
            desc = entry.get("proteinDescription") or {}
            name = ((desc.get("recommendedName") or {}).get("fullName") or {}).get("value", "")
            if not name:
                subs = desc.get("submissionNames") or []
                name = ((subs[0] if subs else {}).get("fullName") or {}).get("value", "")
            rows.append(dict(sequence_id=entry.get("primaryAccession", ""),
                             protein_name=name, family=assign_family(name)))
        print(f"  [family] {min(i + chunk, len(accessions))}/{len(accessions)}")

    out = pd.DataFrame(rows, columns=["sequence_id", "protein_name", "family"])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(FAMILIES_PATH, index=False)
    print(f"[family] wrote {FAMILIES_PATH}")
    return out


def _negative_folds(neg_clusters: np.ndarray, k: int) -> list[np.ndarray]:
    """Split negative row indices into k groups by cluster, so no cluster spans two folds."""
    rng = np.random.default_rng(SEED)
    clusters = np.unique(neg_clusters)
    rng.shuffle(clusters)
    assignment = {c: i % k for i, c in enumerate(clusters)}
    return [np.flatnonzero(np.array([assignment[c] for c in neg_clusters]) == i)
            for i in range(k)]


def _holdout_train_indices(groups, test):
    """Exclude every test cluster, including clusters spanning protective family names."""
    groups = np.asarray(groups)
    return np.flatnonzero(~np.isin(groups, groups[test]))


def main():
    import pandas as pd
    from sklearn.metrics import roc_auc_score

    _require_blast()
    df, emb = _load()

    sub = df[df["label"].isin(["protective", "idp_matched"])]
    if "in_matched_set" in sub.columns:
        sub = sub[sub["in_matched_set"].astype(str).str.lower().isin(("true", "1"))]
    sub = sub.reset_index(drop=True)

    pos_ids = sub.loc[sub["label"] == "protective", "sequence_id"].tolist()
    fam = fetch_families(pos_ids)
    fam_by_id = dict(zip(fam["sequence_id"], fam["family"]))
    sub["family"] = sub["sequence_id"].map(fam_by_id).fillna("other")
    sub.loc[sub["label"] != "protective", "family"] = "negative"

    counts = sub[sub["label"] == "protective"]["family"].value_counts()
    print(f"\n[family] positives by family:\n{counts.to_string()}")
    testable = [f for f, n in counts.items() if n >= MIN_FAMILY and f != "other"]
    if not testable:
        print(f"\n[family] no family has >= {MIN_FAMILY} members — cannot hold one out.")
        return

    y_all = (sub["label"] == "protective").astype(int).to_numpy()
    X = _matrix(sub, emb, "esm2")
    ids, seqs = sub["sequence_id"].tolist(), sub["sequence"].tolist()
    neg_idx = np.flatnonzero(y_all == 0)
    neg_folds = _negative_folds(sub.loc[neg_idx, "cluster_id"].to_numpy(), len(testable))

    print(f"\n[family] holding out, one at a time: {', '.join(testable)}")
    rows = []
    for i, family in enumerate(testable):
        test_pos = np.flatnonzero((y_all == 1) & (sub["family"] == family).to_numpy())
        test_neg = neg_idx[neg_folds[i]]
        test = np.concatenate([test_pos, test_neg])
        train = _holdout_train_indices(sub["cluster_id"].to_numpy(), test)
        # No positive of the held-out family may remain in training.
        train = train[~((y_all[train] == 1) & (sub["family"].to_numpy()[train] == family))]

        y_te = y_all[test]
        if len(set(y_te)) < 2:
            print(f"  {family}: only one class in the test split — skipped")
            continue
        if len(set(y_all[train])) < 2:
            print(f"  {family}: only one class remains in training — skipped")
            continue

        esm = _classifier().fit(X[train], y_all[train]).predict_proba(X[test])[:, 1]
        blast = _blast_fold([ids[i] for i in train], [seqs[i] for i in train], y_all[train],
                            [ids[i] for i in test], [seqs[i] for i in test])
        a_esm, a_blast = roc_auc_score(y_te, esm), roc_auc_score(y_te, blast)
        print(f"  {family:>12}: {len(test_pos):>4} held-out positives vs {len(test_neg):>4} "
              f"negatives   BLAST {a_blast:.3f}   ESM-2 {a_esm:.3f}   diff {a_esm - a_blast:+.3f}")
        rows.append(dict(family=family, n_pos=len(test_pos), n_neg=len(test_neg),
                         blast_auc=a_blast, esm2_auc=a_esm))

    if not rows:
        return
    res = pd.DataFrame(rows)
    res.to_csv(DATA_DIR / "family_holdout.csv", index=False)
    print(f"\n[family] mean over held-out families: BLAST {res['blast_auc'].mean():.3f}   "
          f"ESM-2 {res['esm2_auc'].mean():.3f}")
    print(f"[family] wrote {DATA_DIR / 'family_holdout.csv'}")
    print("\n  Read: these are the honest generalization numbers. Scores far below the 0.99 of the"
          "\n  within-family split mean that result was family recognition. Whatever survives here"
          "\n  is protective character detected without a known relative — the claim worth making.")


if __name__ == "__main__":
    main()
