"""
Tool: get_client_full_profile
Fetches everything about a client in one call:
  - CRM profile (Zoho): name, risk profile, AUM, investment objectives, last meeting date
  - Portfolio (PostgreSQL holdings + snapshots): allocation, sectors, geography, top holdings, risk metrics
  - Insurance policies (PostgreSQL policies): all active policies with coverage details
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine
from agent_tools.zoho_client import find_contact_by_client_id
from agent_tools.query_portfolio import query_portfolio
from agent_tools.query_policies import query_policies


def get_client_full_profile(client_id: str) -> str:
    # 1. CRM profile from Zoho
    crm = find_contact_by_client_id(client_id) or {}

    # 2. Portfolio data from PostgreSQL
    portfolio = json.loads(query_portfolio(client_id))

    # 3. All policies from PostgreSQL
    policies = json.loads(query_policies(client_id=client_id))

    if "error" in portfolio and not crm:
        return json.dumps({"error": f"No data found for client {client_id}"})

    return json.dumps({
        "client_id":   client_id,
        "crm_profile": {
            "full_name":              crm.get("full_name"),
            "risk_profile":           crm.get("risk_profile"),
            "aum":                    crm.get("aum"),
            "investment_objectives":  crm.get("investment_objectives") if "investment_objectives" in crm else None,
            "last_meeting_date":      crm.get("last_meeting_date") if "last_meeting_date" in crm else None,
        },
        "portfolio":   portfolio,
        "policies":    policies,
    }, default=str)
