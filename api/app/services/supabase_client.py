"""Supabase client for database operations."""
from supabase import create_client, Client
from app.config import get_settings


def get_supabase() -> Client:
    """Get Supabase client with service role key."""
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )
