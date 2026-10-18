# About page plan

A plan for the AnHydra **About** page: who we are, our mission, where the project was made, and
one widget per team member.

> **Theme rule.** This page defines no theme of its own. No new colours, fonts, radii, spacing
> values or CSS custom properties. Every visual decision comes from the tokens and component
> classes the site already uses, so the About page looks like the rest of AnHydra by construction
> and follows any future theme change automatically.

---

## 1. Where it lives

| Surface | Today | Plan |
| --- | --- | --- |
| React app (`frontend/anhydra-frontend/`) | No About page | **Build it here** (primary target) |
| FastAPI static page (`app/static/about.html`, served at `/about`) | Exists, with its own inline copy of the tokens | Keep serving until the React deploy goes live, then retire it |

`frontend/anhydra-frontend/` is the integrated app that `deploy/Caddyfile.react.template` ships.
Caddy already falls back to `index.html` for any path outside the API matcher, so `/about` reaches
the React app with no deploy changes.

---

## 2. Page structure

Top to bottom, inside the existing `.shell` / `.stack` layout:

1. **Masthead** – the same `Masthead` component as the screener, plus a link back to "Screen a
   sequence".
2. **About us** – who we are and why we built AnHydra (two or three short paragraphs).
3. **Mission statement** – one pull-quote and four supporting principles.
4. **Made at SwampHacks XII** – the hackathon context.
5. **The team** – four member widgets.
6. **Built with** – the tech list and a call to action back to the screener.
7. **Footer** – the site's existing footer line.

### 2.1 About us

Plain-language intro, adapted from `TEAM.md` and the current `about.html`:

- An animal smaller than a grain of sand can dry out almost completely and come back to life.
  A few protein families (CAHS, LEA, dehydrins) make that possible.
- Finding more of them could help vaccines, medicines and crops survive without refrigeration.
- AnHydra is a first-pass filter: paste a sequence, see whether it looks like a protective family,
  and see **why**.
- The honest-number story: we scored 0.987 on our hardest test, went looking for the flaw, found
  it in our negative set, and rebuilt the data.

### 2.2 Mission statement

Pull-quote (final wording from `TEAM.md`):

> Find the proteins that let life survive without water, and be honest about what a model can and
> cannot tell you.

Supporting principles, rendered as four small numbered cards:

1. **Triage, not prophecy** – "Does this look like a protective family?", never "how well will it
   protect?"
2. **No made-up numbers** – if the model can't score, the site says so.
3. **Doubt good results** – our best finding came from questioning our best score.
4. **Explain every score** – each result shows the features behind it, in plain language.

### 2.3 Created at the hackathon

A short block with a fact list:

| Fact | Value |
| --- | --- |
| Event | SwampHacks XII |
| Host | University of Florida |
| Dates | October 16–18, 2026 |
| Build time | About 36 hours |
| Team | Four developers |

One or two sentences on how we worked: the project was split into lanes (data and model, backend
and auth, frontend, domain and deploy) so four people could push to one repository without
colliding. Optional: link to the Devpost submission (`docs/SUBMISSION.md`) and the demo.

---

## 3. Member widgets

One reusable component rendered four times from a data file, so content edits never touch markup.

### 3.1 Data: `src/content/team.ts`

```ts
export interface TeamMember {
  name: string;
  initials: string;           // fallback when there is no photo
  role: string;               // one line, e.g. "Data, model & evaluation"
  photo?: string;             // e.g. "/team/abdul.jpg"
  contributions: string[];    // 3–4 short bullets
  bio?: string;               // "About me" (optional until filled in)
  funFact?: string;
  links: { github?: string; linkedin?: string; website?: string };
}
```

### 3.2 Content

| Member | Initials | Role | Contributions | GitHub |
| --- | --- | --- | --- | --- |
| Abdul Sidani | AS | Data, model & evaluation | Data pipeline and ESM-2 embeddings · training and the two-tier evaluation · confound checks that caught the flawed negatives · results page redesign | `abdulksidani-png` |
| Benjamin Berrizbeitia | BB | Backend, auth & release | Auth0 token verification and user accounts · sign-in design across backend and frontend · release and deployment checks · Gemini model selection fixes | `Benberrizb` |
| Gayathri Gunda | GG | Frontend design | First AnHydra React results page · the dark "water column" look · the hydra mark | `Gayathri-Gunda` |
| Vitor Ribeiro | VR | Domain, sign-in & deploy | Registered anhydra.work · Auth0 for Google and .edu sign-in · sign-in page and account menu | _needed_ |

