# About page plan

A content and layout plan for the AnHydra **About** page: who we are, our mission, where the
project was made, and one widget per team member.

This document is a plan only. It is written to be independent of the current implementation,
since the site is being rebuilt top to bottom.

> **Theme rule.** This page defines no theme of its own: no colours, fonts, radii, spacing values
> or CSS variables. It uses whatever design tokens and components the rebuilt site defines, so it
> matches the rest of AnHydra by construction and follows any theme change automatically.

---

## Layout

![About page layout wireframe](about-page-layout.svg)

The wireframe shows structure only. Its greys are placeholders, not colours to use.

| # | Section | Contents |
| --- | --- | --- |
| 0 | Header | The site's shared header and navigation, with "About us" marked as the current page |
| 1 | About us | One lead line and two or three short paragraphs |
| 2 | Mission statement | A pull-quote and four principle cards |
| 3 | Made at SwampHacks XII | Five fact tiles and a sentence or two on how we worked |
| 4 | The team | Four member widgets |
| 5 | Built with | Tech chips and a "Screen a sequence" call to action |
| — | Footer | The site's shared footer |

---

## 1. About us

Plain-language intro:

- An animal smaller than a grain of sand can dry out almost completely and come back to life.
  A few protein families (CAHS proteins in tardigrades, LEA proteins and dehydrins in plants) make
  that possible.
- Finding more of them could help vaccines, medicines and crops survive without refrigeration.
- AnHydra is a first-pass filter: paste a sequence, see whether it looks like a protective family,
  and see **why**.
- The honest-number story: our model scored 0.987 on the test we designed to be hard. We went
  looking for the flaw, found it in our negative examples, rebuilt the data and reported the honest
  number.

## 2. Mission statement

Pull-quote:

> Find the proteins that let life survive without water, and be honest about what a model can and
> cannot tell you.

Four numbered principle cards:

1. **Triage, not prophecy.** "Does this look like a protective family?", never "how well will it
   protect?"
2. **No made-up numbers.** If the model can't score, the site says so.
3. **Doubt good results.** Our best finding came from questioning our best score.
4. **Explain every score.** Each result shows the features behind it, in plain language.

## 3. Made at SwampHacks XII

Fact tiles:

| Event | Host | Dates | Build time | Team |
| --- | --- | --- | --- | --- |
| SwampHacks XII | University of Florida | October 16–18, 2026 | About 36 hours | Four developers |

Then one or two sentences: we split the work into lanes (data and model, backend and auth,
frontend, domain and deploy) so four people could push to one repository without colliding.
Optional links: the Devpost submission and the demo video.

## 4. The team: member widgets

One reusable widget, rendered four times from a single data source, so content edits never touch
markup.

### Widget anatomy

1. **Photo** in a fixed 4:5 portrait frame. The member's initials sit underneath, so a missing or
   failed image still looks intentional.
2. **Name** and **role** (one line).
3. **What they built**: three or four short bullets.
4. **Bio** and **fun fact**, shown only when filled in.
5. **Links** (GitHub, LinkedIn, website), only those present, pinned to the bottom so all four
   cards line up.

Grid: four across on desktop, two on tablet, one on phone.

### Data shape

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | |
| `initials` | yes | Photo fallback |
| `role` | yes | One line |
| `contributions` | yes | Three or four bullets |
| `photo` | no | 4:5 portrait, about 800 × 1000 px, under ~300 KB |
| `bio` | no | Two or three sentences |
| `funFact` | no | One sentence |
| `links.github` / `links.linkedin` / `links.website` | no | |

### Content

| Member | Initials | Role | What they built | GitHub |
| --- | --- | --- | --- | --- |
| Abdul Sidani | AS | Data, model & evaluation | Data pipeline and ESM-2 embeddings · training and the two-tier evaluation · confound checks that caught the flawed negatives · results page redesign | `abdulksidani-png` |
| Benjamin Berrizbeitia | BB | Backend, auth & release | Auth0 token verification and user accounts · sign-in design across backend and frontend · release and deployment checks · Gemini model selection fixes | `Benberrizb` |
| Gayathri Gunda | GG | Frontend design | First AnHydra React results page · the dark "water column" look · the hydra mark | `Gayathri-Gunda` |
| Vitor Ribeiro | VR | Domain, sign-in & deploy | Registered anhydra.work · Auth0 for Google and .edu sign-in · sign-in page and account menu | _needed_ |

## 5. Built with

ESM-2 · PyTorch · scikit-learn · FastAPI · React · Gemini API · Auth0 · Vultr · Caddy ·
PostgreSQL · anhydra.work

Followed by a "Screen a sequence →" button back to the screener.

---

## Behaviour

- **Public.** Readable without signing in.
- **Navigation.** "About us" in the site header and footer; "Screen a sequence" on this page.
- **Page title.** "About us — AnHydra".
- **Accessibility.** Alt text on every photo, visible keyboard focus on links, and initials hidden
  from screen readers (the name already says who it is).

---

## Checklist

- [ ] Each member sends a bio, fun fact, links and a photo
- [ ] Vitor's GitHub handle
- [ ] Final wording for the About us paragraphs signed off by the team
- [ ] Page built after the site rebuild, using only the rebuilt site's tokens and components
- [ ] Layout checked at phone, tablet and desktop widths, including the missing-photo fallback
