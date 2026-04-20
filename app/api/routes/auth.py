"""
Auth Routes — Email OTP authentication via Supabase (no SMS provider needed).
Supabase sends a 6-digit OTP to the email for free.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerify(BaseModel):
    email: EmailStr
    token: str  # 8-digit code sent to email (expires in 3600s per Supabase settings)


@router.post("/send-otp")
async def send_otp(payload: OTPRequest):
    """Send an 8-digit OTP to the patient's email via Supabase Auth (free, no SMS needed). Expires in 1 hour."""
    supabase = get_supabase()
    try:
        supabase.auth.sign_in_with_otp({"email": payload.email})
        return {"message": "OTP sent to email successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-otp")
async def verify_otp(payload: OTPVerify):
    """Verify the 8-digit email OTP and return a valid access token."""
    supabase = get_supabase()
    try:
        result = supabase.auth.verify_otp({
            "email": payload.email,
            "token": payload.token,
            "type": "email",
        })
        return {
            "access_token": result.session.access_token,
            "user_id": result.user.id,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
