# AnHydra, explained from scratch

*This is written to be read aloud. No jargon goes by without being explained, no tables, no code.
Hand the whole file to a text-to-speech voice or to a podcast tool and it will work start to finish —
about fifteen minutes. If you are using a tool that generates a two-host conversation, use this as
the source document.*

---

## Part one: the animal

There is an animal called a tardigrade. It is about half a millimetre long, it lives in moss and
sand and gutters, and under a microscope it looks like a plump eight-legged bear, which is why people
call it a water bear.

Here is the thing it can do. A tardigrade can lose essentially all of the water in its body. Not
most of it — nearly all of it. It pulls its legs in, shrivels into a little barrel, and stops. No
metabolism, no movement, nothing you could call alive. It can stay that way for years. Then you add
water, and it walks away.

That state has a name: anhydrobiosis. Life without water. And it is not unique to tardigrades —
certain plant seeds do it, some rotifers and nematodes do it, a few resurrection plants do it. The
question that matters is *how*.

The answer, as far as we understand it, is proteins. Specific families of them. When the water
leaves a normal cell, the things dissolved in it crash together and form crystals, and crystals tear
membranes apart. These proteins stop that. As the cell dries, they turn its interior into a glass —
a solid that is disordered at the molecular level, like window glass rather than like ice. Everything
inside gets locked in place before it can be destroyed. When water comes back, the glass dissolves
and the cell picks up where it left off.

Three families of these proteins keep coming up. In tardigrades they are called CAHS proteins. In
plants they are called LEA proteins, and a subgroup of those are called dehydrins. Different
organisms, same trick.

## Part two: the problem worth solving

Here is why anybody outside a biology department should care.

Almost every vaccine in the world needs a refrigerator. So do most blood products, many antibody
drugs, and most of the reagents a diagnostic test depends on. That refrigeration chain — the cold
chain — is the single biggest reason medicine is harder to deliver to remote places than it needs to
be. Power fails, a cooler sits on a runway too long, a shipment is lost.

If you could dry a vaccine and have it survive, that problem changes shape entirely. And that is
exactly what these proteins do for a tardigrade.

So biopreservation researchers want more of them. The catch is that finding them is slow. You can
sequence an organism in an afternoon now, but working out which of its twenty thousand proteins
might be protective means expressing them one at a time in the lab and testing each one. That is
weeks of work per candidate.

What those researchers need first is a shortlist. Something that reads a protein sequence and says:
this one is worth your bench time, this one is not.

That is what AnHydra is.

## Part three: what a protein looks like to a computer

A protein is a chain. Each link in the chain is one of twenty molecules called amino acids, and each
amino acid gets a letter. So a protein, to a computer, is just a long word — a few hundred letters
from a twenty-letter alphabet. M, S, G, K, E, and so on.

Normally that chain folds into a specific three-dimensional shape, and the shape is what does the
work. The water-hating amino acids bury themselves in the middle, away from the water, and the
water-loving ones face outward. That buried middle is called a hydrophobic core, and it is what
holds a normal protein together.

The protective proteins do not do that. They have almost no water-hating amino acids at all, so
there is nothing to bury and no core to form. They stay floppy — a chain that never settles into one
shape. Biologists call these intrinsically disordered proteins, and that disorder is not a defect.
It is the mechanism. A floppy chain can spread out and fill space as the water leaves, which is what
lets it form that glass.

Hold onto this point, because the whole project turns on it: **being disordered and being protective
are not the same thing.** Plenty of proteins are disordered and do something completely unrelated.

## Part four: the model

We used a protein language model called ESM-2, built by Meta's research group.

The idea behind it is the same one behind the language models you already know. Take an enormous
pile of text — in this case, hundreds of millions of protein sequences from every organism anyone
has ever sequenced — hide some of the letters, and train a network to guess what is missing. To get
good at that game, the model has to pick up on real structure: which amino acids tend to sit near
each other, which patterns show up in proteins that do similar jobs, what a folded protein looks
like versus a floppy one. Nobody teaches it any of that explicitly. It falls out of the guessing
game.

What you get at the end is a translator. Hand it a protein sequence, and it hands you back four
hundred and eighty numbers that summarise the character of that sequence.

