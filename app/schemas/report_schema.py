"""
Schemas for Reports endpoints — daily summaries & weekly doctor reports.
"""
from pydantic import BaseModel
from typing import List, Optional


# ── Requests ──────────────────────────────────────────────────────────────────


class WeeklyReportRequest(BaseModel):
    patient_id: str
    weekly_events: List[str] = []
    doctor_email: Optional[str] = None  # If provided, report will also be emailed
    language: str = "ar"               # "ar" = Arabic, "en" = English


# ── Responses ─────────────────────────────────────────────────────────────────


class WeeklyReportResponse(BaseModel):
    patient_id: str
    report: str
    emailed: bool = False
    agent_used: str = "reporting_agent"
