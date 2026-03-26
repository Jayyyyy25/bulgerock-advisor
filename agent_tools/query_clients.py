"""
Tool: query_clients
Retrieves client profiles from Zoho CRM with dynamic filtering.
"""
import json
from agent_tools.zoho_client import search_contacts


def query_clients(
    name_contains: str = None,
    advisor_id: str = None,
    risk_profile: str = None,
    min_aum: float = None,
    max_aum: float = None,
    limit: int = 10,
) -> str:
    clients = search_contacts(
        name_contains=name_contains,
        risk_profile=risk_profile,
        advisor_id=advisor_id,
        min_aum=min_aum,
        max_aum=max_aum,
        limit=limit,
    )

    if not clients:
        return json.dumps({"message": "No clients found matching the given filters."})

    return json.dumps(clients, default=str)
