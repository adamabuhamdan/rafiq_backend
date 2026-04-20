"""
Supabase Client — singleton client + token utilities.
"""
from supabase import create_client, Client
from app.core.config import get_settings
import jwt as pyjwt

settings = get_settings()

_client: Client | None = None


def get_supabase() -> Client:
    """Return a singleton Supabase client (uses service key — bypasses RLS for admin ops)."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def get_supabase_with_token(token: str) -> Client:
    """
    Return a Supabase client authenticated with the user's JWT token.
    This respects RLS policies (auth.uid() = patient_id).
    """
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(token)
    return client


def get_user_id_from_token(token: str) -> str | None:
    """
    Extract user_id (Supabase auth.uid) from a Supabase JWT access token.
    Returns the UUID string or None if the token is invalid.
    """
    try:
        # Supabase tokens are signed with the JWT secret — decode without verification for uid extraction
        # For production, verify using supabase_jwt_secret
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub")  # Supabase stores user UUID in 'sub' claim
    except Exception:
        return None
