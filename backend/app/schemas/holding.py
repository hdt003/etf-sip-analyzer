from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class HoldingCreate(BaseModel):
    asset_type: str  # 'ETF' or 'MUTUAL_FUND'
    symbol_or_code: str  # e.g., 'NIFTYBEES.NS' or '122639'
    name: str
    quantity: float = 0.0
    buy_price: float = 0.0
    sip_amount: float = 0.0
    sip_date: Optional[int] = None
    exchange: str = "NSE"
    sector: str = "General"
    amc: str = "Other"

class HoldingUpdate(BaseModel):
    quantity: Optional[float] = None
    buy_price: Optional[float] = None
    sip_amount: Optional[float] = None
    sip_date: Optional[int] = None
    sector: Optional[str] = None
    amc: Optional[str] = None

class HoldingResponse(BaseModel):
    id: int
    user_id: int
    asset_type: str
    symbol_or_code: str
    name: str
    quantity: float
    buy_price: float
    total_invested: float
    sip_amount: float
    sip_date: Optional[int] = None
    exchange: str
    sector: str
    amc: str
    
    # Dynamic live fields populated by market service
    current_price: float = 0.0
    current_value: float = 0.0
    gain_loss: float = 0.0
    gain_loss_pct: float = 0.0
    ath_price: float = 0.0
    down_from_ath_pct: float = 0.0
    buy_score: int = 50
    buy_recommendation: str = "Hold"
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
