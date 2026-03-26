from pydantic import BaseModel
from typing import Optional
from datetime import date


class PolicyResponse(BaseModel):
    policy_id: str
    client_id: str
    full_name: Optional[str] = None
    policy_type: Optional[str] = None
    insurer: Optional[str] = None
    coverage_amount: Optional[float] = None
    premium: Optional[float] = None
    renewal_date: Optional[date] = None
    days_until_renewal: Optional[int] = None
    status: Optional[str] = None
