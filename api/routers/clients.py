from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from ..dependencies import get_db
from ..schemas.client import ClientSummary

router = APIRouter()


@router.get("/", response_model=List[ClientSummary])
def list_clients(
    name: Optional[str] = Query(None, description="Partial name filter"),
    risk_profile: Optional[str] = Query(None),
    advisor_id: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {"limit": limit}

    if name:
        conditions.append("LOWER(full_name) LIKE :name_pattern")
        params["name_pattern"] = f"%{name.lower()}%"
    if risk_profile:
        conditions.append("risk_profile = :risk_profile")
        params["risk_profile"] = risk_profile.lower()
    if advisor_id:
        conditions.append("advisor_id = :advisor_id")
        params["advisor_id"] = advisor_id

    sql = f"""
        SELECT client_id, full_name, email, phone, risk_profile, advisor_id, aum, updated_at
        FROM clients
        WHERE {" AND ".join(conditions)}
        ORDER BY aum DESC NULLS LAST
        LIMIT :limit
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/{client_id}", response_model=ClientSummary)
def get_client(client_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT * FROM clients WHERE client_id = :id"),
        {"id": client_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found")
    return dict(row)