Still to collect from each member (currently `TODO` in `TEAM.md`): bio, fun fact, LinkedIn,
website, photo. Vitor's GitHub handle is also missing. Fields left empty are simply not rendered.

### 3.3 Component: `src/components/MemberCard.tsx`

Each widget shows, in order:

1. **Photo** in a fixed 4:5 portrait frame. Initials sit underneath, so a missing or failed image
   still looks intentional.
2. **Name** (heading) and **role** (one line).
3. **Contributions** as a short bullet list.
4. **Bio** and **fun fact**, only when present.
5. **Links** (GitHub, LinkedIn, website), only those present, pinned to the bottom of the card so
   all four cards line up.

The four cards sit in a responsive grid: four across on wide screens, two on tablets, one on
phones.

### 3.4 Photos

Move the photo slot from `app/static/team/` to `frontend/anhydra-frontend/public/team/` with the
same filenames and guidance (`abdul.jpg`, `benjamin.jpg`, `gayathri.jpg`, `vitor.jpg`; 4:5,
about 800 × 1000 px, under ~300 KB).

---

## 4. Styling: reuse only

**Allowed:**

- Tokens from `src/styles/tokens.css`: `--abyss`, `--column`, `--column-raised`, `--foam`,
  `--silt`, `--silt-deep`, `--rule*`, `--glow`, `--glow-deep`, `--amber`, `--font-serif`,
  `--font-mono`, `--gap-*`, `--radius`, `--radius-sharp`, `--measure`.
- Existing classes from `src/styles/app.css`: `.shell`, `.stack`, `.card`, `.card--tight`,
  `.card__label`, `.card__lede`, `.row`, the `.masthead*` family.

**Not allowed:**

- New `:root` variables, hex/rgb literals, new font families, or a separate About stylesheet with
  its own palette.
- Copying the inline token block from `app/static/about.html`. It has drifted from `tokens.css`
  (for example `--radius: 10px` vs `6px`, different `--abyss`), which is exactly what this rule
  prevents.

New CSS is limited to **layout** (the member grid, the photo aspect ratio, the fact list) and is
added to `app.css` under an `/* ========== About ========== */` section, written entirely in
existing tokens.

---

## 5. Routing and auth

- The app has no router today. Add a small pathname check in `App.tsx` (`/about` → `AboutPage`)
  rather than a routing dependency.
- The About page is **public**: the check runs *before* the auth gate, so visitors can read it
  without signing in.
- Navigation: an "About us" link in the masthead and footer of the screener; a "Screen a
  sequence" link on the About page. `Masthead` currently requires `runNumber` and `screenedAt`;
  make the run metadata optional so the About page can reuse it.
- Set `document.title` to "About us — AnHydra" on mount.

---

## 6. Files

| File | Change |
| --- | --- |
| `src/content/team.ts` | New: member data and mission/hackathon copy |
| `src/components/MemberCard.tsx` | New: one member widget |
| `src/components/AboutPage.tsx` | New: page sections in the order above |
| `src/App.tsx` | Route `/about` ahead of the auth gate |
| `src/components/Masthead.tsx` | Optional run metadata; About link |
| `src/styles/app.css` | About layout section, existing tokens only |
| `public/team/*.jpg` | Member photos |
| `TEAM.md` | Stays the source for wording; update both together |

All paths are relative to `frontend/anhydra-frontend/` except `TEAM.md`.

---

## 7. Checklist

- [ ] Each member fills in bio, fun fact, links and sends a photo
- [ ] Vitor's GitHub handle
- [ ] `team.ts` and `MemberCard`
- [ ] `AboutPage` with all six sections
- [ ] `/about` route, public, before the auth gate
- [ ] Nav links both ways
- [ ] `git diff` on `app.css` contains no new custom properties or colour literals
- [ ] Layout checked at phone, tablet and desktop widths; missing-photo fallback checked
- [ ] Keyboard focus and alt text on photos and links
- [ ] `npm test` and `npm run build` pass
- [ ] After the React deploy is live, retire `app/static/about.html` and the FastAPI `/about` route
