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

## How we interrogated our own result

The real task first scored **0.987**, far above the 0.7–0.8 we had predicted. We treated that as a
problem rather than a success and tested four explanations for it.

| # | hypothesis | test | outcome |
| --- | --- | --- | --- |
| 1 | the cross-validation leaks | ESM-2 on shuffled labels | **ruled out** — 0.478 / 0.523, sitting on chance |
| 2 | it is detecting sequence length | matched positives and negatives on length | **ruled out** — length-only AUC fell 0.770 → 0.514 while ESM-2 held at 0.990 |
| 3 | it is detecting the source database | drew positives and negatives both from UniProt | **removed by rebuilding the dataset** |
| 4 | it is detecting disorder itself | rebuilt the negatives, matched on disorder coverage | **this was the real problem** |

**What hypothesis 4 found.** The original negatives came from DisProt, which annotates disordered
*regions inside* proteins rather than whole disordered proteins. Their median disorder coverage was
**0.15** against **0.88** for the positives — they were folded proteins with a floppy tail. The
"hard" task was substantially re-measuring folded-versus-unfolded, which is what the *trivial* task
already does.

We rebuilt the negative set from UniProt proteins that are themselves genuinely disordered, matched
one-to-one to the positives on **both** disorder coverage and length under the Austin caliper above.
Final balance on the matched set:

| matched variable | standardized mean difference | threshold |
| --- | --- | --- |
| disorder coverage | +0.015 | < 0.10 |
| sequence length | +0.013 | < 0.10 |

Both variables are uninformative in the matched set by construction, so neither can explain the
result that follows.

`src/tardiscreen/diagnose.py` runs checks 1, 2 and 4 on demand; `build_negatives.py`,
`match_negatives.py` and `merge_dataset.py` are the rebuild.

## The dataset

| tier | what it is | n |
| --- | --- | --- |
| **protective** (positive) | LEA, dehydrin and other anhydrobiosis-associated disordered proteins from UniProt | 1,069 |
| **idp_matched** (hard negative) | genuinely disordered UniProt proteins, matched 1:1 to a positive on disorder coverage and length | 529 matched pairs |
| **ordered** (sanity negative) | folded globular proteins | the *trivial* task only |

3,151 sequences in total carry embeddings. The **real** task uses only the matched subset, because
that is the only subset where the matching guarantee holds.

## Limitations, in full

Each of these is a real constraint on what the numbers mean. They are listed because a result you
cannot argue against is a result nobody can check.

**The dataset contains no CAHS proteins.** Despite the project's origin, the 529 matched positives
break down as LEA 308, dehydrin 198, other 21, hydrophilin 2 — and **zero CAHS**. Reviewed tardigrade
entries are scarce in Swiss-Prot. So this is a *desiccation-protection-family* screener trained
almost entirely on **plant** LEA and dehydrin proteins, motivated by tardigrade CAHS biology rather
than trained on it. LEA and CAHS proteins are thought to protect through the same disorder-driven
vitrification mechanism, which is why the framing holds — but the training data is plant-dominated.

**The two held-out families are related.** Dehydrins are LEA group 2, so "train on LEA, test on
dehydrin" leaves related proteins in training. That is almost certainly why BLAST still reaches
0.925 on the dehydrin holdout against 0.739 on the LEA holdout. With only two families large enough
to hold out (n ≥ 25), the generalization result rests on two non-independent rotations.

**The cluster split is permissive.** See the Rost (1999) discussion above. We measured the
consequence: BLAST found hits for **97% of queries** against training sequences in *different*
clusters. **Our AUCs are therefore optimistic, not conservative.**

**A species confound is untested.** The positives are plant and invertebrate proteins; the negatives
come mostly from human, mouse, fly and yeast. Amino-acid usage differs between organisms, so part of
the composition signal (0.897) may be taxonomic rather than functional. We did not test this.

**The matched set covers mid-range disorder only.** Matching paired 529 of 835 annotated positives.
The unmatched 306 skew highly disordered — matched positives sit at median 0.66 coverage against
0.88 for the full set — because negatives that are both sufficiently disordered *and* short are rare.
Results apply to the mid-disorder range, not to the most extreme protective proteins.

**Coverage was measured with two different rulers.** The candidate negatives were measured through
MobiDB and UniProt region annotations; the positives through UniProt regions alone.
`match_negatives.py` prints a warning when the sources differ. Treat the matched coverage as
approximate rather than exact.

**No efficacy data exists.** We classify family membership and surface signatures. We do not predict
how *much* a protein protects, and no dataset we know of would support that.

**Labels are heterogeneous.** LEA, dehydrin and CAHS proteins protect by different mechanisms
(gelation, vitrification, membrane support). One score flattens that, which is why the app shows a
per-feature breakdown alongside it.

**A name-filter bug affected the original pull.** The inherited protective-term filter matched `lea`
as a bare substring, so it also caught "nuc**lea**r", "c**lea**vage", "re**lea**se" and
"**lea**der", dropping ordinary disordered proteins as "protective-related". It is fixed and covered
by a regression test, but the original DisProt negatives were drawn with it in place.

## Still unverified

Stated here so nobody cites them as settled:

- No published threshold defining "fully disordered" by percentage coverage was located. Our floor is
  derived from the data instead (above).
- The charge–hydropathy relationship often attributed to Uversky underlies two of our biophysical
  features (`fraction_charged`, `mean_hydropathy`). We have **not** verified that citation and it
  should be checked before appearing in the README.
