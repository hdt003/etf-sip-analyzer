"""
Market Indices API — Live NIFTY index data via yfinance.
Returns current value, today's change, ATH and % down from ATH for each index.
"""

from fastapi import APIRouter
import yfinance as yf
import math
from datetime import datetime
from typing import List, Dict, Any

router = APIRouter(prefix="/indices", tags=["Market Indices"])


# ─── Index definitions ────────────────────────────────────────────────────────
INDICES = [
    {
        "key": "nifty50",
        "ticker": "^NSEI",
        "display_name": "Nifty 50 Index",
        "label": "NIFTY 50",
        "description": "Benchmark index of India's top 50 large-cap companies",
        "color": "blue",
    },
    {
        "key": "nifty100",
        "ticker": "^CNX100",
        "display_name": "Nifty 100 Index",
        "label": "NIFTY 100",
        "description": "Top 100 large-cap companies on NSE",
        "color": "indigo",
    },
    {
        "key": "niftymidcap150",
        "ticker": "NIFTYMIDCAP150.NS",
        "fallback_ticker": "^NSMIDCP",
        "display_name": "Nifty Midcap 150",
        "label": "NIFTY MIDCAP 150",
        "description": "150 mid-cap companies ranked 101-250 by market cap",
        "color": "violet",
    },
    {
        "key": "niftysmlcap100",
        "ticker": "^CNXSC",
        "display_name": "Nifty Smlcap 100",
        "label": "NIFTY SMLCAP 100",
        "description": "Top 100 small-cap companies on NSE",
        "color": "amber",
    },
]


def _safe_float(val, default: float = 0.0) -> float:
    """Convert any value to a JSON-safe float, replacing NaN/Inf with default."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _fetch_index(ticker_symbol: str, fallback: str | None = None) -> Dict[str, Any]:
    """Fetch index data via yfinance. Tries multiple history periods as fallback."""
    candidates = [ticker_symbol] + ([fallback] if fallback else [])
    # Try progressively shorter periods if 'max' is not available for some indices
    for sym in candidates:
        periods = ["5d", "1d"] if sym == "^CNXSC" else ["max", "5y", "2y", "1y", "5d", "1d"]
        for period in periods:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period=period)
                if hist.empty:
                    continue

                hist = hist.reset_index()
                hist["DateStr"] = hist["Date"].dt.strftime("%Y-%m-%d")
                hist = hist.dropna(subset=["Close"])
                hist = hist[hist["Close"] > 0]

                if hist.empty:
                    continue

                records = [
                    {"date": row["DateStr"], "close": _safe_float(row["Close"])}
                    for _, row in hist.iterrows()
                    if _safe_float(row["Close"]) > 0
                ]

                if not records:
                    continue

                current_value = records[-1]["close"]
                prev_value = records[-2]["close"] if len(records) >= 2 else current_value

                # Prefer live fast_info
                try:
                    fi = ticker.fast_info
                    live_last = _safe_float(getattr(fi, "last_price", 0))
                    live_prev = _safe_float(getattr(fi, "previous_close", 0))
                    if live_last > 0:
                        current_value = live_last
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        if records and records[-1]["date"] == today_str:
                            records[-1]["close"] = live_last
                        else:
                            records.append({"date": today_str, "close": live_last})
                    if live_prev > 0:
                        prev_value = live_prev
                except Exception:
                    pass

                ath_value = max(r["close"] for r in records)
                ath_record = next(r for r in records if r["close"] == ath_value)
                ath_date = ath_record["date"]

                last_250 = [r["close"] for r in records[-250:]]
                low_52w = min(last_250)
                high_52w = max(last_250)

                today_change_pct = 0.0
                if prev_value > 0:
                    today_change_pct = round(((current_value - prev_value) / prev_value) * 100.0, 2)

                down_pct = round(((ath_value - current_value) / ath_value) * 100.0, 2) if ath_value > 0 else 0.0

                # For indices: Green = within 5% of ATH, Red = 5%+ fall (no Yellow zone)
                if down_pct < 5.0:
                    color_status = "Green"
                else:
                    color_status = "Red"

                return {
                    "ok": True,
                    "used_ticker": sym,
                    "current_value": round(current_value, 2),
                    "prev_value": round(prev_value, 2),
                    "today_change_pct": today_change_pct,
                    "ath_value": round(ath_value, 2),
                    "ath_date": ath_date,
                    "down_from_ath_pct": down_pct,
                    "low_52w": round(low_52w, 2),
                    "high_52w": round(high_52w, 2),
                    "color_status": color_status,
                }

            except Exception:
                continue

    return {"ok": False, "error": f"Could not fetch data for {ticker_symbol}"}


@router.get("", response_model=List[Dict[str, Any]])
def get_indices():
    """
    Fetch live data for 4 key Indian market indices.
    Returns current value, ATH, % down from peak and color-coded status.
    """
    results = []
    for idx in INDICES:
        raw = _fetch_index(idx["ticker"], idx.get("fallback_ticker"))
        entry = {
            "key": idx["key"],
            "ticker": idx["ticker"],
            "display_name": idx["display_name"],
            "label": idx["label"],
            "description": idx["description"],
            "color": idx["color"],
        }
        if raw.get("ok"):
            entry.update({
                "status": "ok",
                "used_ticker": raw["used_ticker"],
                "current_value": raw["current_value"],
                "prev_value": raw["prev_value"],
                "today_change_pct": raw["today_change_pct"],
                "ath_value": raw["ath_value"],
                "ath_date": raw["ath_date"],
                "down_from_ath_pct": raw["down_from_ath_pct"],
                "low_52w": raw["low_52w"],
                "high_52w": raw["high_52w"],
                "color_status": raw["color_status"],
            })
        else:
            entry.update({
                "status": "error",
                "error": raw.get("error", "Unknown error"),
                "current_value": 0,
                "today_change_pct": 0,
                "ath_value": 0,
                "down_from_ath_pct": 0,
                "color_status": "Red",
            })
        results.append(entry)
    return results
