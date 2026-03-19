"""HubSpot merge operations service."""
from __future__ import annotations
import httpx
import asyncio
from typing import Optional
from datetime import datetime

from app.services.hubspot import HubSpotConnection


class HubSpotMergeService:
    """
    Service for merging contacts in HubSpot.

    HubSpot provides two approaches:
    1. Native merge endpoint: POST /crm/v3/objects/contacts/merge
       - Automatically re-parents associations
       - Less control over field blending
    2. Manual update + archive:
       - Update winner with blended fields
       - Archive losers
       - More control but more API calls

    We use the native merge endpoint for simplicity and reliability.
    """

    BASE_URL = "https://api.hubapi.com"
    RATE_LIMIT_DELAY = 0.1  # 10 requests per second

    def __init__(self, connection: HubSpotConnection):
        self.connection = connection
        self.access_token = connection.access_token

    async def merge_contacts(
        self,
        winner_id: str,
        loser_id: str,
    ) -> dict:
        """
        Merge two contacts using HubSpot's native merge endpoint.

        The loser contact's associations will be transferred to the winner.
        The loser contact will be archived (soft deleted).

        Args:
            winner_id: HubSpot ID of the contact to keep
            loser_id: HubSpot ID of the contact to merge into winner

        Returns:
            Dict with merge result
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/crm/v3/objects/contacts/merge",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "primaryObjectId": winner_id,
                    "objectIdToMerge": loser_id,
                },
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HubSpot merge failed: {response.status_code} - {response.text}",
                }

    async def update_contact(
        self,
        contact_id: str,
        properties: dict,
    ) -> dict:
        """
        Update a contact's properties.

        Used to apply blended field values to the winner.

        Args:
            contact_id: HubSpot ID of the contact
            properties: Dict of property name -> value to update

        Returns:
            Dict with update result
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json={"properties": properties},
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HubSpot update failed: {response.status_code} - {response.text}",
                }

    async def merge_duplicate_set(
        self,
        winner_id: str,
        loser_ids: list[str],
        blended_properties: Optional[dict] = None,
    ) -> dict:
        """
        Merge a complete duplicate set.

        Steps:
        1. Update winner with blended properties (if provided)
        2. Merge each loser into winner

        Args:
            winner_id: HubSpot ID of the winner contact
            loser_ids: List of HubSpot IDs to merge into winner
            blended_properties: Optional dict of properties to update on winner

        Returns:
            Dict with overall merge result
        """
        errors = []

        # Step 1: Update winner with blended fields (fill gaps)
        if blended_properties:
            update_result = await self.update_contact(winner_id, blended_properties)
            if not update_result["success"]:
                errors.append(f"Failed to update winner: {update_result['error']}")
                # Continue anyway - merge might still work

        # Step 2: Merge each loser
        for loser_id in loser_ids:
            # Rate limiting
            await asyncio.sleep(self.RATE_LIMIT_DELAY)

            merge_result = await self.merge_contacts(winner_id, loser_id)
            if not merge_result["success"]:
                errors.append(f"Failed to merge {loser_id}: {merge_result['error']}")

        return {
            "success": len(errors) == 0,
            "merged_count": len(loser_ids) - len([e for e in errors if "merge" in e]),
            "errors": errors,
        }

    async def batch_merge(
        self,
        merge_operations: list[dict],
        progress_callback: Optional[callable] = None,
    ) -> dict:
        """
        Execute multiple merge operations.

        Args:
            merge_operations: List of {winner_id, loser_ids, blended_properties}
            progress_callback: Optional callback(completed, total, errors)

        Returns:
            Dict with batch results
        """
        total = len(merge_operations)
        completed = 0
        failed = 0
        all_errors = []

        for op in merge_operations:
            result = await self.merge_duplicate_set(
                winner_id=op["winner_id"],
                loser_ids=op["loser_ids"],
                blended_properties=op.get("blended_properties"),
            )

            if result["success"]:
                completed += 1
            else:
                failed += 1
                all_errors.extend(result["errors"])

            # Progress callback
            if progress_callback:
                await progress_callback(completed + failed, total, all_errors)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "errors": all_errors,
        }
