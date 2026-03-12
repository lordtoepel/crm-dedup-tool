"""HubSpot OAuth and API endpoints."""
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/exchange-token")
async def exchange_token(code: str):
    """Exchange OAuth code for access token."""
    # TODO: Implement OAuth token exchange
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/connection-status")
async def connection_status(user_id: str):
    """Check if user has valid HubSpot connection."""
    # TODO: Implement connection check
    raise HTTPException(status_code=501, detail="Not implemented")
