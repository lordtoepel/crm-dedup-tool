"""HubSpot API service for OAuth and CRM operations."""
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel

from app.config import get_settings
from app.services.encryption import encrypt_token, decrypt_token
from app.services.supabase_client import get_supabase


class HubSpotTokens(BaseModel):
    """HubSpot OAuth tokens."""
    access_token: str
    refresh_token: str
    expires_in: int  # seconds


class HubSpotConnection(BaseModel):
    """Stored HubSpot connection."""
    id: str
    user_id: str
    portal_id: str
    access_token: str  # Decrypted
    refresh_token: str  # Decrypted
    expires_at: datetime


class HubSpotService:
    """Service for HubSpot OAuth and API operations."""

    BASE_URL = "https://api.hubapi.com"
    OAUTH_URL = "https://api.hubapi.com/oauth/v1/token"

    def __init__(self):
        self.settings = get_settings()
        self.supabase = get_supabase()

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str
    ) -> HubSpotTokens:
        """Exchange OAuth authorization code for access tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.settings.hubspot_client_id,
                    "client_secret": self.settings.hubspot_client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")

            data = response.json()
            return HubSpotTokens(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_in=data["expires_in"],
            )

    async def refresh_tokens(self, refresh_token: str) -> HubSpotTokens:
        """Refresh expired access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.settings.hubspot_client_id,
                    "client_secret": self.settings.hubspot_client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise Exception(f"Token refresh failed: {response.text}")

            data = response.json()
            return HubSpotTokens(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_in=data["expires_in"],
            )

    async def get_portal_id(self, access_token: str) -> str:
        """Get the HubSpot portal ID for the authenticated account."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/oauth/v1/access-tokens/{access_token}",
            )

            if response.status_code != 200:
                raise Exception(f"Failed to get portal info: {response.text}")

            data = response.json()
            return str(data["hub_id"])

    async def save_connection(
        self,
        user_id: str,
        tokens: HubSpotTokens,
        portal_id: str
    ) -> dict:
        """Save or update HubSpot connection for a user."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)

        # Encrypt tokens before storing
        encrypted_access = encrypt_token(tokens.access_token)
        encrypted_refresh = encrypt_token(tokens.refresh_token)

        # Upsert connection
        result = self.supabase.table("crm_connections").upsert(
            {
                "user_id": user_id,
                "crm_type": "hubspot",
                "access_token_encrypted": encrypted_access,
                "refresh_token_encrypted": encrypted_refresh,
                "portal_id": portal_id,
                "expires_at": expires_at.isoformat(),
            },
            on_conflict="user_id,crm_type",
        ).execute()

        return result.data[0] if result.data else None

    async def get_connection(self, user_id: str) -> Optional[HubSpotConnection]:
        """Get HubSpot connection for a user, refreshing if needed."""
        result = self.supabase.table("crm_connections").select("*").eq(
            "user_id", user_id
        ).eq("crm_type", "hubspot").single().execute()

        if not result.data:
            return None

        conn = result.data
        expires_at = datetime.fromisoformat(conn["expires_at"].replace("Z", "+00:00"))

        # Check if token needs refresh (5 min buffer)
        if expires_at < datetime.now(timezone.utc) + timedelta(minutes=5):
            # Decrypt and refresh
            refresh_token = decrypt_token(conn["refresh_token_encrypted"])
            new_tokens = await self.refresh_tokens(refresh_token)
            await self.save_connection(user_id, new_tokens, conn["portal_id"])

            return HubSpotConnection(
                id=conn["id"],
                user_id=conn["user_id"],
                portal_id=conn["portal_id"],
                access_token=new_tokens.access_token,
                refresh_token=new_tokens.refresh_token,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=new_tokens.expires_in),
            )

        # Decrypt and return existing
        return HubSpotConnection(
            id=conn["id"],
            user_id=conn["user_id"],
            portal_id=conn["portal_id"],
            access_token=decrypt_token(conn["access_token_encrypted"]),
            refresh_token=decrypt_token(conn["refresh_token_encrypted"]),
            expires_at=expires_at,
        )

    async def delete_connection(self, user_id: str) -> bool:
        """Delete HubSpot connection for a user."""
        result = self.supabase.table("crm_connections").delete().eq(
            "user_id", user_id
        ).eq("crm_type", "hubspot").execute()

        return len(result.data) > 0 if result.data else False