Now the important bit, and the thing to be precise about if anyone asks. We did not train ESM-2. We
did not modify it in any way. Those are Meta's weights, frozen exactly as they were published. What
we trained is a very small classifier that sits on top — it reads those four hundred and eighty
numbers and outputs one number between zero and one. That technique has a name: linear probing. It
is a deliberate choice, not a shortcut. Freezing the big model means our training set cannot quietly
reshape it, which makes our evaluation numbers mean something.

So the full path, when you paste a sequence into the website, is: your sequence goes into ESM-2,
ESM-2 produces four hundred and eighty numbers, our trained classifier reads those numbers, and out
comes a score.

## Part five: how you measure whether it works

The number we report is called AUC — area under the curve. The intuition is simple. Take one
protective protein and one non-protective protein at random. AUC is the probability that the model
gives the protective one the higher score. Fifty percent is a coin flip. A hundred percent is
perfect.

But a number like that is only as honest as the test behind it, and there is a classic way to fool
yourself in biology. Proteins come in families. If you shuffle your data randomly, you can easily end
up training on one member of a family and testing on its near-twin. The model then looks brilliant
when all it did was recognise something it had already seen.

So we never split randomly. We grouped every sequence by similarity first — any two proteins sharing
more than forty percent of their letters go in the same group — and then split by group. A protein
and its close relatives are always on the same side of the line. That makes the test harder and the
number smaller, and it also makes it real.

We also ran two different tests, on purpose. The first one we call the trivial task: protective
proteins against ordinary folded proteins. That one is easy, and it is supposed to be — it is a
sanity check. The second is the one the project exists for: protective proteins against *other
disordered proteins*. Both sides floppy. The only question left is whether this particular floppy
protein is one of the protective ones.

## Part six: the part where we did not believe ourselves

On that hard task, our first result was 0.987. Call it ninety-nine percent.

That was far better than we expected, and the correct response to a result that is too good is
suspicion, not celebration. So we stopped building and started attacking it.

We tested four explanations.

First: maybe the evaluation leaks somehow. We tested that by scrambling all the labels at random and
retraining. If there is a hidden leak, the model will still find something. It did not — it landed
on a coin flip. No leak.

Second: maybe it is just measuring length. Our protective proteins might simply be longer. We
rematched everything so the two groups had the same length distribution. The length signal
collapsed, and the model's score did not move. Not length.

Third: maybe it is detecting which database each protein came from, because different databases have
different quirks. We rebuilt both groups from the same source. That one we removed by construction.

Fourth: maybe it is just detecting disorder. And this is the one that was true.

Here is what happened. Our negative examples — the disordered proteins that are not protective —
came from a database that annotates disordered *regions inside* proteins. So what we had actually
collected was a pile of normal folded proteins that each happened to have one floppy tail. Measured
properly, they were about fifteen percent disordered. Our protective proteins were about
eighty-eight percent disordered. The model was not learning protection at all. It was learning
folded versus floppy — which is the easy question we were already asking separately.

So we threw the entire negative set away and built a new one, from proteins that are genuinely
disordered end to end. And we did not just filter them — we matched them. For each protective
protein, we found a non-protective one with nearly the same amount of disorder and nearly the same
length, using a standard rule from the statistics of matched studies for how close "nearly" has to
be. After that, the two groups were indistinguishable on both of those variables, which means
neither one can be the reason for whatever the model does next.

That rebuild cost us most of a day and it is the single most important thing we did.

## Part seven: the result that actually matters

Then we ran into a second, more uncomfortable problem.

There is a tool called BLAST, invented in 1990, that does something much simpler than a language
model: it searches a database for sequences that look similar to yours, letter by letter. It is the
most-used tool in all of biology and it involves no machine learning whatsoever.

We ran BLAST on our benchmark as a baseline, expecting our model to win comfortably. BLAST scored
0.981. Our model scored 0.990. That is a tie, in practical terms.

Which means the headline table proves nothing. If a thirty-five-year-old search tool matches your
neural network, you have not demonstrated that the neural network is doing anything interesting.

So we looked at why. And the answer was that the test was too easy in a specific way: almost every
protein in the test set had a relative sitting in the training set. BLAST just had to find the
relative. The model, in all likelihood, was doing the same thing in its own way.

So we designed the harder test. We took an entire protein family — all three hundred and eight LEA
proteins — pulled them completely out of training, and trained on everything else. Now, when we test
on them, there is no relative to find. Nothing to align against.

