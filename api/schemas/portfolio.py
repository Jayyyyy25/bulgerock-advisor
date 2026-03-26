from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class AllocationItem(BaseModel):
    asset_class: str
    total_value: float
    pct: float


class HoldingItem(BaseModel):
    ticker: str
    security_name: Optional[str] = None
    isin: Optional[str] = None
    asset_class: Optional[str] = None
    sector: Optional[str] = None
    account_type: Optional[str] = None
    quantity: Optional[float] = None
    market_value: float


class PortfolioResponse(BaseModel):
    client_id: str
    as_of_date: Optional[date] = None
    total_aum_usd: float
    allocation: List[AllocationItem]
    top_holdings: List[HoldingItem]
