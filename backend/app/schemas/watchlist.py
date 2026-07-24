from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WatchlistCreate(BaseModel):
    asset_type: str  # 'ETF' or 'MUTUAL_FUND'
    symbol_or_code: str
    name: str

class WatchlistResponse(BaseModel):
    id: int
    user_id: int
    asset_type: str
    symbol_or_code: str
    name: str
    current_price: float = 0.0
    ath_price: float = 0.0
    down_from_ath_pct: float = 0.0
    buy_score: int = 50
    buy_recommendation: str = "Hold"
    created_at: datetime

    class Config:
        from_attributes = True
