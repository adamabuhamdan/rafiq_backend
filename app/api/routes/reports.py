"""
Reports Routes — Daily patient summaries & weekly doctor reports.
Calls ReportingAgent directly (no orchestrator needed).
Emails are sent via notify_service, which reads contact info from patient_settings.
"""
from fastapi import APIRouter, HTTPException
from app.schemas.report_schema import (
    WeeklyReportRequest,
    WeeklyReportResponse,
)   

from app.agents.functional.reporting_agent import ReportingAgent
from app.services.notify_service import send_weekly_doctor_summary
from app.db.supabase_client import get_supabase
from app.schemas.daily_report import DailyReportCreate, DailyReportResponse, CronWeeklyResponse
from app.agents.orchestrator import evaluate_daily_report
from datetime import datetime, timedelta
import logging
router = APIRouter(prefix="/reports", tags=["Reports - التقارير"])

reporting_agent = ReportingAgent()



@router.post("/daily-report", response_model=DailyReportResponse)
async def submit_daily_report(payload: DailyReportCreate):
    """
    Submits a daily structural report (meds, sugar, BP, notes).
    Upserts it into the public.daily_reports table, then passes the 
    report to Orchestrator to give multi-agent feedback.
    """
    supabase = get_supabase()
    
    # 1) Format data
    data = payload.model_dump(exclude={"language"}, exclude_unset=False, exclude_none=True)
    # Ensure patient_id is stringified for JSON/Supabase
    data["patient_id"] = str(data["patient_id"])
    
    # 2) Get advice from orchestrator
    advice = await evaluate_daily_report(str(payload.patient_id), data, payload.language)
    data["ai_advice"] = advice
    
    # 3) Perform upsert using Supabase
    db_result = (
        supabase.table("daily_reports")
        .upsert(data, on_conflict="patient_id, report_date")
        .execute()
    )
    
    if not db_result.data:
        raise HTTPException(status_code=500, detail="Failed to save daily report.")
        
    saved_report = db_result.data[0]
    report_date = saved_report.get("report_date", datetime.now().date().isoformat())
    
    return DailyReportResponse(
        patient_id=payload.patient_id,
        report_date=report_date,
        advice=advice
    )

@router.get("/today/{patient_id}")
async def get_today_report(patient_id: str):
    """
    Fetches the most recent daily report for the patient. 
    This avoids timezone issues where the DB report_date is still yesterday in UTC.
    """
    supabase = get_supabase()
    result = (
        supabase.table("daily_reports")
        .select("*")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No report found")
    return result.data[0]


@router.post("/weekly-doctor-report", response_model=WeeklyReportResponse)
async def weekly_doctor_report(payload: WeeklyReportRequest):
    """
    Generate a professional weekly medical report for the treating physician.
    Automatically reads doctor_email from patient_settings.
    Optionally accepts a doctor_email override in the request body.
    """
    supabase = get_supabase()
    result = (
        supabase.table("patients")
        .select("*")
        .eq("id", payload.patient_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_data = result.data
    report = await reporting_agent.generate_weekly_doctor_report(
        patient_data, payload.weekly_events, payload.language
    )

    # Send email via notify_service (reads settings from patient_settings table)
    emailed = await send_weekly_doctor_summary(
        patient_id=payload.patient_id,
        patient_name=patient_data.get("full_name", ""),
        summary_html=report,
        override_email=payload.doctor_email,  # Optional override from request
    )

    return WeeklyReportResponse(
        patient_id=payload.patient_id,
        report=report,
        emailed=emailed,
    )


@router.post("/cron/weekly", response_model=CronWeeklyResponse)
async def cron_weekly_reports():
    """
    Cron-like route to grab all patients, generate their weekly reports
    from the last 7 days of daily_reports, and email them to the doctor.
    """
    supabase = get_supabase()
    # 1. Fetch all patients
    patients_res = supabase.table("patients").select("*").execute()
    if not patients_res.data:
        return CronWeeklyResponse(status="No patients found.", reports_sent=0)
        
    patients = patients_res.data
    reports_sent = 0
    
    # Date bounds for last 7 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    for patient in patients:
        patient_id = patient.get("id")
        
        # We only generate if they have recent events
        # We fetch their daily reports
        dr_res = (
            supabase.table("daily_reports")
            .select("*")
            .eq("patient_id", patient_id)
            .gte("report_date", start_date.isoformat())
            .lte("report_date", end_date.isoformat())
            .execute()
        )
        recent_reports = dr_res.data or []
        
        if not recent_reports:
            continue
            
        try:
            # 2. Generate Report using real structures
            report_text = await reporting_agent.generate_weekly_doctor_report_from_db(
                patient, recent_reports, language="ar"
            )
            
            # 3. Send email
            emailed = await send_weekly_doctor_summary(
                patient_id=patient_id,
                patient_name=patient.get("full_name", ""),
                summary_html=report_text,
                override_email=None, 
            )
            if emailed:
                reports_sent += 1
        except Exception as e:
            logging.error(f"Failed to generate weekly cron for {patient_id}: {str(e)}")
            continue

    return CronWeeklyResponse(
        status="Success",
        reports_sent=reports_sent
    )
