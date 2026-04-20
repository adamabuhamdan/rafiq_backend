from pydantic import BaseModel
from typing import Optional
from datetime import date
from uuid import UUID

class DailyReportCreate(BaseModel):
    patient_id: UUID
    meds_taken: Optional[bool] = False
    meds_on_time: Optional[bool] = False
    sugar_morning: Optional[float] = None
    sugar_noon: Optional[float] = None
    sugar_evening: Optional[float] = None
    bp_morning_systolic: Optional[float] = None
    bp_morning_diastolic: Optional[float] = None
    bp_evening_systolic: Optional[float] = None
    bp_evening_diastolic: Optional[float] = None
    notes: Optional[str] = None
    # report_date and id are handled by DB defaults, but we can pass language for the response
    language: Optional[str] = "ar"

class DailyReportResponse(BaseModel):
    patient_id: UUID
    report_date: date
    advice: str  # Response from the multi-agent orchestrator

class CronWeeklyResponse(BaseModel):
    status: str
    reports_sent: int
