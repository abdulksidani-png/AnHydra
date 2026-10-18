# AnHydra

**Paste a protein sequence. Find out whether it looks like it can survive drying out.**

Live at **[anhydra.work](https://anhydra.work)** · built for **SwampHacks XII** (Oct 16–18, 2026, UF)

Tardigrades survive losing essentially all of their water. A handful of protein families do that
work — CAHS in tardigrades, LEA and dehydrins in plants — by turning the cell's interior into glass
instead of letting it crystallise. Finding more of them is a real screening problem for
biopreservation research: vaccines, clotting factors and reagents that could ship without a cold
chain. AnHydra scores any amino-acid sequence for that character and explains the score in plain
language.

> **Read this first.** AnHydra is a **family classifier and triage tool**, not an efficacy predictor.
> It answers *"does this sequence belong to the desiccation-protective families?"* — never *"how much
> does this protein protect?"* Every limitation we know of is listed in
> [docs/METHODS.md](docs/METHODS.md).

*(The repository and the Python package are named `tardiscreen`, the project's working title.
AnHydra is the same thing.)*

Release checks and deployment gates: [docs/RELEASE.md](docs/RELEASE.md).
The API accepts one sequence of **20–1,022 standard residues**, including an optional FASTA
header. Longer inputs are rejected instead of silently scoring only a prefix. Scores are
uncalibrated classifier outputs, not experimentally measured protection probabilities.
The results below are recorded experiments; they have not been regenerated with the release fixes.

---

## How it works

| 1 · Data | 2 · Embed | 3 · Model | 4 · Explain | 5 · App |
| --- | --- | --- | --- | --- |
| Protective IDPs vs. *other disordered* proteins, matched on disorder and length | ESM-2 protein language model → a 480-number vector per sequence | A classifier head on those vectors, plus a parallel interpretable biophysical model | Feature contributions + a Gemini plain-language readout | FastAPI on Vultr, real domain, HTTPS |

ESM-2 is **frozen** — we never touched Meta's 35M pretrained weights. What we trained is the thin
classifier sitting on top of them, which is called *linear probing*. The second, interpretable model
provides auxiliary signatures for the "why" panel; it does not replace ESM-2 if embedding fails.

## The question that makes this hard

"Is this protein disordered?" is trivial — composition alone nearly solves it. "Among disordered
proteins, which ones *protect*?" is the question a lab actually has. We report both, because the
contrast is a better result than either number alone.

## Results

ROC-AUC under 5-fold cross-validation **split by sequence cluster** (CD-HIT 40% identity), never by
row, so homologs cannot sit on both sides of a split.

- **trivial** — protective vs. *ordered* folded proteins. A sanity check.
- **real** — protective vs. *other disordered* proteins, matched one-to-one on disorder coverage and
  length. The question the project exists to ask.

| model | what it uses | trivial | real |
| --- | --- | --- | --- |
| composition | 20 amino-acid frequencies | 0.922 | 0.897 |
| biophysical | 9 interpretable features | 0.893 | 0.780 |
| BLAST | classical alignment search | 0.977 | 0.981 |
| CNN | DeepFam-style, trained from scratch | 0.987 | 0.965 |
| **ESM-2** | **pretrained protein language model** | **0.998** | **0.990** |

### That table does not justify the ML approach — so we kept going

BLAST (0.981) and ESM-2 (0.990) are within about one standard deviation. A 1990s alignment search
nearly matches the language model. Stratifying held-out sequences by how much alignment signal they
had shows why:

| best bitscore to training set | n | % protective | BLAST | ESM-2 |
| --- | --- | --- | --- | --- |
| none / very weak | 482 | 12% | 0.925 | 0.947 |
| weak | 290 | 78% | 1.000 | 0.999 |
| moderate | 219 | 85% | 1.000 | 1.000 |

Read the **% protective** column. *"Does this protein have a close relative in the training set?"* is
close to the entire classifier — the positives are a few dense families whose members stay related
through a 40% identity split, while the negatives are unrelated singletons.

So we removed that advantage: **hold out an entire family**, train on the rest, test on a family with
no members of that annotated family in training. Related families can remain.

| held-out family | n | BLAST | ESM-2 |
| --- | --- | --- | --- |
| LEA | 308 | 0.739 | **0.818** |
| dehydrin | 198 | 0.925 | **0.934** |
| **mean** | | **0.832** | **0.876** |

LEA is the cleaner test — dehydrins are LEA group 2, so holding them out still leaves relatives in
training, which is why BLAST manages 0.925 there. With the annotated LEA family held out, BLAST falls to
0.739 while the language model holds at 0.818.

**This is the finding.** BLAST and ESM-2 have similar measured AUC on the cluster-split benchmark.
ESM-2 has higher measured AUC on these two annotated family holdouts. The families are related,
and these experiments do not establish performance for arbitrary uncatalogued organisms.

## The CNN rediscovered a published motif on its own

The CNN is trained from scratch on raw sequence: no pretraining, no hand-designed features, no motif
database. Its convolution filters are pattern detectors, so after training we can ask what makes them
fire. Ranking filters by how well their activation separates the classes and reading the
strongest-activating windows gives the patterns it found by itself — 48 filters cleared the
threshold:

| filter | AUC | learned pattern |
| --- | --- | --- |
| 81 | 0.914 | `FLDKIKEKL` |
| 22 | 0.896 | `IKEKLPGYH` |
| 59 | 0.893 | `EKKGIMDKI` |
| 26 | 0.893 | `EKIKEKLPG` |
| 102 | 0.886 | `KGIKEKIKE` |

Residue content across all learned motifs: **K 31%**, I 15%, E 12%, G 10%, D 7%, L 6%.

The dehydrin family is *defined* by a lysine-rich 15-residue motif, the
[K-segment](https://pmc.ncbi.nlm.nih.gov/articles/PMC4215689), consensus `EKKGIMDKIKEKLPG`. The
filters reconstruct it:

```
canonical K-segment   E K K G I M D K I K E K L P G
filter 59             E K K G I M D K I
filter 26                     E K I K E K L P G
filter 81                   F L D K I K E K L
```

Filter 59 matches the first nine residues exactly. Filter 26 covers the last nine with E where the
canonical has D — and the published consensus is `[XKXGXX(D/E)KIK(D/E)KXPG]`, which permits either at
that position ([Malik et al. 2017](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5415607/)). The 31%
lysine content matches the same literature's finding that lysines are the most conserved residues in
the segment.

**Nothing in the pipeline was told this motif exists.** A network with 101k parameters, trained on
1,049 sequences, recovered a motif that plant biologists named and published decades ago.

It is also the *right* motif for this dataset rather than the expected one. We predicted glycine and
serine repeats, the CAHS signature. The dataset contains **no CAHS proteins** — it is 308 LEA and 198
dehydrins — so the network learned what is actually there. Had it produced what we expected, we would
have had more reason to suspect we were fooling ourselves.

This is the one result none of the other four models can produce. ESM-2 scores better; it cannot tell
you what it saw.

## We did not believe our own number

The real task first scored **0.987**, far above what we predicted. We treated that as a bug. Four
hypotheses, four tests: cross-validation leakage (ruled out — shuffled labels sit at chance), length
(ruled out — length-only AUC fell to 0.514 while ESM-2 held), source database (removed), and disorder
itself — **which turned out to be the real problem.** The original negatives were folded proteins
with a floppy tail, median disorder coverage 0.15 against 0.88 for the positives.

So we rebuilt the entire negative set from genuinely disordered UniProt proteins, matched one-to-one
on disorder coverage *and* length under the caliper from
[Austin (2011)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3120982/). Both variables came out
balanced (|SMD| ≤ 0.015, threshold 0.10), so neither can explain the result.

Every threshold, its published source, the full confound table and all nine limitations are in
**[docs/METHODS.md](docs/METHODS.md)**.

## Repo layout

```
anhydra/  (repo: tardiscreen)
├── app/
│   ├── main.py             FastAPI: sequence in → score + explanation out
│   └── static/index.html   the results page
├── src/tardiscreen/
│   ├── data.py             pull + label UniProt / DisProt / MobiDB sequences
│   ├── build_negatives.py  candidate pool of genuinely disordered proteins
│   ├── coverage.py         per-sequence disorder coverage
│   ├── match_negatives.py  caliper matching on coverage + length
│   ├── merge_dataset.py    fold the matched negatives into the dataset
│   ├── features.py         9 interpretable biophysical features
│   ├── embed.py            ESM-2 embeddings
│   ├── model.py            classifier head + feature model → data/models.joblib
│   ├── evaluate.py         cluster-split CV, ROC/PR-AUC, confusion matrix
│   ├── blast_baseline.py   classical alignment baseline
│   ├── remote_homology.py  stratify test sequences by alignment signal
│   ├── family_holdout.py   leave-one-family-out generalization
│   ├── cnn.py              DeepFam-style CNN trained from scratch
│   ├── motifs.py           read motifs back out of the CNN's filters
│   ├── diagnose.py         the confound checks
│   └── explain.py          Gemini plain-language "why this score"
├── docs/
│   ├── METHODS.md          every threshold, its source, and all limitations
│   ├── DEMO.md             the presentation + live-demo script
│   ├── EXPLAINER.md        the whole project in plain English
│   └── results/            the CSVs and figures behind every number above
├── frontend/               React UIs (separate from the served page; see their READMEs)
│   └── anhydra-site/       the Duda-built site: landing, screener, about
├── deploy/                 systemd unit + Caddy config for the Vultr host
└── scripts/check_site.sh   is the live site demo-ready?
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m tardiscreen.data          # pull + label sequences
python -m tardiscreen.coverage      # disorder coverage
python -m tardiscreen.build_negatives
python -m tardiscreen.match_negatives
python -m tardiscreen.merge_dataset
python -m tardiscreen.embed         # ESM-2 embeddings (CPU is fine)
python -m tardiscreen.evaluate      # cluster-split CV
python -m tardiscreen.model         # writes data/models.joblib for the app

uvicorn app.main:app --reload       # http://127.0.0.1:8000
```

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` for the plain-language readout. Without it the
app falls back to a local template rather than failing. Without `data/models.joblib`, `/score`
returns 503 rather than inventing a number.

To check the deployed site: `bash scripts/check_site.sh https://anhydra.work`

## Sponsor stack

- **Vultr** — hosts the app. No GPU needed; ESM-2 small embeds on CPU.
- **Gemini API** — writes the plain-language "why this score" readout.
- **GoDaddy Registry** — [anhydra.work](https://anhydra.work).
- **DEV** — the write-up.

Tracks: **Most Creative Use of AI**, **Overall**, **Easy on the Eyes**.

## References

- Lin et al., *Language models of protein sequences at the scale of evolution* — ESM-2.
- Seo et al. (2018), [DeepFam](https://pmc.ncbi.nlm.nih.gov/articles/PMC6022622/) — the CNN architecture.
- Malik et al. (2017), [dehydrin K-segment consensus](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5415607/).
- Hughes & Graether, [K-segment structure](https://pmc.ncbi.nlm.nih.gov/articles/PMC4215689/).
- Austin (2011), [caliper width for matching](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3120982/).
- Rost (1999), [twilight zone of sequence alignment](https://www.biostat.wisc.edu/~kbroman/teaching/statgen/2004/refs/rost1.pdf).

## License

MIT — see [LICENSE](LICENSE).
