"""
Tool: query_policies
Returns insurance policies with renewals within N days.
Policy data lives in the DB; client details are enriched from Zoho CRM.
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine
from agent_tools.zoho_client import get_contacts_by_client_ids


def query_policies(client_id: str = None, days_ahead: int = None) -> str:
    conditions = ["status = 'active'"]
    params: dict = {}

    if days_ahead is not None:
        conditions.append("renewal_date BETWEEN CURRENT_DATE AND CURRENT_DATE + :days_ahead")
        params["days_ahead"] = days_ahead

    if client_id:
        conditions.append("client_id = :client_id")
        params["client_id"] = client_id

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT
            policy_id,
            client_id,
            policy_type,
            insurer,
            coverage_amount,
            premium,
            renewal_date,
            (renewal_date - CURRENT_DATE) AS days_until_renewal
        FROM policies
        WHERE {where_clause}
        ORDER BY renewal_date ASC
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    policies = [dict(r) for r in rows]

    if not policies:
        return json.dumps([])

    # Enrich with client details from Zoho CRM
    client_ids = list({p["client_id"] for p in policies})
    clients_by_id = get_contacts_by_client_ids(client_ids)

    for policy in policies:
        client = clients_by_id.get(policy["client_id"], {})
        policy["full_name"]    = client.get("full_name")
        policy["risk_profile"] = client.get("risk_profile")

    return json.dumps(policies, default=str)
