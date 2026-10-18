# Prompt: build the AnHydra About page

You are building the **About** page for AnHydra, a web tool that screens protein sequences for
desiccation-protective character. Build only the page body described below. The site around it
(header, logo, navigation, footer) already exists, so do not add or duplicate any of it.

![About page layout wireframe](about-page-layout.svg)

The wireframe (`docs/about-page-layout.svg`) shows structure only. Its greys are placeholders,
not colours to use.

## Theme

Do **not** define a theme. Add no colours, fonts, font sizes, radii, shadows or CSS variables of
your own. Use the design tokens and existing components (cards, buttons, chips, headings, icons) that the
site already defines, so the page matches the rest of AnHydra and follows any theme change
automatically. Any new CSS should be layout only (grid, gaps, wrapping), expressed in the site's
existing spacing tokens.

## Page body, in this order

### 1. Built with

A heading and a row of chips that wraps on narrow screens:

ESM-2 · PyTorch · scikit-learn · FastAPI · React · Gemini API · Auth0 · Vultr · Caddy · PostgreSQL

### 2. About us

A heading, one lead line, then two short paragraphs. Use this copy:

> **Lead:** An animal smaller than a grain of sand can lose almost all its water and come back to
> life. We wanted to know which proteins make that possible.
>
> Tardigrades survive drying out with the help of a few protein families: CAHS proteins in
> tardigrades, and LEA proteins and dehydrins in plants. Finding more proteins like them could
> help vaccines, medicines and crops survive without refrigeration. AnHydra is a first-pass
> filter: paste a sequence, see whether it looks like one of the protective families, and see why.
>
> Our model scored 0.987 on the test we designed to be hard. Instead of celebrating, we went
> looking for the catch and found it: our negative examples made the task easier than it looked.
> We rebuilt the data and reported the honest number.

### 3. The team

A heading and four cards in a responsive grid: four across on desktop, two on tablet, one on
phone. Each card has **only**:

- the member's **name**, and
- a row of three **icon widgets**: GitHub, LinkedIn, Website.

No photos, roles, bios or descriptions.

Icon widgets:

- Icons only, no visible text labels.
- Use the GitHub mark, the LinkedIn "in" mark and a globe for the website. If the site already
  has an icon set, take them from it; otherwise use inline SVGs.
- Icons take their colour from the surrounding text (`currentColor`) so they follow the theme.
  Hover and focus states come from the site's existing button styles.
- Each widget is a link with an accessible name that includes the person, for example
  `aria-label="Abdul Sidani on GitHub"`, plus a matching tooltip (`title`).
- All three widgets render on every card. If a URL is ever removed from the data, hide that
  widget rather than rendering a dead link.
- Links open in a new tab with `rel="noopener noreferrer"`.
- Make each widget a comfortable tap target on phones (about 44 × 44 px), sized with the site's
  existing spacing tokens.

Keep the member data in one list so content edits never touch markup:

| Name | GitHub | LinkedIn | Website |
| --- | --- | --- | --- |
| Abdul Sidani | https://github.com/abdulksidani-png | https://www.linkedin.com/in/abdulrahman-sidani/ | https://www.linkedin.com/in/abdulrahman-sidani/ |
| Benjamin Berrizbeitia | https://github.com/Benberrizb | https://www.linkedin.com/in/berrizbeitia/ | https://www.linkedin.com/in/berrizbeitia/ |
| Gayathri Gunda | https://github.com/Gayathri-Gunda | https://www.linkedin.com/in/gayathri-gunda/ | https://www.linkedin.com/in/gayathri-gunda/ |
| Vitor Ribeiro | https://github.com/bolachala | https://www.linkedin.com/in/vitor-gonzaga-feres-ribeiro-41b572339/ | https://www.linkedin.com/in/vitor-gonzaga-feres-ribeiro-41b572339/ |

The **Website** widget is always shown. Until a member has a personal site, its URL is a
placeholder pointing to their LinkedIn, so the website field can be swapped for a real URL later
with no other changes. Keep `website` a separate field in the data (not derived from `linkedin`)
and mark each placeholder with a `// TODO: replace with personal website` comment. Do not invent
URLs.

## Requirements

- The page is public: readable without signing in.
- Page title: "About us — AnHydra".
- No horizontal scroll at phone width; chips and cards wrap.
- Visible keyboard focus on every link and button.

## Done when

- The three sections render in the order above, inside the site's existing header and footer.
- `git diff` adds no colour values, font declarations or new CSS variables.
- The layout has been checked at phone, tablet and desktop widths.
- The project's existing tests and build pass.