BLAST fell from 0.98 to 0.739. The language model held at 0.818.

That is the finding. When a protein has a known relative, a 1990s search tool is as good as a modern
language model, and you should just use the search tool. When it does not, the search tool degrades
and the language model keeps working.

And that second case is the entire point of this product. If you are screening proteins from an
organism nobody has catalogued yet, by definition there are no relatives in any database. That is
precisely where alignment has nothing to go on and the language model still does.

## Part eight: the thing we did not plan

Alongside the language model we trained a second, much smaller network from scratch — a
convolutional network, about a hundred thousand parameters, which is tiny. No pretraining. No
database. Just a thousand sequences and the raw letters.

A network like that works by learning pattern detectors. Each one scans along the sequence looking
for a specific short stretch of letters and fires when it finds one. Which means that after
training, you can ask it a question you cannot ask the big model: what did you learn to look for?

So we ranked its detectors by how well each one separated protective from non-protective, took the
best ones, and read out the stretches that made them fire hardest.

They came back with this: E, K, K, G, I, M, D, K, I, K, E, K, L, P, G.

That sequence has a name. It is called the K-segment — K for lysine, the amino acid that dominates
it — and it is the motif that *defines* the dehydrin family. If a plant protein contains it, it is a
dehydrin. That is the definition, and it was published decades ago.

Our network had never been told it exists. There was no motif database anywhere in our pipeline. It
saw a thousand proteins as strings of letters, worked out by itself what separated the protective
ones, and several of its detectors independently landed on pieces of that exact stretch. One of them
matched the first nine letters precisely.

This matters for a reason that has nothing to do with being impressive. A score of 0.99 cannot be
checked by anyone. You can always suspect it of a shortcut. "It found the K-segment" *can* be
checked — you look up the motif, you compare, and it either matches or it does not. It is a claim
with a verifiable answer, which makes it worth more than the score.

And there is a detail that makes it better rather than worse. We predicted the wrong motif. We
expected glycine and serine repeats, which are the signature of the tardigrade CAHS proteins this
project was named after. It turns out our dataset contains zero tardigrade proteins — there simply
are not enough well-curated ones in the public databases — so it is three hundred LEA proteins and
two hundred dehydrins. The network learned the dehydrin motif because that is what was actually in
front of it. It followed the data instead of our expectations. If it had produced the answer we
wanted, we would have had more reason to suspect ourselves, not less.

## Part nine: the thing you can actually use

All of this is wrapped in a website at anhydra dot work.

You paste a protein sequence. It goes through ESM-2 and the trained classifier, and you get back a
score between zero and one with a dial that sweeps up to it. Below that, a map of every amino acid
in the protein coloured by chemistry, so you can see at a glance that a protective protein has
almost none of the water-hating residues that make up a normal protein's core. Below that, any
places where the K-segment actually appears, highlighted in the map. Then the three biophysical
features that pushed the call one way or the other, and a plain-language paragraph written by
Google's Gemini from the model's output — the score, the call, the feature contributions, and
nothing else.

The whole thing runs on a single small server. No GPU. The model is small enough to run on an
ordinary processor, which is itself a design decision — a screening tool that needs a graphics card
is a screening tool most labs will not run.

## Part ten: what it cannot do, said plainly

This is a family classifier. It answers the question "does this sequence belong to the
desiccation-protective families?" It does not answer "how much does this protein protect?" — and no
public dataset exists that would let anyone train the second thing honestly. We say that on the
results page itself, under every score.

The training data is plant-dominated. Despite being inspired by tardigrades, it contains no CAHS
proteins at all, for the simple reason that there are not enough curated ones available.

Our similarity grouping is set at forty percent, and the literature puts the genuinely ambiguous
zone lower, around twenty to thirty-five percent. Getting there needs a far more expensive
computation than a weekend allows. The consequence is that our numbers are optimistic rather than
conservative, and we would rather say that than let somebody discover it.

And the generalization result rests on two held-out families, which are related to each other — one
is a subgroup of the other. Two is not many.

Every one of those limitations is written down in the repository, in a document that exists for
exactly that purpose. A result you cannot argue with is a result nobody can check — and the whole
point of this project is that you can check it.
