# Demo script

Two things live here: the **spoken script** for presenting to judges, and the **recording
checklist** for the backup video. Read the pre-flight section before either.

---

## Pre-flight (do this 20 minutes before, every time)

```bash
bash scripts/check_site.sh https://anhydra.work
```

Every line must say PASS. If `model is loaded` fails, the server lost `data/models.joblib` — nothing
will score and there is no talking around it. If the explanation line says it came from the offline
fallback, Gemini is rate-limited or down: the demo still works, but do not claim Gemini wrote the
readout.

Then, by hand:

1. Open **https://anhydra.work** in a clean window. No other tabs, no bookmarks bar.
2. Click **dehydrin** → **Screen sequence**. This warms up ESM-2 — the first request after a restart
   takes about 15 seconds while the model loads into memory. **Never let a judge watch that happen.**
3. Reload the page so it is back at the idle state.
4. Have the backup video open in a second window, paused at frame one.

---

## The three-minute script

Rough timings. Say it in your own words; keep the structure.

### 0:00 — the hook (20s)

> A tardigrade can lose essentially all of its water, sit dry for years, and come back. It does that
> with proteins — a few families that turn the inside of the cell into glass instead of letting it
> crystallise.
>
> If you could find more proteins like that, you could ship vaccines without a refrigerator. So:
> here's a protein. Does it do that?

*(On screen: the idle page, scrolled to the top.)*

### 0:20 — the demo (50s)

Click **dehydrin**, then **Screen sequence**.

> This is a plant dehydrin. It's a real protein, and it's one of the families that does this job.

The gauge sweeps to its score.

> Point-nine-six. And here's the part I actually care about — it doesn't just hand you a number.

Scroll to the **residue map**.

> That's every amino acid in the protein, coloured by chemistry. Almost no grey — grey is the
> water-hating residues that make up a normal folded protein's core. This thing has no core. That's
> what being disordered looks like.

Scroll to **known motifs** — the highlighted blocks.

> And those lit-up stretches are a motif called the K-segment. Hold that thought, it comes back in
> thirty seconds.

Scroll to the **readout**.

> That paragraph is written by Gemini, from the model's own output — the score, the call, the feature
> contributions. Nothing else.

Now click **folded control** → **Screen sequence**.

> Lysozyme. Tightly folded, has a real core, does not do this. Point-oh-eight. The gauge goes amber,
> the motif panel says no match.

### 1:10 — why you should believe it (60s)

> Now, the honest part. Our first result on the hard task was 0.987, and that was too good. So we
> spent most of the project trying to break it.
>
> Four hypotheses. We shuffled the labels — the model dropped to chance, so there's no leak. We
> matched on length — no change. And then we found the real one: our negatives were folded proteins
> with a floppy tail. They were fifteen percent disordered; our positives were eighty-eight percent.
> The model wasn't detecting protection. It was detecting disorder.
>
> So we threw the negatives out and rebuilt them — genuinely disordered proteins, matched one-to-one
> to each positive on disorder *and* length, using a caliper rule from the matching statistics
> literature. After that, neither variable can explain the result.
>
> And one more. BLAST — a sequence search from the nineties — scores 0.981 on this. Basically a tie
> with our model. So the table on its own proves nothing. We held out an entire protein family, so
> there were no relatives left in training. BLAST falls to 0.739. The language model holds at 0.818.
> **That's the result.** When a close relative exists, alignment is as good as ML. When one doesn't,
> only the language model still works — and that's the case you actually care about, because it's
> every organism nobody has sequenced yet.

### 2:10 — the thing we did not expect (40s)

> We also trained a small convolutional network from scratch — no pretraining, no motif database,
> nothing but raw sequence. Then we asked its filters what they had learned to look for.
>
> They came back with this: E-K-K-G-I-M-D-K-I-K-E-K-L-P-G. That's the K-segment. It's the motif that
> *defines* the dehydrin family, and plant biologists published it decades ago. Our network had never
> heard of it. It found it by itself, out of a thousand sequences.
>
> And here's why that's the honest version: we predicted the wrong motif. We expected glycine-serine
> repeats, the tardigrade signature this project is named after. Our dataset turned out to have zero
> tardigrade proteins in it — so the network learned what was actually there, not what we wanted.

### 2:50 — close (10s)

> A score you can't check is just a number. This one, you can go look up.
>
> It's live at anhydra.work.

---

## If something breaks

| what happens | what you say |
| --- | --- |
| Page won't load | "Let me show you the recording" — switch windows, keep talking. Don't debug in front of judges. |
| Score takes >20s | "It's loading the language model into memory — first request after a restart." Keep narrating the residue map. |
| Readout is the offline template | Say "the plain-language layer is rate-limited right now, so this is our local fallback." Don't claim Gemini wrote it. |
| Judge asks for a sequence of their own | Say yes. Paste it. If it scores oddly, that's a finding, not a failure — talk through the residue map. |

---

## Questions judges actually ask

**"Did you train the protein language model?"**
No. ESM-2 is frozen — those are Meta's pretrained weights, untouched. We trained the classifier on
top of its representations. That's called linear probing, and it's why the whole thing trains in
seconds and why our cluster-split numbers mean something.

**"Isn't 0.99 suspicious?"**
Yes, and that's why we don't lead with it. It's 0.818 on an unseen family, which is the number that
matters. The 0.99 is what you get when the test set has relatives in training.

**"How is this different from a BLAST search?"**
On this benchmark, mostly it isn't — 0.981 versus 0.990. The difference shows up when there is no
relative to align to: 0.739 versus 0.818. Screening uncatalogued organisms is exactly that case.

**"What can't it do?"**
It cannot tell you *how much* a protein protects. It's a family and triage signal. No efficacy
dataset exists that would support the stronger claim, and we say so on the results page itself.

**"How big is the dataset?"**
3,151 sequences with embeddings; the hard task runs on 529 matched pairs. It is plant-dominated —
LEA and dehydrins — and contains zero CAHS proteins, which we list as a limitation rather than
hiding.

**"What would you do next?"**
Two things. A stricter homology split — ours clusters at 40% identity, and Rost puts the twilight
zone at 20–35%, so our numbers are optimistic rather than conservative. And more held-out families:
right now the generalization result rests on two, and they're related.

---

## Recording the backup video

Four minutes, one take, no editing needed if you follow this.

**Setup.** 1920×1080, browser zoom 100%, clean window. Run the pre-flight above so ESM-2 is warm.
Record system audio *and* mic. Do a 10-second test and play it back before the real take.

**Shot list.**

| # | what's on screen | what you say | ~time |
| --- | --- | --- | --- |
| 1 | Idle page, top | The hook — 0:00 above | 0:20 |
| 2 | Click dehydrin, Screen sequence | The demo — 0:20 above | 0:50 |
| 3 | Slow scroll: gauge → residue map → motifs → readout | Keep narrating; don't scroll faster than you talk | — |
| 4 | Click folded control, Screen sequence | The contrast — amber gauge, no motifs | 0:20 |
| 5 | Screen-share the README results tables | Why you should believe it — 1:10 above | 1:00 |
| 6 | README "CNN rediscovered a published motif" | The K-segment — 2:10 above | 0:40 |
| 7 | Back to the live site | The close | 0:10 |

**Rules.** Never show a terminal. Never show this repo's `.env` or the server. If you fumble a line,
stop, breathe, and start that shot again — a clean four-minute take beats a stitched one.

**Where it goes.** Upload unlisted to YouTube, put the link in the Devpost entry *and* in a pinned
message to the team, so nobody is hunting for it at 7:55 AM.
