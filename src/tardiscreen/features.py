"""Interpretable biophysical features for a protein sequence.

These are the features behind the "why" readout and the fallback model that still runs if the
embedding pipeline stalls. They are standard IDP descriptors; keep them transparent and easy to
explain to a judge.

All functions take a plain amino-acid string (one-letter codes, upper-case) and are pure.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

AA = "ACDEFGHIKLMNPQRSTVWY"

# Kyte-Doolittle hydropathy scale.
KD_HYDROPATHY = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

POSITIVE = set("KR")   # charged + at physiological pH (His treated as ~neutral here)
NEGATIVE = set("DE")   # charged -
CHARGED = POSITIVE | NEGATIVE


def clean_sequence(seq: str) -> str:
    """Upper-case and drop anything that isn't one of the 20 standard residues."""
    return "".join(c for c in seq.upper() if c in AA)


def fraction_charged(seq: str) -> float:
    """FCR — fraction of charged residues."""
    if not seq:
        return 0.0
    return sum(1 for c in seq if c in CHARGED) / len(seq)


def net_charge_per_residue(seq: str) -> float:
    """NCPR — (count + minus count -) / length."""
    if not seq:
        return 0.0
    return (sum(c in POSITIVE for c in seq) - sum(c in NEGATIVE for c in seq)) / len(seq)


def mean_hydropathy(seq: str) -> float:
    """Mean Kyte-Doolittle hydropathy. Lower = more hydrophilic (typical of IDPs)."""
    if not seq:
        return 0.0
    return sum(KD_HYDROPATHY[c] for c in seq) / len(seq)


def residue_enrichment(seq: str, residues: str) -> float:
    """Fraction of the sequence made up of the given residues (e.g. 'GSH')."""
    if not seq:
        return 0.0
    wanted = set(residues)
    return sum(1 for c in seq if c in wanted) / len(seq)


def low_complexity_fraction(seq: str, window: int = 20, threshold: float = 2.2) -> float:
    """Fraction of windows whose Shannon entropy (bits) falls below `threshold`.

    Low-complexity / repetitive regions are common in protective IDPs. A full LCR caller (e.g. SEG)
    is better; this is a fast, dependency-free proxy good enough for a weekend.
    """
    import math

    if len(seq) < window:
        window = len(seq)
    if window == 0:
        return 0.0
    low = 0
    n = 0
    for i in range(0, len(seq) - window + 1):
        counts = Counter(seq[i : i + window])
        entropy = -sum((c / window) * math.log2(c / window) for c in counts.values())
        low += entropy < threshold
        n += 1
    return low / n if n else 0.0


@dataclass
class Features:
    length: int
    fraction_charged: float
    net_charge_per_residue: float
    mean_hydropathy: float
    glycine: float
    serine: float
    histidine: float
    gly_ser_his: float
    low_complexity: float

    def as_dict(self) -> dict:
        return asdict(self)


def compute_features(seq: str) -> Features:
    """Full interpretable feature vector for one sequence.

    TODO (model owner): add a predicted-disorder feature (e.g. IUPred/metapredict) — it's one of the
    strongest IDP signals but needs an extra dependency, so it's left out of the dependency-free core.
    """
    s = clean_sequence(seq)
    return Features(
        length=len(s),
        fraction_charged=fraction_charged(s),
        net_charge_per_residue=net_charge_per_residue(s),
        mean_hydropathy=mean_hydropathy(s),
        glycine=residue_enrichment(s, "G"),
        serine=residue_enrichment(s, "S"),
        histidine=residue_enrichment(s, "H"),
        gly_ser_his=residue_enrichment(s, "GSH"),
        low_complexity=low_complexity_fraction(s),
    )


FEATURE_NAMES = [f.name for f in Features.__dataclass_fields__.values()]  # type: ignore[attr-defined]


if __name__ == "__main__":
    # A CAHS-like toy: Gly/Ser-rich, highly charged, hydrophilic.
    demo = "MSGSGSGKEKEKDKDKGSGSGSHGHGSGSEKEKDKDKGSGSGSGHKGHGSGS"
    for k, v in compute_features(demo).as_dict().items():
        print(f"{k:>24}: {v}")
