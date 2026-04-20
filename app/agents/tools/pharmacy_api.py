"""
Drug Interaction Tool — Powered by Gemini AI
Replaces RxNorm. Analyzes drug-drug interactions using medication names
and active ingredients, returning structured results.

Works for single drug (safety check) or multiple drugs (interaction analysis).
JSON response keys are always in English; summary text follows the caller's language.
"""
import json
import re
import google.generativeai as genai
from app.core.config import get_settings
from app.core.prompts import (
    DRUG_INTERACTION_PROMPT,
    DRUG_INTERACTION_SINGLE_TASK,
    DRUG_INTERACTION_MULTI_TASK,
    _language_instruction,
)

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)


class MedicationInfo:
    def __init__(self, name: str, active_ingredient: str | None = None):
        self.name = name
        self.active_ingredient = active_ingredient or name


async def check_drug_interactions(
    medications: list[MedicationInfo],
    language: str = "ar",
) -> dict:
    """
    Analyze drug interactions using Gemini.

    - Single medication  → safety profile & common warnings.
    - Multiple medications → pairwise interaction analysis.

    Returns a structured dict with status, interactions, and a summary
    in the requested language.
    JSON keys are always English (status, summary, interactions, drugs, severity, description).
    """
    if not medications:
        return {"status": "safe", "interactions": [], "summary": "No medications to analyze."}

    # Build medication list for the prompt
    med_lines = "\n".join(
        f"- {m.name} (active ingredient: {m.active_ingredient})"
        for m in medications
    )

    task = DRUG_INTERACTION_SINGLE_TASK if len(medications) == 1 else DRUG_INTERACTION_MULTI_TASK

    prompt = DRUG_INTERACTION_PROMPT.format(
        task=task,
        med_lines=med_lines,
        language_instruction=_language_instruction(language),
    )

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)

    # Parse JSON from response
    try:
        raw = response.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except Exception:
        # Fallback if JSON parsing fails
        return {
            "status": "warning",
            "summary": response.text,
            "interactions": [],
        }
