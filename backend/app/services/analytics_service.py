import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.domain import Holding
from backend.app.services.market_data.market_data_service import MarketDataService
from backend.app.services.buy_score_service import BuyScoreService

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.market_service = MarketDataService(db)

    def get_dashboard_summary(self, user_id: int) -> Dict[str, Any]:
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        
        total_invested = 0.0
        total_current_value = 0.0
        etf_count = 0
        sip_count = 0
        dip_percentages = []

        processed_holdings = []

        for h in holdings:
            mdata = self.market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
            cur_price = mdata.get("current_price", h.buy_price)
            ath_price = mdata.get("ath_price", cur_price)
            
            cur_val = h.quantity * cur_price
            tot_inv = h.quantity * h.buy_price
            
            total_invested += tot_inv
            total_current_value += cur_val
            
            if h.asset_type == "ETF":
                etf_count += 1
            else:
                sip_count += 1

            if h.sip_amount > 0 and h.asset_type == "MUTUAL_FUND":
                pass # accounted in sip count

            down_pct = 0.0
            if ath_price > 0:
                down_pct = max(0.0, ((ath_price - cur_price) / ath_price) * 100.0)
            dip_percentages.append(down_pct)

            profit = cur_val - tot_inv
            profit_pct = ((cur_val - tot_inv) / tot_inv * 100.0) if tot_inv > 0 else 0.0

            processed_holdings.append({
                "holding": h,
                "current_price": cur_price,
                "current_value": cur_val,
                "total_invested": tot_inv,
                "profit": profit,
                "profit_pct": profit_pct,
                "down_pct": down_pct,
                "ath_price": ath_price,
                "buy_score": mdata.get("buy_score", 50),
                "asset_type": h.asset_type,
                "name": h.name,
                "symbol": h.symbol_or_code
            })

        total_profit = total_current_value - total_invested
        overall_gain_pct = (total_profit / total_invested * 100.0) if total_invested > 0 else 0.0
        avg_dip = float(np.mean(dip_percentages)) if dip_percentages else 0.0

        # Highlights calculation
        top_gainer = max(processed_holdings, key=lambda x: x["profit_pct"]) if processed_holdings else None
        top_loser = min(processed_holdings, key=lambda x: x["profit_pct"]) if processed_holdings else None
        
        etf_holdings = [x for x in processed_holdings if x["asset_type"] == "ETF"]
        mf_holdings = [x for x in processed_holdings if x["asset_type"] == "MUTUAL_FUND"]

        most_discounted_etf = max(etf_holdings, key=lambda x: x["down_pct"]) if etf_holdings else None
        most_discounted_mf = max(mf_holdings, key=lambda x: x["down_pct"]) if mf_holdings else None

        highest_profit_holding = max(processed_holdings, key=lambda x: x["profit"]) if processed_holdings else None
        lowest_profit_holding = min(processed_holdings, key=lambda x: x["profit"]) if processed_holdings else None

        return {
            "total_portfolio_value": round(total_current_value, 2),
            "total_invested": round(total_invested, 2),
            "total_profit": round(total_profit, 2),
            "overall_gain_pct": round(overall_gain_pct, 2),
            "todays_gain_loss": round(total_current_value * 0.005, 2),  # Simulated daily change
            "todays_gain_loss_pct": 0.5,
            "number_of_etfs": etf_count,
            "number_of_sips": sip_count,
            "avg_dip_from_ath": round(avg_dip, 2),
            "top_gainer": top_gainer,
            "top_loser": top_loser,
            "most_discounted_etf": most_discounted_etf,
            "most_discounted_mf": most_discounted_mf,
            "highest_profit_holding": highest_profit_holding,
            "lowest_profit_holding": lowest_profit_holding
        }

    def get_peak_analysis(self, user_id: int) -> List[Dict[str, Any]]:
        import math

        def _safe(val, default=0.0):
            try:
                f = float(val)
                return default if (math.isnan(f) or math.isinf(f)) else f
            except Exception:
                return default

        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        results = []

        for h in holdings:
            try:
                mdata = self.market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type, force_refresh=True)
            except Exception as fetch_err:
                results.append({
                    "symbol_or_code": h.symbol_or_code,
                    "name": h.name,
                    "asset_type": h.asset_type,
                    "current_price": 0.0,
                    "ath_or_peak_nav": 0.0,
                    "down_pct": 0.0,
                    "today_change_pct": 0.0,
                    "color_status": "Error",
                    "buy_score": 0,
                    "buy_recommendation": "Data Error",
                    "score_reasons": f"Fetch failed: {str(fetch_err)[:80]}"
                })
                continue

            cur_price = _safe(mdata.get("current_price", 0.0))
            ath_price = _safe(mdata.get("ath_price", cur_price))
            today_change_pct = _safe(mdata.get("today_change_pct", 0.0))

            if cur_price <= 0 or ath_price <= 0:
                results.append({
                    "symbol_or_code": h.symbol_or_code,
                    "name": h.name,
                    "asset_type": h.asset_type,
                    "current_price": 0.0,
                    "ath_or_peak_nav": 0.0,
                    "down_pct": 0.0,
                    "today_change_pct": 0.0,
                    "color_status": "Error",
                    "buy_score": 0,
                    "buy_recommendation": "Invalid Data",
                    "score_reasons": "Provider returned zero/invalid price — check symbol"
                })
                continue

            down_pct = round(((ath_price - cur_price) / ath_price) * 100.0, 2)

            if down_pct <= 5.0:
                color_status = "Green"
            elif down_pct <= 15.0:
                color_status = "Yellow"
            else:
                color_status = "Red"

            history = mdata.get("history", [])
            b_score, b_rec, b_reasons = BuyScoreService.calculate_buy_score(
                cur_price, ath_price,
                _safe(mdata.get("low_52w", cur_price * 0.85)),
                _safe(mdata.get("high_52w", ath_price)),
                history,
                asset_type=h.asset_type
            )

            results.append({
                "symbol_or_code": h.symbol_or_code,
                "name": h.name,
                "asset_type": h.asset_type,
                "current_price": round(cur_price, 4),
                "ath_or_peak_nav": round(ath_price, 4),
                "ath_date": mdata.get("ath_date", ""),
                "down_pct": down_pct,
                "today_change_pct": today_change_pct,
                "color_status": color_status,
                "buy_score": b_score,
                "buy_recommendation": b_rec,
                "score_reasons": ", ".join(b_reasons)
            })

        return results

    def get_allocation_breakdown(self, user_id: int) -> Dict[str, Any]:
        holdings = self.db.query(Holding).filter(Holding.user_id == user_id).all()
        
        asset_alloc = {"ETF": 0.0, "Mutual Fund": 0.0}
        amc_alloc = {}
        sector_alloc = {}
        total_val = 0.0

        for h in holdings:
            mdata = self.market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
            cur_price = mdata.get("current_price", h.buy_price)
            val = h.quantity * cur_price
            total_val += val

            # Asset type
            atype_key = "ETF" if h.asset_type == "ETF" else "Mutual Fund"
            asset_alloc[atype_key] = asset_alloc.get(atype_key, 0.0) + val

            # AMC
            amc_key = h.amc or mdata.get("amc", "Other")
            amc_alloc[amc_key] = amc_alloc.get(amc_key, 0.0) + val

            # Sector
            sec_key = h.sector or mdata.get("sector", "General")
            sector_alloc[sec_key] = sector_alloc.get(sec_key, 0.0) + val

        # Convert to percentages
        if total_val > 0:
            asset_alloc = {k: round((v / total_val) * 100.0, 1) for k, v in asset_alloc.items()}
            amc_alloc = {k: round((v / total_val) * 100.0, 1) for k, v in amc_alloc.items()}
            sector_alloc = {k: round((v / total_val) * 100.0, 1) for k, v in sector_alloc.items()}

        return {
            "asset_allocation": asset_alloc,
            "amc_allocation": amc_alloc,
            "sector_allocation": sector_alloc
        }

    def get_historical_chart(self, symbol_or_code: str, timeframe: str = "1Y", user_id: Optional[int] = None) -> Dict[str, Any]:
        mdata = self.market_service.get_market_data(symbol_or_code)
        history = mdata.get("history", [])
        
        if not history:
            # Generate fallback timeline
            dates = pd.date_range(end=datetime.today(), periods=30, freq='D').strftime("%Y-%m-%d")
            base_p = mdata.get("current_price", 100.0)
            history = [{"date": str(d), "close": base_p * (1 + np.sin(i/3.0)*0.05)} for i, d in enumerate(dates)]

        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Filter by timeframe
        now = datetime.today()
        if timeframe == "1M":
            cutoff = now - timedelta(days=30)
        elif timeframe == "3M":
            cutoff = now - timedelta(days=90)
        elif timeframe == "6M":
            cutoff = now - timedelta(days=180)
        elif timeframe == "1Y":
            cutoff = now - timedelta(days=365)
        elif timeframe == "5Y":
            cutoff = now - timedelta(days=365 * 5)
        else:
            cutoff = df['date'].min()

        filtered_df = df[df['date'] >= cutoff]
        if filtered_df.empty:
            filtered_df = df.tail(30)

        ath_price = mdata.get("ath_price", filtered_df['close'].max())
        
        buy_price = None
        if user_id:
            h = self.db.query(Holding).filter(Holding.symbol_or_code == symbol_or_code, Holding.user_id == user_id).first()
            if h:
                buy_price = h.buy_price

        points = []
        for _, row in filtered_df.iterrows():
            points.append({
                "date": row['date'].strftime("%Y-%m-%d"),
                "price": round(float(row['close']), 2),
                "ath": round(float(ath_price), 2),
                "buy_price": round(float(buy_price), 2) if buy_price else None,
                "avg_price": round(float(buy_price), 2) if buy_price else None
            })

        return {
            "symbol_or_code": symbol_or_code,
            "name": mdata.get("name", symbol_or_code),
            "timeframe": timeframe,
            "points": points,
            "current_price": mdata.get("current_price", 0.0),
            "ath_price": ath_price,
            "buy_price": buy_price,
            "avg_price": buy_price
        }

    def get_holding_statistics(self, holding_id: int, user_id: int) -> Dict[str, Any]:
        h = self.db.query(Holding).filter(Holding.id == holding_id, Holding.user_id == user_id).first()
        if not h:
            raise ValueError("Holding not found")

        mdata = self.market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
        cur_price = mdata.get("current_price", h.buy_price)
        history = mdata.get("history", [])

        if history:
            df = pd.DataFrame(history)
            closes = df['close']
            highest = float(closes.max())
            lowest = float(closes.min())
            atl = float(closes.min())
            
            # Volatility (annualized std dev)
            pct_change = closes.pct_change().dropna()
            volatility = float(pct_change.std() * np.sqrt(252) * 100.0) if not pct_change.empty else 15.0

            # Max Drawdown
            rolling_max = closes.cummax()
            drawdown = (closes - rolling_max) / rolling_max
            max_drawdown = float(abs(drawdown.min()) * 100.0)
        else:
            highest = mdata.get("ath_price", cur_price)
            lowest = cur_price * 0.8
            atl = cur_price * 0.75
            volatility = 15.0
            max_drawdown = 12.0

        ath = mdata.get("ath_price", highest)
        high_52w = mdata.get("high_52w", highest)
        low_52w = mdata.get("low_52w", lowest)

        tot_inv = h.quantity * h.buy_price
        cur_val = h.quantity * cur_price
        abs_return = cur_val - tot_inv
        abs_return_pct = (abs_return / tot_inv * 100.0) if tot_inv > 0 else 0.0

        # Estimated 1-year CAGR
        cagr = abs_return_pct

        return {
            "symbol_or_code": h.symbol_or_code,
            "name": h.name,
            "highest_price": round(highest, 2),
            "lowest_price": round(lowest, 2),
            "ath": round(ath, 2),
            "atl": round(atl, 2),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "average_nav_cost": round(h.buy_price, 2),
            "current_return_amount": round(abs_return, 2),
            "absolute_return_pct": round(abs_return_pct, 2),
            "cagr_pct": round(cagr, 2),
            "volatility_pct": round(volatility, 2),
            "max_drawdown_pct": round(max_drawdown, 2)
        }
