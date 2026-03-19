"""Salesforce OAuth and API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.salesforce import SalesforceService

router = APIRouter()


class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str
    user_id: str


class ConnectionStatusResponse(BaseModel):
    connected: bool
    org_id: Optional[str] = None
    instance_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/exchange-token")
async def exchange_token(request: TokenExchangeRequest):
    """Exchange OAuth code for access token and save connection."""
    service = SalesforceService()

    try:
        # Exchange code for tokens
        tokens = await service.exchange_code_for_tokens(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )

        # Get org ID
        org_id = await service.get_org_id(tokens.access_token, tokens.instance_url)

        # Save connection
        connection = await service.save_connection(
            user_id=request.user_id,
            tokens=tokens,
            org_id=org_id,
        )

        return {
            "success": True,
            "org_id": org_id,
            "instance_url": tokens.instance_url,
            "connection_id": connection["id"] if connection else None,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connection-status/{user_id}")
async def connection_status(user_id: str) -> ConnectionStatusResponse:
    """Check if user has valid Salesforce connection."""
    service = SalesforceService()

    try:
        connection = await service.get_connection(user_id)

        if connection:
            return ConnectionStatusResponse(
                connected=True,
                org_id=connection.org_id,
                instance_url=connection.instance_url,
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
    """Disconnect Salesforce for a user."""
    service = SalesforceService()

    try:
        deleted = await service.delete_connection(user_id)
        return {"success": deleted}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
