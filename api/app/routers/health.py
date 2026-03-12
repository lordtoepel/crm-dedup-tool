"""Health check endpoint for Railway/deployment verification."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check for deployment platforms."""
    return {"status": "healthy"}
