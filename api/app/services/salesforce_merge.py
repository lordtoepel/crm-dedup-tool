"""Salesforce merge operations service."""
import httpx
import asyncio
from typing import Optional

from app.services.salesforce import SalesforceConnection


class SalesforceMergeService:
    """
    Service for merging contacts in Salesforce.

    Salesforce uses the Merge API endpoint:
    POST /services/data/vXX.0/sobjects/Contact/merge/

    Note: Salesforce requires specific permissions for merge operations.
    """

    RATE_LIMIT_DELAY = 0.05  # Salesforce allows more requests

    def __init__(self, connection: SalesforceConnection):
        self.connection = connection
        self.access_token = connection.access_token
        self.instance_url = connection.instance_url

    async def merge_contacts(
        self,
        master_id: str,
        merge_ids: list[str],
    ) -> dict:
        """
        Merge contacts using Salesforce's Merge API.

        The master record is kept, and merge records are deleted.
        Related records are re-parented to the master.

        Args:
            master_id: Salesforce ID of the contact to keep (master)
            merge_ids: List of Salesforce IDs to merge into master (max 2)

        Returns:
            Dict with merge result
        """
        # Salesforce merge endpoint only supports merging up to 2 records at a time
        # For more, we need to do multiple merge calls

        async with httpx.AsyncClient() as client:
            for merge_id in merge_ids[:2]:  # Salesforce limit
                response = await client.post(
                    f"{self.instance_url}/services/data/v59.0/sobjects/Contact/{master_id}/merge",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "masterRecord": {"Id": master_id},
                        "recordToMergeIds": [merge_id],
                    },
                )

                if response.status_code not in [200, 201, 204]:
                    return {
                        "success": False,
                        "error": f"Salesforce merge failed: {response.status_code} - {response.text}",
                    }

                await asyncio.sleep(self.RATE_LIMIT_DELAY)

        # If more than 2 merge_ids, recursively merge remaining
        if len(merge_ids) > 2:
            remaining = merge_ids[2:]
            return await self.merge_contacts(master_id, remaining)

        return {"success": True}

    async def update_contact(
        self,
        contact_id: str,
        properties: dict,
    ) -> dict:
        """
        Update a contact's fields.

        Args:
            contact_id: Salesforce ID of the contact
            properties: Dict of field name -> value to update

        Returns:
            Dict with update result
        """
        # Map common field names to Salesforce API names
        field_mapping = {
            "phone": "Phone",
            "email": "Email",
            "firstname": "FirstName",
            "lastname": "LastName",
            "company": "AccountId",  # Note: This needs special handling
            "jobtitle": "Title",
        }

        # Transform properties to Salesforce field names
        sf_properties = {}
        for key, value in properties.items():
            sf_key = field_mapping.get(key.lower(), key)
            if sf_key != "AccountId" and value:  # Skip company for now
                sf_properties[sf_key] = value

        if not sf_properties:
            return {"success": True}  # Nothing to update

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.instance_url}/services/data/v59.0/sobjects/Contact/{contact_id}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json=sf_properties,
            )

            if response.status_code in [200, 204]:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"Salesforce update failed: {response.status_code} - {response.text}",
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
        2. Merge losers into winner

        Args:
            winner_id: Salesforce ID of the winner contact
            loser_ids: List of Salesforce IDs to merge into winner
            blended_properties: Optional dict of properties to update on winner

        Returns:
            Dict with overall merge result
        """
        errors = []

        # Step 1: Update winner with blended fields
        if blended_properties:
            update_result = await self.update_contact(winner_id, blended_properties)
            if not update_result["success"]:
                errors.append(f"Failed to update winner: {update_result['error']}")

        # Step 2: Merge losers
        merge_result = await self.merge_contacts(winner_id, loser_ids)
        if not merge_result["success"]:
            errors.append(merge_result["error"])

        return {
            "success": len(errors) == 0,
            "merged_count": len(loser_ids) if len(errors) == 0 else 0,
            "errors": errors,
        }
