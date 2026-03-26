from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from ..dependencies import get_db
from ..schemas.portfolio import PortfolioResponse

router = APIRouter()


@router.get("/{client_id}", response_model=PortfolioResponse)
def get_portfolio(
    client_id: str,
    as_of_date: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to latest"),
    db: Session = Depends(get_db),
):
    if as_of_date:
        date_filter = "h.as_of_date = :as_of_date"
        params = {"client_id": client_id, "as_of_date": as_of_date}
    else:
        date_filter = """
            h.as_of_date = (
                SELECT MAX(as_of_date) FROM holdings WHERE client_id = :client_id
            )
        """
        params = {"client_id": client_id}

    allocation = db.execute(text(f"""
        SELECT
            asset_class,
            SUM(market_value) AS total_value,
            ROUND(100.0 * SUM(market_value) / NULLIF(SUM(SUM(market_value)) OVER (), 0), 2) AS pct
        FROM holdings h
        WHERE h.client_id = :client_id AND {date_filter}
        GROUP BY asset_class
        ORDER BY total_value DESC
    """), params).mappings().all()

    if not allocation:
        raise HTTPException(status_code=404, detail=f"No holdings found for client '{client_id}'")

    top_holdings = db.execute(text(f"""
        SELECT ticker, security_name, isin, asset_class, sector, account_type, quantity, market_value
        FROM holdings h
        WHERE h.client_id = :client_id AND {date_filter}
        ORDER BY market_value DESC
        LIMIT 5
    """), params).mappings().all()

    summary = db.execute(text(f"""
        SELECT SUM(market_value) AS total_aum, MAX(as_of_date) AS as_of_date
        FROM holdings h
        WHERE h.client_id = :client_id AND {date_filter}
    """), params).mappings().first()

    return {
        "client_id": client_id,
        "as_of_date": summary["as_of_date"] if summary else None,
        "total_aum_usd": float(summary["total_aum"]) if summary and summary["total_aum"] else 0.0,
        "allocation": [dict(r) for r in allocation],
        "top_holdings": [dict(r) for r in top_holdings],
    }
