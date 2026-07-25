from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import date

class MetricCard(BaseModel):
    title: str
    value: str
    subtext: Optional[str] = None
    change_pct: Optional[float] = None
    icon: Optional[str] = None
    color: Optional[str] = "blue"

class DashboardSummary(BaseModel):
    total_portfolio_value: float
    total_invested: float
    total_profit: float
    overall_gain_pct: float
    todays_gain_loss: float
    todays_gain_loss_pct: float
    number_of_etfs: int
    number_of_sips: int
    avg_dip_from_ath: float
    
    # Widget highlights
    top_gainer: Optional[Dict[str, Any]] = None
    top_loser: Optional[Dict[str, Any]] = None
    most_discounted_etf: Optional[Dict[str, Any]] = None
    most_discounted_mf: Optional[Dict[str, Any]] = None
    highest_profit_holding: Optional[Dict[str, Any]] = None
    lowest_profit_holding: Optional[Dict[str, Any]] = None

class PeakAnalysisItem(BaseModel):
    symbol_or_code: str
    name: str
    asset_type: str
    current_price: float
    ath_or_peak_nav: float
    ath_date: Optional[str] = ""
    down_pct: float
    color_status: str  # 'Green' (within 5%), 'Yellow' (5-15%), 'Red' (>15%)
    buy_score: int
    buy_recommendation: str

class AllocationBreakdown(BaseModel):
    asset_allocation: Dict[str, float]  # e.g., {"ETF": 60.0, "Mutual Fund": 40.0}
    amc_allocation: Dict[str, float]
    sector_allocation: Dict[str, float]

class HistoricalChartPoint(BaseModel):
    date: str
    price: float
    ath: Optional[float] = None
    buy_price: Optional[float] = None
    avg_price: Optional[float] = None

class HistoricalChartResponse(BaseModel):
    symbol_or_code: str
    name: str
    timeframe: str
    points: List[HistoricalChartPoint]
    current_price: float
    ath_price: float
    buy_price: Optional[float] = None
    avg_price: Optional[float] = None

class SIPTrackerSummary(BaseModel):
    monthly_sip_amount: float
    current_corpus: float
    total_invested: float
    total_profit: float
    overall_profit_pct: float
    xirr_pct: float
    next_sip_date: Optional[str] = None
    active_sips_count: int

class SIPCalculatorRequest(BaseModel):
    monthly_investment: float
    expected_return_rate: float  # Annual % e.g. 12.0
    time_period_years: int

class SIPCalculatorResponse(BaseModel):
    total_invested: float
    estimated_returns: float
    total_value: float
    breakdown_by_year: List[Dict[str, Any]]

class GoalCalculatorRequest(BaseModel):
    target_amount: float
    expected_return_rate: float
    time_period_years: int

class GoalCalculatorResponse(BaseModel):
    required_monthly_sip: float
    required_lumpsum: float

class HoldingStatistics(BaseModel):
    symbol_or_code: str
    name: str
    highest_price: float
    lowest_price: float
    ath: float
    atl: float
    high_52w: float
    low_52w: float
    average_nav_cost: float
    current_return_amount: float
    absolute_return_pct: float
    cagr_pct: float
    volatility_pct: float
    max_drawdown_pct: float
