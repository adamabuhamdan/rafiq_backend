"""
Background Scheduler for automatic missed dose detection and email alerts.
"""
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.supabase_client import get_supabase
from app.api.routes.pharmacy import check_missed_doses_for_patient

scheduler = BackgroundScheduler()

async def check_all_patients_missed_doses():
    """
    Fetch all patients and check missed doses for each.
    Called periodically by the scheduler.
    """
    supabase = get_supabase()
    try:
        patients = supabase.table("patients").select("id").execute()
        if not patients.data:
            return

        for patient in patients.data:
            patient_id = patient["id"]
            await check_missed_doses_for_patient(patient_id)
            print(f"[SCHEDULER] Checked patient: {patient_id}")
    except Exception as e:
        print(f"[SCHEDULER] Error checking missed doses: {e}")

# 🛠️ التعديل السحري هنا: دالة متزامنة تقوم بتشغيل الكود غير المتزامن
def run_check_sync():
    asyncio.run(check_all_patients_missed_doses())

def start_scheduler():
    """
    Start the background scheduler when the FastAPI app starts.
    """
    scheduler.add_job(
        run_check_sync,  
        'interval',
        minutes=15, 
        id='missed_doses_checker',
        replace_existing=True
    )
    scheduler.start()
    print("[SCHEDULER] Started. Will check missed doses every 15 minutes.")