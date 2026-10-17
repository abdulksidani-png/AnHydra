"""Plain-language "why this score" readout, via the Gemini API.

Owner: App/Model. This earns its place in the product — it turns a number and a feature vector into a
sentence a biologist can act on. Keep the honest framing: this is a triage/prioritization aid, not an
efficacy claim.
"""

from __future__ import annotations

import os

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

PROMPT_TEMPLATE = """\
You are explaining a protein-screening result to a biologist. Be concise, concrete, and honest.

The TardiScreen model classifies whether a protein sequence belongs to the desiccation-protective
families (CAHS / LEA / other anhydrobiosis IDPs). It does NOT predict how much a protein protects.

Sequence summary:
- Protection-family score: {score:.2f} (0 = unlike protective families, 1 = very like them)
- Family call: {label}
- Nearest known protective homolog: {homolog}
- Biophysical signatures (feature: value):
{feature_lines}

Write 2-3 sentences explaining which signatures drove this score and what a lab should do next
(e.g. "prioritize for wet-lab testing" or "unlikely to be worth expressing"). Do not overclaim.
"""


def build_prompt(score: float, label: str, homolog: str | None,
                 top_features: list[tuple[str, float]]) -> str:
    feature_lines = "\n".join(f"  - {name}: {value:.3f}" for name, value in top_features)
    return PROMPT_TEMPLATE.format(
        score=score, label=label, homolog=homolog or "none found", feature_lines=feature_lines
    )


def explain(score: float, label: str, homolog: str | None,
            top_features: list[tuple[str, float]]) -> str:
    """Call Gemini and return the readout. Falls back to a template string if the key is missing.

    TODO (app owner): POST build_prompt(...) to the Gemini REST endpoint with GEMINI_API_KEY.
    Handle 429 gracefully (free-tier limits) — fall back to `_offline_readout` rather than erroring
    the whole request.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _offline_readout(score, label, top_features)
    raise NotImplementedError("App owner: implement the Gemini REST call (prompt is ready above).")


def _offline_readout(score: float, label: str, top_features: list[tuple[str, float]]) -> str:
    """No-API fallback so the app still demos if Gemini is down or rate-limited."""
    drivers = ", ".join(name for name, _ in top_features[:3]) or "its overall composition"
    verdict = "worth prioritizing for wet-lab testing" if score >= 0.5 else "unlikely to be protective"
    return (f"This sequence scores {score:.2f} for {label}-family character, driven mainly by "
            f"{drivers}. On that basis it is {verdict}. Note: this is a family/triage signal, not a "
            f"measured protection efficacy.")


if __name__ == "__main__":
    print(_offline_readout(0.81, "protective",
                           [("low_complexity", 0.9), ("gly_ser_his", 0.4), ("fraction_charged", 0.35)]))
