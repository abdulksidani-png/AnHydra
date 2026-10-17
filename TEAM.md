# The AnHydra team

Four developers, one weekend, and a protein classifier we refused to trust until we understood
why it worked. AnHydra was built at **SwampHacks XII** (University of Florida, Oct 16–18, 2026).

---

## Mission

> **Find the proteins that let life survive without water, and be honest about what a model can
> and cannot tell you.**

<!--
  Pick one mission statement and delete the rest (or mix them).

  Option A (science-first)
  Make the search for desiccation-protective proteins faster: paste a sequence, get a clear,
  explained answer about whether it looks like the families that let tardigrades dry out and
  come back to life.

  Option B (honesty and rigor)
  Never show a number we cannot defend. When our model scored 0.987 on the task we designed to be
  hard, we went looking for the flaw before celebrating, and we built the tool to say "I don't
  know" instead of inventing an answer.

  Option C (real-world impact)
  Help move medicine and agriculture past the cold chain. Vaccines, clotting factors and crops
  that tolerate drying start with finding the right proteins, and AnHydra is a first-pass filter
  for that search.

  The quote at the top is a blend of A and B.
-->

### What we believe

- **Triage, not prophecy.** AnHydra answers "does this look like a protective family?", never
  "how well will this protect?"
- **No fabricated numbers.** If the model isn't loaded, the app returns an error, not a guess.
- **Doubt good results.** Our best result came from questioning our best score.
- **Explain everything.** Every score comes with the features that drove it, in plain language.

---

## The developers

| | Developer | Focus |
| --- | --- | --- |
| 🧬 | [Abdul Sidani](#abdul-sidani) | Data, model and evaluation |
| 🛡️ | [Benjamin Berrizbeitia](#benjamin-berrizbeitia) | Backend, auth and release hardening |
| 🎨 | [Gayathri Gunda](#gayathri-gunda) | Frontend design |
| 🌐 | [Vitor Ribeiro](#vitor-ribeiro) | Domain, sign-in and deployment |

<!-- Each section has the same fields. Replace anything in _italics with a TODO_. -->

### Abdul Sidani

**Role:** Project lead · data and model pipeline · [@abdulksidani-png](https://github.com/abdulksidani-png)

**What I built**
- The data pipeline: UniProt/DisProt pulls, CD-HIT cluster splits and class balancing
- ESM-2 embeddings with a resumable, checkpointed cache
- Training, the two-tier cluster-split evaluation, and the confound checks that caught our flawed
  negative set
- The results page redesign, the hero, and mobile layout

**About me:** _TODO: school, major, year, what got you into this._

**Links:** [GitHub](https://github.com/abdulksidani-png) · _LinkedIn_ · _Website_

**Fun fact:** _TODO_

---

### Benjamin Berrizbeitia

**Role:** Backend and security · [@Benberrizb](https://github.com/Benberrizb)

**What I built**
- Auth0 token verification on the backend, with PostgreSQL user accounts and migrations
- The authentication design and the frontend/backend handoff docs
- Release validation, scoring fixes and deployment checks
- The Gemini model selection and explanation fixes

**About me:** _TODO_

**Links:** [GitHub](https://github.com/Benberrizb) · _LinkedIn_ · _Website_

**Fun fact:** _TODO_

---

### Gayathri Gunda

**Role:** Frontend design · [@Gayathri-Gunda](https://github.com/Gayathri-Gunda)

**What I built**
- The original AnHydra React results page
- The dark "water column" theme and the hydra mark
- _TODO: anything else you worked on (slides, demo video, pitch, research…)_

**About me:** _TODO_

**Links:** [GitHub](https://github.com/Gayathri-Gunda) · _LinkedIn_ · _Website_

**Fun fact:** _TODO_

---

### Vitor Ribeiro

**Role:** Domain, sign-in and deployment

**What I built**
- Registered **anhydra.work** and pointed it at our Vultr server
- Set up the Auth0 tenant (Google sign-in plus `.edu` email accounts)
- The sign-in page, the account menu, and attaching login tokens to scoring requests

**About me:** _TODO_

**Links:** _GitHub_ · _LinkedIn_ · _Website_

**Fun fact:** _TODO_

---

## How we worked

We split the project into lanes so four people could push to one repo in 36 hours without stepping
on each other:

| Lane | Owner | Files |
| --- | --- | --- |
| Data and model | Abdul | `src/tardiscreen/` |
| Backend and auth | Benjamin | `app/`, `migrations/` |
| Frontend | Gayathri, Abdul | `frontend/`, `app/static/` |
| Domain, sign-in and deploy | Vitor | Auth0, DNS, `deploy/` |

Only the data owner regenerates the dataset or embeddings. Everyone pulls before they start and
before they open a pull request.

## Built with

ESM-2 (Meta AI) · scikit-learn · PyTorch · FastAPI · React + Vite · Gemini API · Auth0 · Vultr ·
Caddy · PostgreSQL · `anhydra.work` (a GoDaddy Registry `.work` domain)

## Thanks

_TODO: mentors, SwampHacks organizers, sponsors, anyone who helped._
