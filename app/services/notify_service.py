"""
Notification Service
Handles:
- Missed dose alerts to family members (via email from patient_settings)
- Weekly medical summaries to doctors (via email from patient_settings)
"""
from app.db.supabase_client import get_supabase
from app.services.email_service import send_missed_dose_email, send_weekly_doctor_report_email


async def _get_patient_settings(patient_id: str) -> dict:
    """Fetch patient notification settings from Supabase safely without crashing if empty."""
    supabase = get_supabase()
    result = (
        supabase.table("patient_settings")
        .select("*")
        .eq("patient_id", patient_id)
        .execute()
    )
    if not result.data or len(result.data) == 0:
        return {}
    return result.data[0]


async def send_missed_dose_alert(
    patient_id: str,
    patient_name: str,
    medication_name: str,
) -> bool:
    """
    Send a missed dose alert to the family member's email.
    Reads the family_email from patient_settings and checks if alerts are enabled.
    """
    settings = await _get_patient_settings(patient_id)

    if not settings:
        print(f"[NOTIFY] No settings found for patient {patient_id}. Alert skipped.")
        return False

    if not settings.get("notifications_enabled", False):
        return False
        
    if not settings.get("missed_dose_alert_enabled", False):
        return False

    family_email = settings.get("family_email")
    if not family_email:
        print(f"[NOTIFY] No family_email configured for patient {patient_id}")
        return False

    return await send_missed_dose_email(
        to=family_email,
        patient_name=patient_name,
        medication_name=medication_name,
    )


async def send_weekly_doctor_summary(
    patient_id: str,
    patient_name: str,
    summary_html: str,
    override_email: str | None = None,
) -> bool:
    """
    Email a weekly medical summary to the patient's doctor.
    Uses the doctor_email from patient_settings unless override_email is provided.
    Checks weekly_report_enabled flag.
    """
    settings = await _get_patient_settings(patient_id)

    if not settings.get("weekly_report_enabled", False):
        return False

    doctor_email = override_email or settings.get("doctor_email")
    if not doctor_email:
        print(f"[NOTIFY] No doctor_email configured for patient {patient_id}")
        return False

    return await send_weekly_doctor_report_email(
        to=doctor_email,
        patient_name=patient_name,
        report_html=summary_html,
    )