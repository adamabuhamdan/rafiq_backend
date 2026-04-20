"""
Patient Settings Schemas — maps to the `patient_settings` table in Supabase.
One-to-one with patients (patient_id is UNIQUE).
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class SettingsResponse(BaseModel):
    id: str
    patient_id: str
    family_email: Optional[str] = None
    doctor_email: Optional[str] = None
    notifications_enabled: bool = True
    missed_dose_alert_enabled: bool = True
    weekly_report_enabled: bool = True
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    family_email: Optional[EmailStr] = None
    doctor_email: Optional[EmailStr] = None
    notifications_enabled: Optional[bool] = None
    missed_dose_alert_enabled: Optional[bool] = None
    weekly_report_enabled: Optional[bool] = None
