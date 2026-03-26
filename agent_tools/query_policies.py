"""
Tool: query_policies
Returns insurance policies with renewals within N days.
Can be scoped to a single client or run across the full book.
"""
import json
from sqlalchemy import text
from ingestion.db_client import engine


def query_policies(client_id: str = None, days_ahead: int = 30) -> str:
    conditions = [
        "p.status = 'active'",
        "p.renewal_date BETWEEN CURRENT_DATE AND CURRENT_DATE + :days_ahead",
    ]
    params: dict = {"days_ahead": days_ahead}

    if client_id:
        conditions.append("p.client_id = :client_id")
        params["client_id"] = client_id

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT
            p.policy_id,
            p.client_id,
            c.full_name,
            c.risk_profile,
            p.policy_type,
            p.insurer,
            p.coverage_amount,
            p.premium,
            p.renewal_date,
            (p.renewal_date - CURRENT_DATE) AS days_until_renewal
        FROM policies p
        JOIN clients c ON c.client_id = p.client_id
        WHERE {where_clause}
        ORDER BY p.renewal_date ASC
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return json.dumps([dict(r) for r in rows], default=str)
