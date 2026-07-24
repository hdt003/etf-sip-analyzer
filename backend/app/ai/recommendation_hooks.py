from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.domain import Holding
from backend.app.services.market_data.market_data_service import MarketDataService

class AIRecommendationEngine:
    """
    Future-ready AI Advisory Hooks interface.
    Designed for LLM integration (e.g. Gemini 1.5/2.0 API, OpenAI, or local quantitative LLMs).
    """
    def __init__(self, db: Session):
        self.db = db
        self.market_service = MarketDataService(db)

    def get_personalized_dip_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        AI-generated personalized 'Buy the Dip' suggestions based on historical holdings.
        """
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        recommendations = []

        for h in holdings:
            mdata = self.market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
            cur_p = mdata.get("current_price", h.buy_price)
            ath_p = mdata.get("ath_price", cur_p)
            down_pct = round(((ath_p - cur_p) / ath_p * 100.0), 2) if ath_p > 0 else 0.0

            if down_pct >= 10.0:
                recommendations.append({
                    "symbol_or_code": h.symbol_or_code,
                    "name": h.name,
                    "dip_pct": down_pct,
                    "action": "Consider Accumulating",
                    "ai_insight": f"{h.name} is currently down {down_pct}% from its all-time peak of ₹{round(ath_p, 2)}. "
                                 f"Adding to your existing position at current price ₹{round(cur_p, 2)} will lower your average cost."
                })

        return sorted(recommendations, key=lambda x: x["dip_pct"], reverse=True)

    def get_portfolio_health_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Generates holistic AI portfolio health score and assessment.
        """
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        if not holdings:
            return {
                "health_score": 100,
                "status": "Optimal",
                "summary": "Your portfolio is clean and ready for initial capital deployment."
            }

        total_value = sum([h.quantity * h.buy_price for h in holdings])
        etf_count = sum(1 for h in holdings if h.asset_type == "ETF")
        mf_count = sum(1 for h in holdings if h.asset_type == "MUTUAL_FUND")

        # Diversification assessment
        is_balanced = (etf_count > 0 and mf_count > 0)
        
        return {
            "health_score": 88 if is_balanced else 72,
            "status": "Strong" if is_balanced else "Moderate",
            "summary": f"Your portfolio consists of {etf_count} ETFs and {mf_count} Mutual Funds. "
                       f"Asset allocation is {'well balanced between passive index ETFs and active SIP funds.' if is_balanced else 'skewed towards one asset type. Consider blending active mutual funds with low-cost index ETFs.'}"
        }

    def suggest_monthly_allocation(self, available_cash: float, user_id: int) -> List[Dict[str, Any]]:
        """
        Suggests optimal allocation of extra monthly capital into the most discounted assets.
        """
        dips = self.get_personalized_dip_recommendations(user_id)
        if not dips or available_cash <= 0:
            return []

        top_dips = dips[:3]
        total_weight = sum([d["dip_pct"] for d in top_dips])
        
        allocation = []
        for item in top_dips:
            weight = item["dip_pct"] / total_weight if total_weight > 0 else 1.0 / len(top_dips)
            alloc_amount = round(available_cash * weight, 2)
            allocation.append({
                "symbol_or_code": item["symbol_or_code"],
                "name": item["name"],
                "suggested_amount": alloc_amount,
                "allocation_pct": round(weight * 100.0, 1),
                "reason": f"Discounted by {item['dip_pct']}% from ATH."
            })

        return allocation
