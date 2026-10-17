# Data plan

The data decisions are what win or sink the AI track. Read all of this before pulling anything.

## Tiers

### Positives — protective
CAHS / SAHS / MAHS tardigrade disordered proteins; LEA proteins from plants, rotifers, nematodes;
other anhydrobiosis-associated IDPs. **Prefer UniProt entries with experimental evidence codes over
keyword-only annotations.** A few hundred to ~2k sequences is plenty with frozen embeddings.

### Hard negatives — *this is the whole game*
Other intrinsically disordered proteins that are **not** desiccation-protective, from **DisProt** or
**MobiDB**. "Is this protein disordered?" is trivial — composition alone solves it. "Among disordered
proteins, which ones protect?" is the real, hard question.

### Sanity tier — keep, don't lead with
Ordered globular proteins as an easy control. **Report both tasks:**
- Trivial (protective vs. ordered globular): expect ≈0.98 AUC.
- Real (protective vs. other IDPs): expect ≈0.7–0.8 AUC.

The contrast between the two is a better slide than either number alone, and it's where ESM-2 can beat
a composition baseline.

## The one rule you cannot break: split by cluster, not by row

LEA families are full of near-identical homologs. A random split or plain 5-fold CV leaks them across
train and test and inflates AUC — the most common error in protein ML.

- Cluster with **CD-HIT at 30–40% identity**.
- Split **by cluster** so no cluster appears in both train and test.

## Label provenance

Pulling positives by UniProt keyword means some labels are themselves computational annotations — you'd
risk training a model to reproduce UniProt's own pipeline. Prefer experimental evidence codes, and **say
so in the README.**

## Sources

| Source | What | URL |
| --- | --- | --- |
| UniProt | Positives (CAHS/LEA/anhydrobiosis), evidence-code filtered | https://www.uniprot.org/ |
| DisProt | Curated disordered proteins (hard negatives) | https://disprot.org/ |
| MobiDB | Disorder annotations (hard negatives) | https://mobidb.org/ |
| PDB / UniProt | Ordered globular controls (sanity tier) | — |
| CD-HIT | Clustering for the split | https://sites.google.com/view/cd-hit |

## Output of this stage

A single labeled table: `sequence_id, sequence, label (protective/other_idp/ordered), source,
evidence_code, cluster_id`. Everything downstream (embeddings, features, evals) keys off `cluster_id`
for the split.
