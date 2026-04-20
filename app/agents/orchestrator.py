"""
Orchestrator Agent (Router) — Multi-Agent Clinical Routing
Reads patient context, detects ALL relevant clinical intents in a message,
calls each specialist agent in parallel, then synthesizes a unified response.

Supports: diabetes | blood_pressure | glands | general
"""
import asyncio
from app.db.supabase_client import get_supabase
from app.agents.clinical.diabetes_agent import DiabetesAgent
from app.agents.clinical.bp_agent import BloodPressureAgent
from app.agents.clinical.glands_agent import GlandsAgent
from app.schemas.chat_schema import ChatRequest, ChatResponse
from datetime import datetime
import google.generativeai as genai
from app.core.config import get_settings
from app.core.prompts import (
    INTENT_CLASSIFIER_PROMPT,
    SYNTHESIS_PROMPT,
    GENERAL_FALLBACK_PROMPT,
    _language_instruction,
)

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)

# ── Clinical agent singletons ────────────────────────────────────────────────
diabetes_agent       = DiabetesAgent()
blood_pressure_agent = BloodPressureAgent()
glands_agent         = GlandsAgent()

AGENT_MAP = {
    "diabetes":       diabetes_agent,
    "blood_pressure": blood_pressure_agent,
    "glands":         glands_agent,
}


# ── Multi-intent classification ───────────────────────────────────────────────

async def _classify_all_intents(
    message: str,
    patient_diseases: list[str],
) -> list[str]:
    """
    Detect ALL clinical intents in the patient's message.
    Returns a list of matched categories (can be multiple).

    Example: "my blood sugar is high and my pressure too" → ["diabetes", "blood_pressure"]
    """
    model = genai.GenerativeModel("gemini-2.5-flash")
    diseases_hint = ", ".join(patient_diseases) if patient_diseases else "unknown"

    prompt = INTENT_CLASSIFIER_PROMPT.format(
        diseases_hint=diseases_hint,
        message=message,
    )
    response = model.generate_content(prompt)
    raw = response.text.strip().lower()
    intents = [i.strip() for i in raw.split(",") if i.strip()]
    # Validate against known categories
    valid = {"diabetes", "blood_pressure", "glands", "general"}
    return [i for i in intents if i in valid] or ["general"]


# ── Synthesis: combine multiple agent answers ─────────────────────────────────

async def _synthesize_responses(
    patient_name: str,
    question: str,
    agent_answers: dict[str, str],
    language: str = "ar",
) -> str:
    """
    When multiple agents answered, synthesize their outputs into one
    coherent, flowing response in the chosen language.
    """
    if len(agent_answers) == 1:
        return list(agent_answers.values())[0]

    sections = "\n\n".join(
        f"=== Specialty: {agent} ===\n{answer}"
        for agent, answer in agent_answers.items()
    )

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = SYNTHESIS_PROMPT.format(
        patient_name=patient_name,
        language_instruction=_language_instruction(language),
        sections=sections,
        question=question,
    )
    response = model.generate_content(prompt)
    return response.text


# ── Main routing function ─────────────────────────────────────────────────────

async def route_clinical(request: ChatRequest) -> ChatResponse:
    """
    Route a chat message to ALL relevant clinical agents (multi-agent),
    then synthesize their answers into a single coherent response.
    """
    supabase = get_supabase()
    language = request.language  # "ar" or "en" from the frontend

    result = (
        supabase.table("patients")
        .select("*")
        .eq("id", request.patient_id)
        .single()
        .execute()
    )
    patient_data     = result.data or {}
    patient_name     = patient_data.get("full_name", "Patient")
    patient_diseases = patient_data.get("diseases", [])

    # 1. Detect ALL intents in the message
    intents = await _classify_all_intents(request.message, patient_diseases)
    print(f"🧠 Detected intents: {intents}")

    # 2. Call all matched clinical agents in parallel
    clinical_intents = [i for i in intents if i in AGENT_MAP]

    if clinical_intents:
        tasks = {
            intent: AGENT_MAP[intent].answer(request.message, patient_data, language)
            for intent in clinical_intents
        }
        answers = dict(zip(
            tasks.keys(),
            await asyncio.gather(*tasks.values())
        ))
        agents_used = list(answers.keys())
    else:
        # General fallback
        model = genai.GenerativeModel("gemini-2.5-flash")
        fallback_prompt = GENERAL_FALLBACK_PROMPT.format(
            language_instruction=_language_instruction(language),
            patient_name=patient_name,
            message=request.message,
        )
        fallback = model.generate_content(fallback_prompt).text
        answers = {"general": fallback}
        agents_used = ["general"]

    # 3. Synthesize into one unified response
    final_reply = await _synthesize_responses(
        patient_name, request.message, answers, language
    )

    return ChatResponse(
        reply=final_reply,
        agent_used=", ".join(agents_used),  # e.g. "diabetes, blood_pressure"
        sources=[],
        timestamp=datetime.utcnow(),
    )


async def evaluate_daily_report(patient_id: str, report_data: dict, language: str = "ar") -> str:
    """Takes a structured daily report, converts to natural text, and routes it to clinical agents."""
    details = []
    
    # Adherence
    if report_data.get("meds_taken") is not None:
        if report_data["meds_taken"]:
            details.append("I took my medication today.")
            if report_data.get("meds_on_time"):
                details.append("I took it on time.")
            else:
                details.append("But I did NOT take it on time.")
        else:
            details.append("I did NOT take my medication today.")
            
    # Sugar
    sugar_parts = []
    for k, name in [("sugar_morning", "Morning"), ("sugar_noon", "Noon"), ("sugar_evening", "Evening")]:
        if report_data.get(k):
            sugar_parts.append(f"{name}: {report_data[k]}")
    if sugar_parts:
        details.append("My blood sugar readings - " + ", ".join(sugar_parts) + ".")
        
    # BP
    bp_parts = []
    if report_data.get("bp_morning_systolic") and report_data.get("bp_morning_diastolic"):
        bp_parts.append(f"Morning: {report_data['bp_morning_systolic']}/{report_data['bp_morning_diastolic']}")
    if report_data.get("bp_evening_systolic") and report_data.get("bp_evening_diastolic"):
        bp_parts.append(f"Evening: {report_data['bp_evening_systolic']}/{report_data['bp_evening_diastolic']}")
    if bp_parts:
        details.append("My blood pressure readings - " + ", ".join(bp_parts) + ".")
        
    # Notes
    if report_data.get("notes"):
        details.append(f"Additional notes: {report_data['notes']}")
        
    if not details:
        message = "I have no specific data for my daily report today. Can you give me some general advice?"
    else:
        message = "This is my daily report:\n" + "\n".join(details) + "\n\nPlease give me your clinical advice based on these numbers."
        
    req = ChatRequest(patient_id=patient_id, message=message, language=language)
    resp = await route_clinical(req)
    return resp.reply
