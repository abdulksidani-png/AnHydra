# TardiScreen — Weekend game plan

**SwampHacks XII** · Oct 16–18, 2026, Reitz Union, UF
Hacking begins Fri ~8:30 PM · Devpost due **Sun 8:00 AM** · ≈35.5 hrs · team of 2–4.

## The idea in one breath

Turn CAHS biology into an ML screening problem. You can't do wet-lab tardigrade work in a dorm over a
weekend, but the computational side of CAHS research sits squarely in ML. Learn what separates
desiccation-protective proteins from other disordered proteins, then use it to triage new candidates —
a workflow labs genuinely need.

## Tracks we're targeting

- **Most Creative Use of AI** — *primary.* Requires AI/ML to be central + a public repo with README;
  judges read GitHubs and value depth over polish. A custom model on protein embeddings with real
  evals is exactly what they reward, and almost no other team brings real bio-ML.
- **Overall / Hack of the Year** — novel domain + working tool + real use (cold-chain-free biologics)
  scores on innovation, technical achievement, impact, execution.
- **Easy on the Eyes** — free with a clean, deliberate results page.

Not targeting **Least Vibe Coded** (poor fit if building fast with an AI assistant — don't design around it).

## Hour-by-hour

| When | Block |
| --- | --- |
| **Fri 8:30–11:30 PM** | Lock scope, set up, pull data. Repo + README skeleton. Assign roles. Start UniProt pulls (experimental evidence codes) + DisProt/MobiDB hard negatives. Stand up the Vultr host. |
| **Fri–Sat 11:30 PM–2:30 AM** | Dataset + embeddings. Finalize protective / hard-negative / sanity tiers. CD-HIT cluster for a clean split. Embed with ESM-2 (small, CPU). Compute biophysical features in parallel. Kick off runs, then stop. |
| **Sat 2:30–8:00 AM** | **Real rest block — protect it.** Runs finish unattended. Everyone sleeps. |
| **Sat 8:00 AM–12:30 PM** | Evals + interpretability. Cluster-split CV. Two-tier results table. Model comparison, confusion matrix, feature importance. **AI-track centerpiece.** |
| **Sat 12:30–5:30 PM** | Build the app. Sequence-in → score-out UI. Nearest-homolog lookup. Wire Gemini. Deploy to Vultr; point GoDaddy domain at it. |
| **Sat 5:30–9:00 PM** | Polish + README. Clean, legible results page. Write README: problem, data, two-tier evals, honest limits, citations. Screenshots + plots. |
| **Sat–Sun 9:00 PM–12:00 AM** | Devpost + demo + DEV post. Honest framing. Record a 2–3 min demo backup. Publish DEV write-up. Opt into AI, Overall, Easy on the Eyes, Vultr, Gemini, GoDaddy — confirm public-repo link is attached. |
| **Sun 12:00–6:00 AM** | Buffer + second rest. Fix what broke, then sleep. Nothing new goes in after this. |
| **Sun 6:00–8:00 AM** | Final pass → **SUBMIT by 8:00 AM** (late submissions aren't judged). Confirm teammates joined the Devpost team + all opt-ins checked. Rehearse the pitch. Expo/judging 10 AM–12 PM; awards 2:30 PM. |

## Sponsor stack

| Challenge | How it bolts on | Effort |
| --- | --- | --- |
| **Vultr** | Host the app, point the domain at it. No GPU needed. Claim free credits. | Core |
| **Gemini API** | Plain-language "why this score" readout — part of the product. | Core |
| **GoDaddy Registry** | Register `tardiscreen.*`, demo on a real domain. | Core |
| **DEV Writing** | End-of-weekend write-up you'd do anyway. $100 track. | Bonus |
| Auth0 · Tiger Data | Login + time-series store cost build time a judge can't see. | Skip unless done early |
| DeepSpace / Capital One / Solana / Roblox | No sensible fit. | Skip |

**Realistic stack:** AI + Overall + Easy on the Eyes, plus Vultr + Gemini + GoDaddy, plus the DEV
write-up. Protecting the model and the evals is what wins the AI track; extra sponsor chores eat that time.

## Fallback (back pocket only)

**Sperry PlanIt Control** — a self-contained ML challenge (environmental/time-series hazard scoring),
richest sponsor prize pool. Zero connection to CAHS. Keep it only if, by midnight, the protein data
pipeline isn't cooperating and you need a pivot with more worked examples online.

---
_Built from the SwampHacks XII Hacker Guide. The guide lists two start times (8:00 PM in the schedule,
8:30 PM in "Need to Know") — treat 8:30 as the safe start. Verify final details on the Discord and
confirm the public-repo requirement on Devpost._
