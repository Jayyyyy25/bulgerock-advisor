from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from ..dependencies import get_db
from ..schemas.policy import PolicyResponse

router = APIRouter()


@router.get("/", response_model=List[PolicyResponse])
def list_policies(
    client_id: Optional[str] = Query(None),
    days_ahead: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    conditions = [
        "p.status = 'active'",
        "p.renewal_date BETWEEN CURRENT_DATE AND CURRENT_DATE + :days_ahead",
    ]
    params: dict = {"days_ahead": days_ahead}

    if client_id:
        conditions.append("p.client_id = :client_id")
        params["client_id"] = client_id

    sql = f"""
        SELECT
            p.policy_id, p.client_id, c.full_name, p.policy_type,
            p.insurer, p.coverage_amount, p.premium, p.renewal_date, p.status,
            (p.renewal_date - CURRENT_DATE) AS days_until_renewal
        FROM policies p
        JOIN clients c ON c.client_id = p.client_id
        WHERE {" AND ".join(conditions)}
        ORDER BY p.renewal_date ASC
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]
