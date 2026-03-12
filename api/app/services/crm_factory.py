"""Factory for creating CRM-specific services."""
from typing import Tuple, Any

from app.services.supabase_client import get_supabase


async def get_crm_services(user_id: str, connection_id: str) -> Tuple[Any, Any, Any]:
    """
    Get the appropriate CRM services based on connection type.

    Returns:
        Tuple of (connection, contacts_service, merge_service)
    """
    supabase = get_supabase()

    # Get connection to determine CRM type
    conn_result = supabase.table("crm_connections").select("*").eq(
        "id", connection_id
    ).single().execute()

    if not conn_result.data:
        raise Exception("Connection not found")

    crm_type = conn_result.data["crm_type"]

    if crm_type == "hubspot":
        from app.services.hubspot import HubSpotService
        from app.services.hubspot_contacts import HubSpotContactsService
        from app.services.hubspot_merge import HubSpotMergeService

        service = HubSpotService()
        connection = await service.get_connection(user_id)
        if not connection:
            raise Exception("HubSpot connection not found or expired")

        contacts_service = HubSpotContactsService(connection)
        merge_service = HubSpotMergeService(connection)

        return connection, contacts_service, merge_service

    elif crm_type == "salesforce":
        from app.services.salesforce import SalesforceService
        from app.services.salesforce_contacts import SalesforceContactsService
        from app.services.salesforce_merge import SalesforceMergeService

        service = SalesforceService()
        connection = await service.get_connection(user_id)
        if not connection:
            raise Exception("Salesforce connection not found or expired")

        contacts_service = SalesforceContactsService(connection)
        merge_service = SalesforceMergeService(connection)

        return connection, contacts_service, merge_service

    else:
        raise Exception(f"Unsupported CRM type: {crm_type}")
