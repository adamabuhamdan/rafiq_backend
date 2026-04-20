"""
Reporting Agent (functional)
Generates daily patient summaries and weekly professional medical reports for doctors.
Updated to fetch patient data from Supabase using patient_id.
"""
import google.generativeai as genai
from datetime import datetime
from app.core.config import get_settings
from app.db.supabase_client import get_supabase
from app.core.prompts import WEEKLY_REPORT_PROMPT, _language_instruction

settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)


class ReportingAgent:
    name = "reporting_agent"

    async def _get_patient(self, patient_id: str) -> dict:
        """Fetch patient data from Supabase by patient_id."""
        supabase = get_supabase()
        result = (
            supabase.table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )
        return result.data or {}


    async def generate_weekly_doctor_report(
        self,
        patient_data: dict,
        weekly_events: list,
        language: str = "ar",
    ) -> str:
        """Generate a professional weekly report for the treating physician."""
        events_text  = "\n".join([f"- {e}" for e in weekly_events]) or "No events recorded."
        diseases     = patient_data.get("diseases", [])
        diseases_str = ", ".join(diseases) if diseases else "Not specified"

        prompt = WEEKLY_REPORT_PROMPT.format(
            language_instruction=_language_instruction(language),
            patient_name=patient_data.get("full_name"),
            today=datetime.today().strftime("%Y-%m-%d"),
            diseases_str=diseases_str,
            events_text=events_text,
        )
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model.generate_content(prompt).text

    async def generate_weekly_doctor_report_by_id(
        self,
        patient_id: str,
        weekly_events: list,
        language: str = "ar",
    ) -> str:
        """Generate a weekly doctor report, fetching patient data automatically."""
        patient_data = await self._get_patient(patient_id)
        if not patient_data:
            return "Patient data not found."
        return await self.generate_weekly_doctor_report(patient_data, weekly_events, language)

    async def generate_weekly_doctor_report_from_db(
        self,
        patient_data: dict,
        recent_reports: list[dict],
        language: str = "ar",
    ) -> str:
        """Generate a professional weekly report using structured DB daily reports."""
        # Convert reports into a readable text format
        events_lines = []
        for r in recent_reports:
            day = r.get("report_date", "Unknown Date")
            line = f"Date: {day}"
            if r.get("meds_taken") is not None:
                line += f" | Meds Taken: {'Yes' if r['meds_taken'] else 'No'}"
                if r.get("meds_on_time") is not None:
                    line += f" (On Time: {'Yes' if r['meds_on_time'] else 'No'})"
            if r.get("sugar_morning") or r.get("sugar_noon") or r.get("sugar_evening"):
                line += f" | Sugar (M/N/E): {r.get('sugar_morning', '-')}/{r.get('sugar_noon', '-')}/{r.get('sugar_evening', '-')}"
            if r.get("bp_morning_systolic"):
                line += f" | BP (M): {r.get('bp_morning_systolic')}/{r.get('bp_morning_diastolic')}"
            if r.get("bp_evening_systolic"):
                line += f" | BP (E): {r.get('bp_evening_systolic')}/{r.get('bp_evening_diastolic')}"
            if r.get("notes"):
                line += f" | Notes: {r['notes']}"
            if r.get("ai_advice"):
                line += f" | AI Advice Given: {r['ai_advice']}"
            events_lines.append("- " + line)

        events_text = "\n".join(events_lines) if events_lines else "No valid structured events found."
        diseases = patient_data.get("diseases", [])
        diseases_str = ", ".join(diseases) if diseases else "Not specified"

        prompt = WEEKLY_REPORT_PROMPT.format(
            language_instruction=_language_instruction(language),
            patient_name=patient_data.get("full_name"),
            today=datetime.today().strftime("%Y-%m-%d"),
            diseases_str=diseases_str,
            events_text=events_text,
        )
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model.generate_content(prompt).text
