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

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

PROMPT_TEMPLATE = """\
You are explaining a protein-screening result to a biologist. Be concise, concrete, and honest.

The TardiScreen model classifies whether a protein sequence belongs to the desiccation-protective
families (CAHS / LEA / other anhydrobiosis IDPs). It does NOT predict how much a protein protects.

Sequence summary:
- Protection-family score: {score:.2f} (0 = unlike protective families, 1 = very like them)
- Family call: {label}
- Nearest training-set protective sequence by embedding similarity: {homolog}
- Auxiliary biophysical model contributions (feature: signed contribution):
{feature_lines}

Contributions are standardized feature values times logistic coefficients, NOT raw measurements
or residue fractions. Positive contributions support the auxiliary protective-family call;
negative contributions oppose it. They explain a separate biophysical model, not the ESM-2 score.
Embedding proximity is not evidence of homology. An absent nearest sequence does not establish
novelty or the absence of homologs in public databases.

Write 2-3 sentences describing the score, the supporting or opposing auxiliary signatures, and a
reasonable next lab step. Always state that this is a family/triage signal, not measured protection
efficacy. Do not infer raw feature values, novelty, or experimental protection.
"""


def build_prompt(score: float, label: str, homolog: str | None,
                 top_features: list[tuple[str, float]]) -> str:
    feature_lines = "\n".join(f"  - {name}: {value:.3f}" for name, value in top_features)
    return PROMPT_TEMPLATE.format(
        score=score, label=label, homolog=homolog or "none found", feature_lines=feature_lines
    )


API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_S = float(os.environ.get("GEMINI_TIMEOUT_S", "12"))


def explain(score: float, label: str, homolog: str | None,
            top_features: list[tuple[str, float]]) -> str:
    """Call Gemini and return the readout, falling back to a local template on any failure.

    The demo must never 500 because an external API is down, rate-limited (free tier is easy to
    exhaust), or slow — so every failure path returns `_offline_readout` instead of raising.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _offline_readout(score, label, top_features)

    prompt = build_prompt(score, label, homolog, top_features)
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
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        if not text:                      # safety filter or an empty candidate
            raise ValueError("empty response from Gemini")
        return text
    except Exception as exc:              # noqa: BLE001 — the readout is a nice-to-have, never fatal
        # Do not log exception text: upstream responses may contain request details or credentials.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        print(f"[explain] Gemini unavailable ({type(exc).__name__}, HTTP {status}); using offline readout.")
        return _offline_readout(score, label, top_features)


def _offline_readout(score: float, label: str, top_features: list[tuple[str, float]]) -> str:
    """No-API fallback so the app still demos if Gemini is down or rate-limited."""
    drivers = ", ".join(name for name, _ in top_features[:3]) or "its overall composition"
    verdict = "worth prioritizing for wet-lab testing" if score >= 0.5 else "unlikely to be protective"
    # The score is always P(protective) — never describe it as the character of the negative class.
    return (f"This sequence scores {score:.2f} for desiccation-protective family character "
            f"(call: {label}), driven mainly by {drivers}. On that basis it is {verdict}. Note: this "
            f"is a family/triage signal, not a measured protection efficacy.")


if __name__ == "__main__":
    print(_offline_readout(0.81, "protective",
                           [("low_complexity", 0.9), ("gly_ser_his", 0.4), ("fraction_charged", 0.35)]))
