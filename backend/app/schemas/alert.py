from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AlertCreate(BaseModel):
    symbol_or_code: str
    asset_name: str
    asset_type: str  # 'ETF' or 'MUTUAL_FUND'
    target_type: str = "ATH_DROP"  # 'ATH_DROP' or 'PEAK_NAV_DROP'
    drop_percentage: float  # 5, 10, 15, 20

class AlertResponse(BaseModel):
    id: int
    user_id: int
    symbol_or_code: str
    asset_name: str
    asset_type: str
    target_type: str
    drop_percentage: float
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
