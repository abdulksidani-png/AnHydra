"""Plain-language "why this score" readout, via the Gemini API.

Owner: App/Model. This earns its place in the product — it turns a number and a feature vector into a
sentence a biologist can act on. Keep the honest framing: this is a triage/prioritization aid, not an
efficacy claim.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

PROMPT_TEMPLATE = """\
You are explaining a protein-screening result to a biologist. Be concise, concrete, and honest.

The TardiScreen model classifies whether a protein sequence belongs to the desiccation-protective
families (CAHS / LEA / other anhydrobiosis IDPs). It does NOT predict how much a protein protects.

Sequence summary:
- Protection-family score: {score:.2f} (0 = unlike protective families, 1 = very like them)
- Family call: {label}
- Nearest known protective homolog: {homolog}
{driver_block}{agreement_block}
Rules you must follow:
- A driver's contribution is how much that feature moved the score, NOT the amount of the feature.
  Never restate a contribution as a measured quantity. Describe a measured quantity only from the
  "measured" figure given beside it.
- Positive contribution = pushed toward protective; negative = pushed away.
- These are associations the model learned, not demonstrated causes.

Write 2-3 sentences explaining which signatures drove this score and what a lab should do next
(e.g. "prioritize for wet-lab testing" or "unlikely to be worth expressing"). Do not overclaim.
"""

# Added only when the two models disagree on the call, so the readout says the drivers come from a
# surrogate instead of quietly explaining a score they did not produce.
DISAGREEMENT_NOTE = """
Model agreement: the score above is from the ESM-2 embedding model ({score:.2f}), while the drivers
are from the interpretable biophysical model, which scores this sequence {bio_score:.2f} and so
DISAGREES on the call. Say in one clause that the two disagree and that the drivers explain the
biophysical model, so the reader does not read them as the reason for the headline score.
"""


def _driver_lines(top_features: list[tuple[str, float]], features: dict | None) -> str:
    """Render drivers as contributions, with the measured value beside each when available.

    The distinction matters. A contribution is standardized_value x coefficient, so a NEGATIVE
    contribution can come from a POSITIVE measured value times a negative coefficient. Labelling
    contributions as "value" (which this prompt used to do) invites a fluent, confident, wrong
    sentence about the protein's actual composition.
    """
    lines = []
    for name, contribution in top_features:
        direction = "toward protective" if contribution >= 0 else "away from protective"
        line = f"  - {name}: contribution {contribution:+.3f} ({direction})"
        measured = (features or {}).get(name)
        if isinstance(measured, (int, float)):
            line += f", measured {measured:.3f}"
        lines.append(line)
    return "\n".join(lines)


def build_prompt(score: float, label: str, homolog: str | None,
                 top_features: list[tuple[str, float]], features: dict | None = None,
                 bio_score: float | None = None) -> str:
    """Build the Gemini prompt.

    `features` and `bio_score` are optional so existing callers keep working; pass them when you
    have them, which /score does.
    """
    driver_block = ("- Top drivers (signed contribution to the score):\n"
                    + _driver_lines(top_features, features) + "\n")

    # Surfaced only on disagreement. When the models agree the surrogate is a fair stand-in, and
    # the note would be noise in a 2-3 sentence readout.
    agreement_block = ""
    if bio_score is not None and (bio_score >= 0.5) != (score >= 0.5):
        agreement_block = DISAGREEMENT_NOTE.format(score=score, bio_score=bio_score)

    return PROMPT_TEMPLATE.format(
        score=score, label=label, homolog=homolog or "none found",
        driver_block=driver_block, agreement_block=agreement_block,
    )


API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_S = float(os.environ.get("GEMINI_TIMEOUT_S", "12"))


def explain(score: float, label: str, homolog: str | None,
            top_features: list[tuple[str, float]], features: dict | None = None,
            bio_score: float | None = None) -> str:
    """Call Gemini and return the readout, falling back to a local template on any failure.

    The demo must never 500 because an external API is down, rate-limited (free tier is easy to
    exhaust), or slow — so every failure path returns `_offline_readout` instead of raising.

    `features` are the measured biophysical values (so the prompt can separate "how much of this
    feature there is" from "how much it moved the score"), and `bio_score` is the surrogate model's
    own probability (so a disagreement can be declared rather than hidden). Both optional: without
    them the readout is still correct, just less specific.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _offline_readout(score, label, top_features, bio_score)

    prompt = build_prompt(score, label, homolog, top_features, features, bio_score)
    try:
        import httpx

        response = httpx.post(
            API_URL.format(model=GEMINI_MODEL),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
            },
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        parts = response.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:                      # safety filter or an empty candidate
            raise ValueError("empty response from Gemini")
        return text
    except Exception as exc:              # noqa: BLE001 — the readout is a nice-to-have, never fatal
        print(f"[explain] Gemini unavailable ({type(exc).__name__}: {exc}); using offline readout.")
        return _offline_readout(score, label, top_features, bio_score)


def _offline_readout(score: float, label: str, top_features: list[tuple[str, float]],
                     bio_score: float | None = None) -> str:
    """No-API fallback so the app still demos if Gemini is down or rate-limited."""
    drivers = ", ".join(name for name, _ in top_features[:3]) or "its overall composition"
    verdict = "worth prioritizing for wet-lab testing" if score >= 0.5 else "unlikely to be protective"
    # Same disclosure the Gemini path makes: the drivers belong to the surrogate, so when it
    # disagrees with the score, say so rather than presenting them as the score's reasons.
    caveat = ""
    if bio_score is not None and (bio_score >= 0.5) != (score >= 0.5):
        caveat = (f" Note that the interpretable model disagrees ({bio_score:.2f}), so these "
                  f"drivers explain that model rather than the headline score.")
    # The score is always P(protective) — never describe it as the character of the negative class.
    return (f"This sequence scores {score:.2f} for desiccation-protective family character "
            f"(call: {label}), driven mainly by {drivers}. On that basis it is {verdict}.{caveat} "
            f"Note: this is a family/triage signal, not a measured protection efficacy.")


if __name__ == "__main__":
    print(_offline_readout(0.81, "protective",
                           [("low_complexity", 0.9), ("gly_ser_his", 0.4), ("fraction_charged", 0.35)]))
