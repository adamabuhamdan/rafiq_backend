"""
API Router — Aggregates all route modules
"""
from fastapi import APIRouter
from app.api.routes import auth, patient, chat, pharmacy, reports, settings  # أزلت 'med'

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(patient.router)
router.include_router(chat.router)
router.include_router(pharmacy.router)
router.include_router(reports.router)
router.include_router(settings.router)