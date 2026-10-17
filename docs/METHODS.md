# Methods and the reasoning behind each threshold

Every numeric choice in the pipeline is either taken from published practice or derived from this
dataset. Where neither was possible, that is said plainly rather than papered over with a
confident-looking constant. Each entry gives the value, where it comes from, and what would show up
if it were wrong.

## Matching

### Caliper width — 0.2 × SD of the variable being matched on

When replacing the negatives, each positive is paired with a candidate of similar disorder coverage
and similar length. The permitted difference (the *caliper*) follows
[Austin (2011)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3120982/), whose simulations found that
a caliper of 0.2 standard deviations minimized the mean square error of the estimated effect when
continuous covariates were involved. The rule is standard in observational-study matching.

The SD is computed from **our** positives at runtime, so the caliper adapts to the data instead of
being a constant chosen in advance.

*Austin states the rule on the logit of a propensity score. We match directly on two raw covariates
rather than on a propensity score, so we apply the 0.2 × SD width to each covariate on its own
scale. The underlying statistical argument carries over; the exact simulation setting does not.*

### Balance criterion — |standardized mean difference| < 0.10

A matched set is only useful if the matched variables really are balanced afterwards. The
conventional evidence is a standardized mean difference below 0.10, which the matching literature
treats as adequate balance. `match_negatives.py` reports the SMD for both coverage and length and
states whether each clears it.

**What failure looks like:** an SMD above 0.10 means the classes still differ on a variable we
claimed to neutralize, and that difference reappears later as inflated model accuracy. The script
says so rather than continuing quietly.

A single-variable ROC-AUC is printed alongside as a second view — it should sit near 0.50 — but the
SMD is the criterion with a published threshold behind it.

## Dataset construction

### Homology splitting — CD-HIT at 40% identity, with a stated limitation

Cross-validation splits by sequence cluster, never by row, so homologs cannot appear in both training
and test. Clusters come from CD-HIT at 40% identity.

[Rost (1999)](https://www.biostat.wisc.edu/~kbroman/teaching/statgen/2004/refs/rost1.pdf) places the
"twilight zone" of sequence alignment at **20–35% identity**: above roughly 30% identity about 90% of
pairs are homologous, while below 25% fewer than 10% are.

**This is a real limitation of our split, and it should be reported.** At a 40% threshold, two
proteins that are 30% identical — likely homologous by Rost's finding — land in *different* clusters
and can therefore be split across folds. A stricter 25–30% threshold would be the conservative
choice. CD-HIT's short-word algorithm does not go below 40% reliably; reaching 30% needs PSI-CD-HIT,
which requires an all-against-all BLAST and far more runtime than this project had.

So our cluster split should be read as a **lower bound on strictness**: it removes close homologs,
not every homolog. Any residual leakage inflates the reported numbers, which means our AUCs are
optimistic rather than conservative.

### Pool floor for candidate negatives — derived, not chosen

Candidates below a minimum disorder coverage are discarded before matching. We could not find a
canonical published cutoff defining a "fully disordered protein", so rather than assert one, the
floor is set to the **5th percentile of the annotated positives' own coverage**. A candidate below
that is less disordered than virtually every protein it would be matched against and could never be
a valid partner.

### Disorder coverage — merged annotated regions ÷ sequence length

Coverage is the fraction of residues falling inside at least one annotated disordered region.
Regions overlap, so spans are merged before summing; adding raw region lengths double-counts and can
exceed 1.0.

Two sources are supported and they are **not interchangeable**: UniProt `Region: "Disordered"`
features, and MobiDB's precomputed `content_fraction`. Matching a positive measured one way against a
candidate measured the other is matching across two different rulers, so `match_negatives.py` warns
when the annotation sources differ.

Entries with **no** disorder annotation are excluded rather than treated as coverage 0.0 —
unmeasured is not the same as ordered, and conflating them would make the match partly about
curation effort instead of biology.

## Context for interpreting the results

A [MobiDB-based analysis of UniProt](https://pmc.ncbi.nlm.nih.gov/articles/PMC4384034) found that
fully disordered proteins are a **small minority** — roughly 67,000 of more than 80 million entries —
and that they are **enriched in glycine**.

Both facts bear directly on our evaluation:

- **Rarity** explains why assembling a length- and disorder-matched negative set is hard, and why the
  candidate pool is the binding constraint rather than the matching algorithm.
- **Glycine enrichment** is a property of disordered proteins *in general*. Our per-residue analysis
  found glycine strongly enriched in the positives (AUC 0.73) with bulky hydrophobics depleted
  (L 0.19, F 0.24, W 0.27, C 0.28). That is the signature of **disorder**, not specifically of
  desiccation protection — which is precisely why the negatives had to be rebuilt from proteins that
  are themselves disordered.

## Still unverified

Stated here so nobody cites them as settled:

- No published threshold defining "fully disordered" by percentage coverage was located. Our floor is
  derived from the data instead (above).
- The charge–hydropathy relationship often attributed to Uversky underlies two of our biophysical
  features (`fraction_charged`, `mean_hydropathy`). We have **not** verified that citation and it
  should be checked before appearing in the README.
