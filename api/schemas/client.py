from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClientSummary(BaseModel):
    client_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    risk_profile: Optional[str] = None
    advisor_id: Optional[str] = None
    aum: Optional[float] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
