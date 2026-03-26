"""
Portfolio analysis endpoints: stress testing and cross-portfolio screening.
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import PROCESSED_DIR
from portfolio.cross_portfolio import CrossPortfolioAnalyzer
from portfolio.impact_analysis import MarketImpactAnalyzer

router = APIRouter()

_impact_analyzer:  Optional[MarketImpactAnalyzer]  = None
_cross_portfolio:  Optional[CrossPortfolioAnalyzer] = None


def get_impact_analyzer() -> MarketImpactAnalyzer:
    global _impact_analyzer
    if _impact_analyzer is None:
        _impact_analyzer = MarketImpactAnalyzer()
    return _impact_analyzer


def get_cross_portfolio() -> CrossPortfolioAnalyzer:
    global _cross_portfolio
    if _cross_portfolio is None:
        _cross_portfolio = CrossPortfolioAnalyzer()
    return _cross_portfolio


class StressTestRequest(BaseModel):
    client_id: str          # matches the JSON filename stem (e.g. "Stmt1_NorthernTrust_Client")
    market_event: str


class CrossPortfolioRequest(BaseModel):
    dimension: str          # "asset_class" | "sector" | "geography"
    threshold: float
    operator:  str = ">"
    category:  Optional[str] = None


def _load_portfolio(portfolio_id: str) -> dict:
    path = PROCESSED_DIR / f"{portfolio_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_id}' not found.")
    return json.loads(path.read_text())


@router.post("/stress-test")
def stress_test(request: StressTestRequest):
    """Run a Claude-powered market event stress test on a processed portfolio."""
    client_data = _load_portfolio(request.client_id)
    result = get_impact_analyzer().assess_impact(client_data, request.market_event)
    return {"client_id": request.client_id, "market_event": request.market_event, "analysis": result}


@router.post("/cross-portfolio")
def cross_portfolio(request: CrossPortfolioRequest):
    """Screen all processed portfolios by exposure dimension (pure pandas, no AI)."""
    analyzer = get_cross_portfolio()
    analyzer.reload()
    try:
        results = analyzer.query_exposure(
            dimension=request.dimension,
            threshold=request.threshold,
            operator=request.operator,
            category=request.category,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"query": request.model_dump(), "results": results, "count": len(results)}


@router.get("/portfolios")
def list_portfolios():
    """List all processed portfolio JSON files (web UI client list)."""
    portfolios = []
    if PROCESSED_DIR.exists():
        for json_file in sorted(PROCESSED_DIR.iterdir()):
            if json_file.suffix != ".json":
                continue
            data = json.loads(json_file.read_text())
            portfolios.append({
                "client_id":       data.get("client_id"),
                "zoho_client_id":  data.get("zoho_client_id"),
                "source_file":     data.get("source_file", ""),
                "total_value":     data.get("total_value", 0),
                "asset_allocation": data.get("asset_allocation", {}),
                "risk_metrics":    data.get("risk_metrics", {}),
            })
    return {"portfolios": portfolios, "count": len(portfolios)}


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    """Return the full portfolio JSON for a specific processed portfolio."""
    return _load_portfolio(portfolio_id)
