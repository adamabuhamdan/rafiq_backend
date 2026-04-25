"""
Patient Settings Routes — GET and PUT patient_settings.
One-to-one with patients table (patient_id is UNIQUE in patient_settings).
"""
from fastapi import APIRouter, HTTPException
from app.schemas.settings_schema import SettingsResponse, SettingsUpdate
from app.db.supabase_client import get_supabase
from datetime import datetime

router = APIRouter(prefix="/settings", tags=["Settings - الإعدادات"])


@router.post("/logout")
async def logout():
    """
    Logout the patient.
    (Primarily client-side token clearance, but this endpoint acknowledges the action).
    """
    # If Supabase required server-side session invalidation via JWT, it would go here.
    # We return a success message so the frontend can proceed to clear local data and navigate.
    return {"message": "Logged out successfully"}


@router.get("/{patient_id}", response_model=SettingsResponse)
async def get_settings(patient_id: str):
    """Retrieve patient notification/contact settings. Auto-creates defaults if not found."""
    supabase = get_supabase()
    result = (
        supabase.table("patient_settings")
        .select("*")
        .eq("patient_id", patient_id)
        .execute()
    )
    if not result.data or len(result.data) == 0:
        # Auto-create default settings for new patients
        default_data = {
            "patient_id": patient_id,
            "family_email": None,
            "doctor_email": None,
            "notifications_enabled": True,
            "missed_dose_alert_enabled": True,
            "weekly_report_enabled": True,
            "updated_at": datetime.utcnow().isoformat(),
        }
        created = supabase.table("patient_settings").insert(default_data).execute()
        if not created.data:
            raise HTTPException(status_code=500, detail="Failed to create default settings")
        return created.data[0]
    return result.data[0]


@router.put("/{patient_id}", response_model=SettingsResponse)
async def upsert_settings(patient_id: str, payload: SettingsUpdate):
    """
    Create or update patient settings (upsert).
    Uses patient_id uniqueness constraint to merge on conflict.
    """
    supabase = get_supabase()
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    data["patient_id"] = patient_id
    data["updated_at"] = datetime.utcnow().isoformat()

    result = (
        supabase.table("patient_settings")
        .upsert(data, on_conflict="patient_id")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update settings")
    return result.data[0]
