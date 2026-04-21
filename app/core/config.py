from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_diabetes_collection: str = "diabetes_knowledge"
    qdrant_bp_collection: str = "blood_pressure_knowledge"
    qdrant_glands_collection: str = "glands_knowledge"

    # Gemini AI
    gemini_api_key: str

    # Email
    email_provider: str = "resend"          # "resend" | "sendgrid"
    resend_api_key_1: str = ""
    resend_api_key_2: str = ""
    sendgrid_api_key: str = ""
    from_email: str = "noreply@rafiq.app"

    # App
    app_env: str = "development"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
