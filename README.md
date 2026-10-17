# TardiScreen

**Paste a protein sequence → get a desiccation-protection score + a plain-language "why."**

TardiScreen is a machine-learning screening tool that scores any amino-acid sequence for
**CAHS-like, desiccation-protective character** and explains the biophysical signatures behind
the score. It's built as a triage aid for biopreservation research — prioritizing which sequences
are worth expressing and testing in the lab (stabilizing vaccines, clotting factors, and reagents
without a cold chain).

Built for **SwampHacks XII** (Oct 16–18, 2026, Reitz Union, University of Florida).

> **Honest framing (read this first):** TardiScreen is a **family / character classifier and triage
> tool**, not a validated efficacy predictor. It classifies whether a sequence belongs to the
> protective families (CAHS / LEA / other anhydrobiosis proteins) and surfaces its signatures — it
> does **not** claim to predict how *much* a protein protects. See [Honest limitations](#honest-limitations).

---

## The pipeline

| 1 · Data | 2 · Embed | 3 · Model | 4 · Explain | 5 · App |
| --- | --- | --- | --- | --- |
| Protective IDPs (CAHS/LEA) vs. *other* IDPs — the hard, real question | ESM-2 protein language model → sequence vectors (small model, CPU) | Classifier head + a parallel interpretable biophysical model | Feature importance + Gemini plain-language readout | Clean web UI on a real domain, hosted on Vultr |

The two-model design is deliberate: the ESM-2 embedding model is the centerpiece, and the
interpretable biophysical-features model is both the "why" **and** a fallback that still runs if the
embedding pipeline stalls.

---

## Why "protective vs. other disordered" is the whole game

"Is this protein disordered?" is trivial — composition alone solves it (expect ≈0.98 AUC).
"Among disordered proteins, which ones *protect*?" is the question a lab actually has, and it's
genuinely hard (expect ≈0.7–0.8 AUC). **We report both tasks** — that contrast is a better result
than either number alone, and it's where ESM-2 can beat a plain composition baseline.

---

## Results

All numbers are **ROC-AUC under 5-fold cross-validation split by sequence cluster** (CD-HIT 40%
identity), never by row — so homologs cannot sit on both sides of a split.

### Two tasks

- **trivial** — protective vs. *ordered* (folded) proteins. A sanity check: this should be easy.
- **real** — protective vs. *other disordered* proteins, matched one-to-one on disorder coverage
  and length. This is the question the project exists to ask.

| model | what it uses | trivial | real |
| --- | --- | --- | --- |
| composition | 20 amino-acid frequencies, no order | 0.922 | 0.897 |
| biophysical | 9 interpretable features | 0.893 | 0.780 |
| BLAST | classical alignment search | 0.977 | 0.981 |
| CNN | DeepFam-style, trained from scratch | 0.987 | 0.965 |
| **ESM-2** | **pretrained protein language model** | **0.998** | **0.990** |

### The result that actually distinguishes the models

On the table above, **BLAST (0.981) and ESM-2 (0.990) are within about one standard deviation.**
A 1990s alignment search nearly matches the language model, so that table alone cannot justify the
ML approach.

Stratifying held-out sequences by how much alignment signal they had explains why:

| best bitscore to training set | n | % protective | BLAST | ESM-2 |
| --- | --- | --- | --- | --- |
| none / very weak | 482 | 12% | 0.925 | 0.947 |
| weak | 290 | 78% | 1.000 | 0.999 |
| moderate | 219 | 85% | 1.000 | 1.000 |

Read the **% protective** column. Sequences with no alignment hit are 12% protective; sequences
with a hit are 78–85% protective. *"Does this protein have a close relative in the training set?"*
is close to the entire classifier — because the positives are a few dense families whose members
stay related through a 40% identity split, while the negatives are unrelated singletons.

So we removed that advantage: **hold out an entire family**, train on the rest, and test on a family
with no relatives in training.

| held-out family | n | BLAST | ESM-2 |
| --- | --- | --- | --- |
| LEA | 308 | 0.739 | **0.818** |
| dehydrin | 198 | 0.925 | **0.934** |
| **mean** | | **0.832** | **0.876** |

The LEA row is the cleaner test. Dehydrins are LEA group 2, so holding them out still leaves related
proteins in training, and BLAST accordingly manages 0.925 there; with the family genuinely absent it
falls to 0.739 while the model holds at 0.818.

**This is the finding.** When a close relative exists, alignment and embeddings are equivalent. When
one does not, alignment degrades and the language model holds — which is exactly the case that
matters for screening sequences from organisms nobody has catalogued yet.

## What the network learned

The CNN is trained from scratch on raw sequence — no pretraining, no hand-designed features, no motif
database. Its convolution filters are pattern detectors, so after training they can be asked what
makes them fire. Ranking filters by how well their activation separates the classes and reading the
strongest-activating windows gives the patterns the network found on its own (48 filters cleared the
threshold):

| filter | AUC | learned pattern |
| --- | --- | --- |
| 22 | 0.896 | `IKEKLPGYH` |
| 16 | 0.894 | `FLDKIKEKL` |
| 59 | 0.893 | `EKKGIMDKI` |
| 26 | 0.893 | `EKIKEKLPG` |
| 102 | 0.886 | `KGIKEKIKE` |

Residue content across all learned motifs: **K 31%**, I 15%, E 12%, G 10%, D 7%, L 6%, V 4%, F 4%.

### These reconstruct the dehydrin K-segment

The dehydrin family is *defined* by a lysine-rich 15-residue motif, the
[K-segment](https://pmc.ncbi.nlm.nih.gov/articles/PMC4215689), consensus `EKKGIMDKIKEKLPG`. The
filters recover it:

```
canonical K-segment   E K K G I M D K I K E K L P G
filter 59             E K K G I M D K I
filter 26                     E K I K E K L P G
filter 16                   F L D K I K E K L
```

Filter 59 matches the first nine residues exactly. Filter 26 covers the last nine with E where the
canonical has D — and the published consensus is `[XKXGXX(D/E)KIK(D/E)KXPG]`, which permits either at
that position ([Malik et al. 2017](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5415607/)). The 31%
lysine content matches the same literature's finding that lysines are the most conserved residues in
the segment.

**Nothing in the pipeline was told this motif exists.** A network with 101k parameters, trained on
1,049 sequences, recovered a motif that plant biologists named and published decades ago.

It is also the *right* motif for this dataset rather than the expected one. We predicted glycine/
serine repeats, the CAHS signature. The dataset contains **no CAHS proteins** — it is 308 LEA and 198
dehydrins — so the network learned what is actually present. That mismatch between our expectation
and its output is part of why the result is credible: it followed the data, not the project's title.

This is the one result none of the other four models can produce. ESM-2 scores better; it cannot tell
you what it saw.

### In plain terms

Dehydrins are a family of plant proteins, and biologists identify them by one specific 15-letter
stretch: `EKKGIMDKIKEKLPG`. It is called the K-segment — K for lysine, the letter that dominates it —
and it was named decades ago. A protein containing it is a dehydrin. That is the definition.

Our network had never heard of it. No database, no textbook, no hints: it saw 1,049 proteins as
strings of letters and had to work out for itself what separated the protective ones. Afterwards we
asked each of its pattern detectors what it had learned to look for, and several answered with
pieces of that exact stretch.

This matters because a score of 0.99 cannot be checked — anyone can say the model got lucky or found
a shortcut. "It found the K-segment" can be checked: look up the motif, compare, and see. It is
specific, it is published, and it either matches or it does not.

And we predicted the wrong motif. We expected glycine/serine repeats, the CAHS signature this project
is named for. The dataset contains no CAHS proteins, so the network learned the dehydrin motif
instead — it followed the data rather than the project's title. Had it produced what we expected, we
would have had more reason to suspect we were fooling ourselves.

## How we checked the result

The real task first scored **0.987**, far above the 0.7–0.8 we predicted. We treated that as a
problem rather than a success, and tested four explanations.

| # | hypothesis | test | outcome |
| --- | --- | --- | --- |
| 1 | the cross-validation leaks | ESM-2 on shuffled labels | **ruled out** — 0.478 / 0.523, sitting on chance |
| 2 | it's detecting sequence length | matched positives and negatives on length | **ruled out** — length-only AUC fell 0.770 → 0.514, ESM-2 held at 0.990 |
| 3 | it's detecting the source database | positives and negatives both drawn from UniProt | **removed by rebuilding the dataset** |
| 4 | it's detecting disorder itself | rebuilt the negatives, matched on disorder coverage | **the real problem — see below** |

**What hypothesis 4 found.** The original negatives came from DisProt, which annotates disordered
*regions inside* proteins rather than whole disordered proteins. Their median disorder coverage was
**0.15**, against **0.88** for the positives — they were folded proteins with a floppy tail. The
"hard" task was substantially re-measuring folded-vs-unfolded, which is what the *trivial* task
already does.

We rebuilt the negative set from UniProt proteins that are genuinely disordered, matched one-to-one
to the positives on **both** disorder coverage and length (caliper = 0.2 × SD, after
[Austin 2011](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3120982/)). Final balance:

| matched variable | standardized mean difference | threshold |
| --- | --- | --- |
| disorder coverage | +0.015 | < 0.10 |
| sequence length | +0.013 | < 0.10 |

Both variables are uninformative in the matched set by construction, so neither can explain the
result. See [docs/METHODS.md](docs/METHODS.md) for every threshold and its source.

## Repo layout

```
tardiscreen/
├── README.md               ← you are here
├── CONTRIBUTING.md         ← team roles + workflow (read before you start)
├── requirements.txt
├── docs/
│   ├── GAME_PLAN.md        ← the full weekend timeline
│   ├── DATA_PLAN.md        ← where the data comes from + the cluster-split rule
│   └── EVALS.md            ← the evaluation protocol (our AI-track centerpiece)
├── data/                   ← raw/processed data lives here (gitignored, see data/README.md)
├── src/tardiscreen/
│   ├── data.py             ← pull + label UniProt / DisProt / MobiDB sequences
│   ├── features.py         ← interpretable biophysical features  (implemented)
│   ├── embed.py            ← ESM-2 embeddings
│   ├── model.py            ← classifier head + feature model
│   ├── evaluate.py         ← cluster-split CV, ROC/PR-AUC, confusion matrix
│   └── explain.py          ← Gemini plain-language "why this score"
├── app/
│   └── main.py             ← FastAPI: sequence in → score + explanation out
└── notebooks/              ← scratch / exploration
```

## Quick start

```bash
# 1. Python 3.10+ recommended
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Pull and label the data (see docs/DATA_PLAN.md)
python -m tardiscreen.data

# 3. Compute embeddings + features
python -m tardiscreen.embed
python -m tardiscreen.features

# 4. Train + evaluate (cluster-split CV)
python -m tardiscreen.evaluate

# 5. Run the app locally
uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` for the explanation feature.

## Sponsor stack (what we're opting into)

- **Vultr** — host the app, point the domain at it (no GPU needed; ESM-2 small embeds on CPU).
- **Gemini API** — generates the plain-language "why this score" readout.
- **GoDaddy Registry** — demo on a real `tardiscreen.*` domain.
- **DEV Writing** — the end-of-weekend write-up.

Tracks we're targeting: **Most Creative Use of AI**, **Overall / Hack of the Year**, **Easy on the Eyes**.

## Honest limitations

Each of these is a real constraint on what the numbers mean. They are listed because a result you
cannot argue against is a result nobody can check.

**The dataset contains no CAHS proteins.** Despite the name, the 529 matched positives break down as
LEA 308, dehydrin 198, other 21, hydrophilin 2 — and **zero CAHS**. Reviewed tardigrade entries are
scarce in Swiss-Prot. So this is a *desiccation-protection-family* screener trained almost entirely
on **plant** LEA and dehydrin proteins, motivated by tardigrade CAHS biology rather than trained on
it. LEA and CAHS proteins are thought to protect through the same disorder-driven vitrification
mechanism, which is why the framing still holds — but the training data is plant-dominated and the
name oversells that.

**The two held-out families are related.** Dehydrins are LEA group 2, so "train on LEA, test on
dehydrin" leaves related proteins in training. That is almost certainly why BLAST still reaches
0.941 there versus 0.812 on the LEA holdout. With only two families large enough to hold out
(n ≥ 25), the generalization result rests on two non-independent rotations.

**The cluster split is permissive.** [Rost (1999)](https://www.biostat.wisc.edu/~kbroman/teaching/statgen/2004/refs/rost1.pdf)
places the twilight zone of sequence alignment at 20–35% identity, so clustering at 40% can place
genuinely homologous pairs in different clusters. We measured this: BLAST found hits for **97% of
queries** against training sequences in *different* clusters. Reaching a 25–30% threshold requires
PSI-CD-HIT and an all-against-all BLAST, beyond this project's runtime. **Our AUCs are therefore
optimistic, not conservative.**

**A species confound is untested.** The positives are plant and invertebrate proteins; the negatives
come mostly from human, mouse, fly and yeast. Amino-acid usage differs between organisms, so part of
the composition signal (0.897) may be taxonomic rather than functional. We did not test this.

**The matched set covers mid-range disorder only.** Matching paired 529 of 835 annotated positives.
The unmatched 306 skew highly disordered — matched positives sit at median 0.66 coverage against
0.88 for the full set — because sufficiently disordered *and* short negatives are rare. Results
apply to the mid-disorder range, not the most extreme protective proteins.

**No efficacy data exists.** We classify family membership and surface signatures. We do not predict
how *much* a protein protects, and no dataset we know of would support that.

**Labels are heterogeneous.** LEA, dehydrin and CAHS proteins protect by different mechanisms
(gelation, vitrification, membrane support). One score flattens that, which is why the app shows a
per-feature breakdown alongside it.

**A name-filter bug affected the original pull.** Our inherited protective-term filter matched `lea`
as a bare substring, so it also caught "nuc**lea**r", "c**lea**vage", "re**lea**se" and
"**lea**der" — dropping ordinary disordered proteins as "protective-related". Fixed, but the
original DisProt negatives were drawn with it in place.

## References

Keep real CAHS / anhydrobiosis literature (Nature, Wiley, Frontiers, PubMed) cited here before
submission — citing real sources strengthens both the AI and Overall judging. _(Add links as you go.)_

## License

MIT — see [LICENSE](LICENSE).
