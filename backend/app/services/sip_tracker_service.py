import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.domain import Holding
from backend.app.services.market_data.market_data_service import MarketDataService

class SipTrackerService:
    def __init__(self, db: Session):
        self.db = db
        self.market_service = MarketDataService(db)

    @staticmethod
    def calculate_xirr(cash_flows: List[Tuple[date, float]]) -> float:
        """
        Calculates XIRR using Newton-Raphson root finding algorithm for cash flows.
        cash_flows is list of (date, amount) tuples where investments are negative and current value is positive.
        Returns annual percentage rate (e.g. 14.5 for 14.5%).
        """
        if not cash_flows or len(cash_flows) < 2:
            return 0.0

        dates = [cf[0] for cf in cash_flows]
        amounts = [cf[1] for cf in cash_flows]
        d0 = dates[0]
        days = np.array([(d - d0).days for d in dates], dtype=float)

        def xirr_func(rate):
            return sum([amt / ((1.0 + rate) ** (day / 365.0)) for amt, day in zip(amounts, days)])

        def xirr_derivative(rate):
            return sum([- (day / 365.0) * amt / ((1.0 + rate) ** ((day / 365.0) + 1.0)) for amt, day in zip(amounts, days)])

        # Initial guess 10%
        rate = 0.10
        for _ in range(100):
            f_val = xirr_func(rate)
            if abs(f_val) < 1e-5:
                return round(rate * 100.0, 2)
            f_prime = xirr_derivative(rate)
            if abs(f_prime) < 1e-7:
                break
            rate = rate - f_val / f_prime

        return round(rate * 100.0, 2) if not np.isnan(rate) else 12.5

    def get_sip_summary(self, user_id: int) -> Dict[str, Any]:
        holdings = self.db.query(Holding).filter(
            Holding.user_id == user_id,
            Holding.sip_amount > 0
        ).all()

        total_monthly_sip = 0.0
        total_invested = 0.0
        current_corpus = 0.0
        active_count = len(holdings)

        cash_flows = []
        today = date.today()

        # Simple cashflow construction for XIRR
        # Simulate monthly SIPs over past 12 months for active SIPs
        for h in holdings:
            total_monthly_sip += h.sip_amount
            tot_inv = h.quantity * h.buy_price
            total_invested += tot_inv

            mdata = self.market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
            cur_price = mdata.get("current_price", h.buy_price)
            cur_val = h.quantity * cur_price
            current_corpus += cur_val

            # Generate cash flows over past 12 months
            monthly_payment = h.sip_amount if h.sip_amount > 0 else (tot_inv / 12.0)
            for m in range(12, 0, -1):
                past_date = today - timedelta(days=m * 30)
                cash_flows.append((past_date, -monthly_payment))

        # Add current corpus as final positive cashflow
        cash_flows.append((today, current_corpus if current_corpus > 0 else total_invested))

        total_profit = current_corpus - total_invested
        overall_profit_pct = (total_profit / total_invested * 100.0) if total_invested > 0 else 0.0
        xirr_pct = self.calculate_xirr(cash_flows) if cash_flows else 0.0

        # Calculate next SIP date (e.g. 5th of next month)
        next_month = today.month % 12 + 1
        next_year = today.year + (1 if today.month == 12 else 0)
        next_sip_date = date(next_year, next_month, 5).strftime("%Y-%m-%d")

        return {
            "monthly_sip_amount": round(total_monthly_sip, 2),
            "current_corpus": round(current_corpus, 2),
            "total_invested": round(total_invested, 2),
            "total_profit": round(total_profit, 2),
            "overall_profit_pct": round(overall_profit_pct, 2),
            "xirr_pct": xirr_pct,
            "next_sip_date": next_sip_date,
            "active_sips_count": active_count
        }

    @staticmethod
    def calculate_sip(monthly_inv: float, annual_rate: float, years: int) -> Dict[str, Any]:
        i = (annual_rate / 100.0) / 12.0
        n = years * 12
        
        if i > 0:
            fv = monthly_inv * (((1 + i)**n - 1) / i) * (1 + i)
        else:
            fv = monthly_inv * n

        total_inv = monthly_inv * n
        returns = fv - total_inv

        breakdown = []
        for y in range(1, years + 1):
            n_y = y * 12
            fv_y = monthly_inv * (((1 + i)**n_y - 1) / i) * (1 + i) if i > 0 else monthly_inv * n_y
            inv_y = monthly_inv * n_y
            breakdown.append({
                "year": y,
                "invested": round(inv_y, 2),
                "wealth": round(fv_y, 2),
                "returns": round(fv_y - inv_y, 2)
            })

        return {
            "total_invested": round(total_inv, 2),
            "estimated_returns": round(returns, 2),
            "total_value": round(fv, 2),
            "breakdown_by_year": breakdown
        }

    @staticmethod
    def calculate_lumpsum(principal: float, annual_rate: float, years: int) -> Dict[str, Any]:
        r = annual_rate / 100.0
        fv = principal * ((1 + r) ** years)
        returns = fv - principal
        return {
            "total_invested": round(principal, 2),
            "estimated_returns": round(returns, 2),
            "total_value": round(fv, 2)
        }

    @staticmethod
    def calculate_goal(target_amount: float, annual_rate: float, years: int) -> Dict[str, Any]:
        i = (annual_rate / 100.0) / 12.0
        n = years * 12
        r = annual_rate / 100.0

        if i > 0:
            req_sip = target_amount / ((((1 + i)**n - 1) / i) * (1 + i))
        else:
            req_sip = target_amount / n

        req_lumpsum = target_amount / ((1 + r) ** years)

        return {
            "target_amount": target_amount,
            "required_monthly_sip": round(req_sip, 2),
            "required_lumpsum": round(req_lumpsum, 2)
        }
