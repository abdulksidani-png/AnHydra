# Submission checklist

SwampHacks XII · Devpost due **Sunday 8:00 AM**. Work top to bottom; nothing here takes long, and
every one of them has sunk a good project before.

## Before you touch Devpost

- [ ] `bash scripts/check_site.sh https://anhydra.work` — every line PASS.
- [ ] Backup video recorded and uploaded unlisted ([docs/DEMO.md](DEMO.md) has the shot list).
- [ ] Repo is **public**. The AI track requires it and judges read the code.
- [ ] `.env` is not in the repo. `git log --all --full-history -- .env` should return nothing.
- [ ] README renders correctly on github.com — check the tables, not just the text.

## The Devpost entry

- [ ] **Title:** AnHydra
- [ ] **Tagline:** one line — *"Paste a protein sequence. Find out whether it looks like it can
      survive drying out."*
- [ ] **Built with:** python, pytorch, scikit-learn, fastapi, esm-2, gemini, blast, vultr, caddy
- [ ] **Try it out** links: https://anhydra.work and the GitHub repo. Both, every time.
- [ ] **Video** link pasted in.
- [ ] Description covers, in this order: the tardigrade hook, the cold-chain problem, what the tool
      does, the family-holdout result (0.818 vs BLAST 0.739), the K-segment discovery, and the
      limitations. The README is already in that order — lift from it.
- [ ] **Every teammate added to the submission.** A teammate who is not on the Devpost entry did not
      compete, as far as the judges are concerned. Check the list by name, out loud, against who is
      in the room.

## Track opt-ins — tick each box on the form

- [ ] Most Creative Use of AI (primary)
- [ ] Overall / Hack of the Year
- [ ] Easy on the Eyes

## Sponsor prizes

- [ ] **Vultr** — the app runs on a Vultr instance. Say so explicitly in the description; some
      sponsor prizes are judged on a keyword search of entries.
- [ ] **Gemini API** — writes the plain-language readout. Same: name it.
- [ ] **GoDaddy Registry** — anhydra.work. Name the registrar.
- [ ] **DEV** — post the write-up to dev.to and link it from the Devpost entry.

## Last thing

- [ ] Submit at least **thirty minutes early**. Devpost gets slow at the deadline and the form does
      not care that you were nearly finished.
