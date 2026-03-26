"""
Tool: query_clients
Retrieves client profiles from CRM data with dynamic filtering.
All user-provided values use parameterized queries; only structural SQL is f-string composed.
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine


def query_clients(
    name_contains: str = None,
    advisor_id: str = None,
    risk_profile: str = None,
    min_aum: float = None,
    max_aum: float = None,
    limit: int = 10,
) -> str:
    conditions = ["1=1"]
    params: dict = {"limit": min(limit, 50)}  # cap at 50 to prevent runaway queries

    if name_contains:
        conditions.append("LOWER(full_name) LIKE :name_pattern")
        params["name_pattern"] = f"%{name_contains.lower()}%"

    if advisor_id:
        conditions.append("advisor_id = :advisor_id")
        params["advisor_id"] = advisor_id

    if risk_profile:
        conditions.append("risk_profile = :risk_profile")
        params["risk_profile"] = risk_profile.lower()

    if min_aum is not None:
        conditions.append("aum >= :min_aum")
        params["min_aum"] = min_aum

    if max_aum is not None:
        conditions.append("aum <= :max_aum")
        params["max_aum"] = max_aum

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT client_id, full_name, email, phone, risk_profile, advisor_id,
               aum, created_at
        FROM clients
        WHERE {where_clause}
        ORDER BY aum DESC NULLS LAST
        LIMIT :limit
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    result = [dict(r) for r in rows]
    return json.dumps(result, default=str)
