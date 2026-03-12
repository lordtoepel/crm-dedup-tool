"""Merge endpoints for executing duplicate merges."""
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.services.supabase_client import get_supabase
from app.services.hubspot import HubSpotService
from app.services.hubspot_merge import HubSpotMergeService

router = APIRouter()


class MergeRequest(BaseModel):
    scan_id: str
    user_id: str
    set_ids: Optional[List[str]] = None  # If None, merge all non-excluded


async def run_merge(merge_id: str, user_id: str, scan_id: str, set_ids: List[str]):
    """
    Background task to execute merges.
    """
    supabase = get_supabase()

    try:
        # Update status to running
        supabase.table("merges").update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }).eq("id", merge_id).execute()

        # Get HubSpot connection
        hubspot_service = HubSpotService()
        connection = await hubspot_service.get_connection(user_id)

        if not connection:
            raise Exception("HubSpot connection not found")

        # Initialize merge service
        merge_service = HubSpotMergeService(connection)

        # Get duplicate sets to merge
        sets_result = supabase.table("duplicate_sets").select("*").in_(
            "id", set_ids
        ).eq("excluded", False).eq("merged", False).execute()

        duplicate_sets = sets_result.data or []
        total_sets = len(duplicate_sets)

        if total_sets == 0:
            supabase.table("merges").update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
            }).eq("id", merge_id).execute()
            return

        # Prepare merge operations
        merge_operations = []
        for dup_set in duplicate_sets:
            merge_operations.append({
                "set_id": dup_set["id"],
                "winner_id": dup_set["winner_record_id"],
                "loser_ids": dup_set["loser_record_ids"],
                "blended_properties": dup_set.get("merged_preview", {}),
            })

        # Execute merges
        completed = 0
        failed = 0
        error_log = []

        for op in merge_operations:
            # Check if merge was paused
            merge_check = supabase.table("merges").select("status").eq(
                "id", merge_id
            ).single().execute()

            if merge_check.data and merge_check.data["status"] == "paused":
                break

            # Execute merge
            result = await merge_service.merge_duplicate_set(
                winner_id=op["winner_id"],
                loser_ids=op["loser_ids"],
                blended_properties=op.get("blended_properties"),
            )

            if result["success"]:
                completed += 1
                # Mark set as merged
                supabase.table("duplicate_sets").update({
                    "merged": True
                }).eq("id", op["set_id"]).execute()
            else:
                failed += 1
                for err in result["errors"]:
                    error_log.append({"set_id": op["set_id"], "error": err})

            # Update progress
            supabase.table("merges").update({
                "completed_sets": completed,
                "failed_sets": failed,
                "error_log": error_log if error_log else None,
            }).eq("id", merge_id).execute()

        # Mark merge as complete
        final_status = "completed"
        merge_check = supabase.table("merges").select("status").eq(
            "id", merge_id
        ).single().execute()

        if merge_check.data and merge_check.data["status"] == "paused":
            final_status = "paused"

        supabase.table("merges").update({
            "status": final_status,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", merge_id).execute()

    except Exception as e:
        # Mark merge as failed
        supabase.table("merges").update({
            "status": "failed",
            "error_log": [{"set_id": "system", "error": str(e)}],
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", merge_id).execute()
        raise


@router.post("/execute")
async def execute_merge(request: MergeRequest, background_tasks: BackgroundTasks):
    """Start merge execution for selected duplicate sets."""
    supabase = get_supabase()

    # Get duplicate sets (either specified or all non-excluded)
    if request.set_ids:
        sets_result = supabase.table("duplicate_sets").select("id").eq(
            "scan_id", request.scan_id
        ).in_("id", request.set_ids).eq("excluded", False).eq("merged", False).execute()
    else:
        sets_result = supabase.table("duplicate_sets").select("id").eq(
            "scan_id", request.scan_id
        ).eq("excluded", False).eq("merged", False).execute()

    set_ids = [s["id"] for s in (sets_result.data or [])]

    if len(set_ids) == 0:
        raise HTTPException(status_code=400, detail="No duplicate sets to merge")

    # Create merge record
    merge_id = str(uuid.uuid4())
    merge_data = {
        "id": merge_id,
        "scan_id": request.scan_id,
        "user_id": request.user_id,
        "status": "pending",
        "total_sets": len(set_ids),
        "completed_sets": 0,
        "failed_sets": 0,
    }

    supabase.table("merges").insert(merge_data).execute()

    # Start background task
    background_tasks.add_task(
        run_merge,
        merge_id,
        request.user_id,
        request.scan_id,
        set_ids,
    )

    return {"merge_id": merge_id, "status": "pending", "total_sets": len(set_ids)}


@router.get("/{merge_id}/status")
async def get_merge_status(merge_id: str):
    """Get current merge progress and status."""
    supabase = get_supabase()

    result = supabase.table("merges").select("*").eq("id", merge_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Merge not found")

    merge = result.data
    return {
        "id": merge["id"],
        "status": merge["status"],
        "total_sets": merge["total_sets"],
        "completed_sets": merge["completed_sets"],
        "failed_sets": merge["failed_sets"],
        "error_log": merge.get("error_log"),
        "started_at": merge.get("started_at"),
        "completed_at": merge.get("completed_at"),
    }


@router.post("/{merge_id}/pause")
async def pause_merge(merge_id: str):
    """Pause an in-progress merge."""
    supabase = get_supabase()

    # Check current status
    result = supabase.table("merges").select("status").eq("id", merge_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Merge not found")

    if result.data["status"] != "running":
        raise HTTPException(status_code=400, detail="Merge is not running")

    # Set to paused - the background task will check this
    supabase.table("merges").update({
        "status": "paused"
    }).eq("id", merge_id).execute()

    return {"success": True, "status": "paused"}


@router.post("/{merge_id}/resume")
async def resume_merge(merge_id: str, background_tasks: BackgroundTasks):
    """Resume a paused merge."""
    supabase = get_supabase()

    # Get merge details
    result = supabase.table("merges").select("*").eq("id", merge_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Merge not found")

    merge = result.data

    if merge["status"] != "paused":
        raise HTTPException(status_code=400, detail="Merge is not paused")

    # Get remaining sets to merge
    sets_result = supabase.table("duplicate_sets").select("id").eq(
        "scan_id", merge["scan_id"]
    ).eq("excluded", False).eq("merged", False).execute()

    set_ids = [s["id"] for s in (sets_result.data or [])]

    if len(set_ids) == 0:
        # Already complete
        supabase.table("merges").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", merge_id).execute()
        return {"success": True, "status": "completed"}

    # Update total and restart
    supabase.table("merges").update({
        "status": "pending",
        "total_sets": merge["completed_sets"] + merge["failed_sets"] + len(set_ids),
    }).eq("id", merge_id).execute()

    # Start background task
    background_tasks.add_task(
        run_merge,
        merge_id,
        merge["user_id"],
        merge["scan_id"],
        set_ids,
    )

    return {"success": True, "status": "running", "remaining_sets": len(set_ids)}
