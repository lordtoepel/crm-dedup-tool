"""Supabase client for database operations."""
from functools import lru_cache
from postgrest import SyncPostgrestClient
from app.config import get_settings


class SupabaseClient:
    """Lightweight Supabase client using only PostgREST (no gotrue auth).

    The backend uses the service role key which bypasses RLS,
    so we don't need the gotrue auth client that causes the
    proxy kwarg incompatibility.
    """

    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        rest_url = f"{url}/rest/v1"
        self._postgrest = SyncPostgrestClient(
            rest_url,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
            },
        )

    def table(self, table_name: str):
        return self._postgrest.from_(table_name)


@lru_cache()
def get_supabase() -> SupabaseClient:
    """Get cached Supabase client with service role key."""
    settings = get_settings()
    return SupabaseClient(
        settings.supabase_url,
        settings.supabase_service_key,
    )
