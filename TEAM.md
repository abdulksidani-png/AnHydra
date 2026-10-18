# The AnHydra team

Four developers, one weekend, and a protein classifier we refused to trust until we understood
why it worked. AnHydra was built at **SwampHacks XII** (University of Florida, Oct 16–18, 2026).

---

## Mission

> **Find the proteins that let life survive without water, and be honest about what a model can
> and cannot tell you.**

### What we believe

- **Triage, not prophecy.** AnHydra answers "does this look like a protective family?", never
  "how well will this protect?"
- **No fabricated numbers.** If the model isn't loaded, the app returns an error, not a guess.
- **Doubt good results.** Our best result came from questioning our best score.
- **Explain everything.** Scores include auxiliary biophysical signals and a plain-language
  readout; those signals do not explain the ESM classifier directly.

---

## The developers

| | Developer | Focus |
| --- | --- | --- |
| 🧬 | [Abdul Sidani](#abdul-sidani) | Data, model and evaluation |
| 🛡️ | [Benjamin Berrizbeitia](#benjamin-berrizbeitia) | Backend, auth and release hardening |
| 🎨 | [Gayathri Gunda](#gayathri-gunda) | Frontend design |
| 🌐 | [Vitor Ribeiro](#vitor-ribeiro) | Domain, sign-in and deployment |

### Abdul Sidani

**Role:** Project lead · data and model pipeline · [@abdulksidani-png](https://github.com/abdulksidani-png)

**What I built**
- The data pipeline: UniProt/DisProt pulls, CD-HIT cluster splits and class balancing
- ESM-2 embeddings with a resumable, checkpointed cache
- Training, the two-tier cluster-split evaluation, and the confound checks that caught our flawed
  negative set
- The results page redesign, the hero, and mobile layout

**Links:** [GitHub](https://github.com/abdulksidani-png)

---

### Benjamin Berrizbeitia

**Role:** Backend and security · [@Benberrizb](https://github.com/Benberrizb)

**What I built**
- Auth0 token verification on the backend, with PostgreSQL user accounts and migrations
- The authentication design and the frontend/backend handoff docs
- Release validation, scoring fixes and deployment checks
- The Gemini model selection and explanation fixes

**Links:** [GitHub](https://github.com/Benberrizb)

---

### Gayathri Gunda

**Role:** Frontend design · [@Gayathri-Gunda](https://github.com/Gayathri-Gunda)

**What I built**
- The original AnHydra React results page
- The dark "water column" theme and the hydra mark

**Links:** [GitHub](https://github.com/Gayathri-Gunda)

---

### Vitor Ribeiro

**Role:** Domain, sign-in and deployment

**What I built**
- Registered **anhydra.work** and pointed it at our Vultr server
- Set up the Auth0 tenant (Google sign-in plus `.edu` email accounts)
- The sign-in page, the account menu, and attaching login tokens to scoring requests

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
