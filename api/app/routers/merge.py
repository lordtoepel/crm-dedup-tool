"""Merge endpoints for executing duplicate merges."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class MergeRequest(BaseModel):
    scan_id: str
    user_id: str
    set_ids: Optional[List[str]] = None  # If None, merge all non-excluded


@router.post("/execute")
async def execute_merge(request: MergeRequest):
    """Start merge execution for selected duplicate sets."""
    # TODO: Implement merge execution
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{merge_id}/status")
async def get_merge_status(merge_id: str):
    """Get current merge progress and status."""
    # TODO: Implement status check
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{merge_id}/pause")
async def pause_merge(merge_id: str):
    """Pause an in-progress merge."""
    # TODO: Implement pause
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{merge_id}/resume")
async def resume_merge(merge_id: str):
    """Resume a paused merge."""
    # TODO: Implement resume
    raise HTTPException(status_code=501, detail="Not implemented")
