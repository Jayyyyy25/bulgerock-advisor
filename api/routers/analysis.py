"""
Portfolio analysis endpoints: stress testing and cross-portfolio screening.
All portfolio data is read from PostgreSQL — no JSON files.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from ingestion.db_client import engine
from portfolio.impact_analysis import MarketImpactAnalyzer

router = APIRouter()

_impact_analyzer: Optional[MarketImpactAnalyzer] = None


def get_impact_analyzer() -> MarketImpactAnalyzer:
    global _impact_analyzer
    if _impact_analyzer is None:
        _impact_analyzer = MarketImpactAnalyzer()
    return _impact_analyzer


class StressTestRequest(BaseModel):
    client_id:   str    # portfolio_name
    market_event: str


class CrossPortfolioRequest(BaseModel):
    dimension: str          # "asset_class" | "sector" | "geography"
    threshold: float
    operator:  str = ">"
    category:  Optional[str] = None


def _load_latest_snapshot(portfolio_name: str) -> dict:
    """Fetch the most recent snapshot for a portfolio from the DB."""
    sql = text("""
        SELECT portfolio_name, zoho_client_id, source_file, as_of_date,
               total_value, asset_allocation, sector_concentration,
               geographic_exposure, top_10_holdings, risk_metrics
        FROM portfolio_snapshots
        WHERE portfolio_name = :portfolio_name
        ORDER BY as_of_date DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"portfolio_name": portfolio_name}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_name}' not found.")

    return {
        "client_id":           row["portfolio_name"],
        "zoho_client_id":      row["zoho_client_id"],
        "source_file":         row["source_file"],
        "as_of_date":          str(row["as_of_date"]),
        "total_value":         float(row["total_value"] or 0),
        "asset_allocation":    row["asset_allocation"] or {},
        "sector_concentration": row["sector_concentration"] or {},
        "geographic_exposure": row["geographic_exposure"] or {},
        "top_10_holdings":     row["top_10_holdings"] or [],
        "risk_metrics":        row["risk_metrics"] or {},
    }


@router.get("/portfolios")
def list_portfolios():
    """List all portfolios — latest snapshot per portfolio_name."""
    sql = text("""
        SELECT DISTINCT ON (portfolio_name)
            portfolio_name, zoho_client_id, source_file, as_of_date,
            total_value, asset_allocation, risk_metrics
        FROM portfolio_snapshots
        ORDER BY portfolio_name, as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    portfolios = [
        {
            "client_id":        row["portfolio_name"],
            "zoho_client_id":   row["zoho_client_id"],
            "source_file":      row["source_file"],
            "as_of_date":       str(row["as_of_date"]),
            "total_value":      float(row["total_value"] or 0),
            "asset_allocation": row["asset_allocation"] or {},
            "risk_metrics":     row["risk_metrics"] or {},
        }
        for row in rows
    ]
    return {"portfolios": portfolios, "count": len(portfolios)}


@router.get("/portfolios/{portfolio_name}/history")
def portfolio_history(portfolio_name: str):
    """List all snapshots (all periods) for a given portfolio."""
    sql = text("""
        SELECT as_of_date, total_value, source_file, ingested_at
        FROM portfolio_snapshots
        WHERE portfolio_name = :portfolio_name
        ORDER BY as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"portfolio_name": portfolio_name}).mappings().all()

    return {
        "portfolio_name": portfolio_name,
        "snapshots": [
            {
                "as_of_date":   str(r["as_of_date"]),
                "total_value":  float(r["total_value"] or 0),
                "source_file":  r["source_file"],
                "ingested_at":  str(r["ingested_at"]),
            }
            for r in rows
        ],
    }


@router.get("/portfolios/{portfolio_name}")
def get_portfolio(portfolio_name: str):
    """Return the latest snapshot for a portfolio."""
    return _load_latest_snapshot(portfolio_name)


@router.post("/stress-test")
def stress_test(request: StressTestRequest):
    """Run a Claude-powered market event stress test on a portfolio."""
    client_data = _load_latest_snapshot(request.client_id)
    result = get_impact_analyzer().assess_impact(client_data, request.market_event)
    return {"client_id": request.client_id, "market_event": request.market_event, "analysis": result}


@router.post("/cross-portfolio")
def cross_portfolio(request: CrossPortfolioRequest):
    """Screen all portfolios by exposure dimension — pure SQL + pandas, no AI."""
    valid_dimensions = {"asset_class", "sector", "geography"}
    valid_operators  = {">", "<", ">=", "<=", "=="}

    if request.dimension not in valid_dimensions:
        raise HTTPException(status_code=400, detail=f"dimension must be one of {sorted(valid_dimensions)}")
    if request.operator not in valid_operators:
        raise HTTPException(status_code=400, detail=f"operator must be one of {sorted(valid_operators)}")

    # Load latest snapshot per portfolio
    sql = text("""
        SELECT DISTINCT ON (portfolio_name)
            portfolio_name, total_value, asset_allocation, sector_concentration, geographic_exposure
        FROM portfolio_snapshots
        ORDER BY portfolio_name, as_of_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    dim_map = {
        "asset_class": "asset_allocation",
        "sector":      "sector_concentration",
        "geography":   "geographic_exposure",
    }
    field = dim_map[request.dimension]
    ops = {">": lambda a, b: a > b, "<": lambda a, b: a < b,
           ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
           "==": lambda a, b: a == b}
    op_fn = ops[request.operator]

    results = []
    for row in rows:
        data = row[field] or {}
        matches = []
        for category, pct in data.items():
            if request.category and category.upper() != request.category.upper():
                continue
            if op_fn(float(pct), request.threshold):
                matches.append({"category": category, "percentage": float(pct)})

        if matches:
            matches.sort(key=lambda x: x["percentage"], reverse=True)
            results.append({
                "client_id":   row["portfolio_name"],
                "total_value": float(row["total_value"] or 0),
                "matches":     matches,
            })

    results.sort(key=lambda x: max(m["percentage"] for m in x["matches"]), reverse=True)
    return {"query": request.model_dump(), "results": results, "count": len(results)}
