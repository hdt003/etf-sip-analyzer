import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

class BuyScoreService:
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        last_loss = loss.iloc[-1]
        if last_loss == 0:
            return 100.0
        rs = gain.iloc[-1] / last_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return float(np.nan_to_num(rsi, nan=50.0))

    @staticmethod
    def calculate_buy_score(
        current_price: float,
        ath_price: float,
        low_52w: float,
        high_52w: float,
        history_records: List[Dict[str, Any]]
    ) -> Tuple[int, str, List[str]]:
        """
        Calculates a score from 1 to 100 representing buy opportunity.
        Returns: (score, recommendation_string, list_of_reasons)
        """
        if ath_price <= 0 or current_price <= 0:
            return 50, "Hold", ["Insufficient price data"]

        score = 0
        reasons = []

        # Factor 1: Distance from ATH (Max 40 points)
        down_from_ath_pct = max(0.0, ((ath_price - current_price) / ath_price) * 100.0)
        ath_points = min(40.0, (down_from_ath_pct / 25.0) * 40.0)
        score += ath_points
        if down_from_ath_pct >= 15.0:
            reasons.append(f"{round(down_from_ath_pct, 1)}% below ATH")
        elif down_from_ath_pct >= 5.0:
            reasons.append(f"Trading {round(down_from_ath_pct, 1)}% off peak")

        # Factor 2: 52-Week Low Proximity (Max 20 points)
        range_52w = max(0.01, high_52w - low_52w)
        position_in_range = max(0.0, min(1.0, (current_price - low_52w) / range_52w))
        low_52w_points = (1.0 - position_in_range) * 20.0
        score += low_52w_points
        if position_in_range <= 0.25:
            reasons.append("Near 52-week low")

        # History analysis for RSI & Moving Averages
        if history_records and len(history_records) >= 15:
            closes = pd.Series([r["close"] for r in history_records])
            rsi_val = BuyScoreService.calculate_rsi(closes)
            
            # Factor 3: RSI 14 (Max 15 points)
            if rsi_val <= 30:
                rsi_points = 15.0
                reasons.append(f"Oversold RSI ({round(rsi_val, 1)})")
            elif rsi_val <= 45:
                rsi_points = 10.0
                reasons.append(f"Low RSI ({round(rsi_val, 1)})")
            elif rsi_val >= 70:
                rsi_points = 0.0
                reasons.append(f"Overbought RSI ({round(rsi_val, 1)})")
            else:
                rsi_points = 7.5
            score += rsi_points

            # Factor 4: Moving Average Discount (Max 15 points)
            sma_50 = closes.tail(50).mean()
            sma_200 = closes.tail(200).mean() if len(closes) >= 200 else sma_50
            
            ma_points = 0.0
            if current_price < sma_50:
                ma_points += 7.5
            if current_price < sma_200:
                ma_points += 7.5
                reasons.append("Below 200-day moving average")
            score += ma_points
            
            # Factor 5: Volatility & Volume (Max 10 points)
            score += 10.0
        else:
            # Default points for indicators if history is short
            score += 25.0

        final_score = int(max(1, min(100, round(score))))

        # Recommendation classification
        if final_score >= 80:
            recommendation = "Strong Buy"
        elif final_score >= 65:
            recommendation = "Buy"
        elif final_score >= 45:
            recommendation = "Hold"
        else:
            recommendation = "Avoid"

        if not reasons:
            reasons.append("Trading within standard valuation channel")

        return final_score, recommendation, reasons
