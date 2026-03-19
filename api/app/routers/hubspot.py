"""HubSpot OAuth and API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.hubspot import HubSpotService

router = APIRouter()


class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str
    user_id: str


class ConnectionStatusResponse(BaseModel):
    connected: bool
    portal_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/exchange-token")
async def exchange_token(request: TokenExchangeRequest):
    """Exchange OAuth code for access token and save connection."""
    service = HubSpotService()

    try:
        # Exchange code for tokens
        tokens = await service.exchange_code_for_tokens(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )

        # Get portal ID
        portal_id = await service.get_portal_id(tokens.access_token)

        # Save connection
        connection = await service.save_connection(
            user_id=request.user_id,
            tokens=tokens,
            portal_id=portal_id,
        )

        return {
            "success": True,
            "portal_id": portal_id,
            "connection_id": connection["id"] if connection else None,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connection-status/{user_id}")
async def connection_status(user_id: str) -> ConnectionStatusResponse:
    """Check if user has valid HubSpot connection."""
    service = HubSpotService()

    try:
        connection = await service.get_connection(user_id)

        if connection:
            return ConnectionStatusResponse(
                connected=True,
                portal_id=connection.portal_id,
            )
        else:
            return ConnectionStatusResponse(
                connected=False,
            )

    except Exception as e:
        return ConnectionStatusResponse(
            connected=False,
            error=str(e),
        )


@router.delete("/disconnect/{user_id}")
async def disconnect(user_id: str):
    """Disconnect HubSpot for a user."""
    service = HubSpotService()

    try:
        deleted = await service.delete_connection(user_id)
        return {"success": deleted}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
