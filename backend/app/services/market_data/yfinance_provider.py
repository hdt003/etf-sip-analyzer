import yfinance as yf
import pandas as pd
import math
import httpx
from datetime import datetime
from typing import Dict, Any, List
from backend.app.services.market_data.base import BaseMarketDataProvider

# Popular Indian ETFs catalog for fast search
POPULAR_ETFS = [
    {"symbol": "NIFTYBEES.NS", "name": "Nippon India ETF Nifty BeES", "sector": "Broad Market", "amc": "Nippon India"},
    {"symbol": "GOLDBEES.NS", "name": "Nippon India ETF Gold BeES", "sector": "Commodities", "amc": "Nippon India"},
    {"symbol": "BANKBEES.NS", "name": "Nippon India ETF Bank BeES", "sector": "Banking & Financials", "amc": "Nippon India"},
    {"symbol": "MID150BEES.NS", "name": "Nippon India ETF Nifty Midcap 150", "sector": "Midcap", "amc": "Nippon India"},
    {"symbol": "JUNIORBEES.NS", "name": "Nippon India ETF Nifty Next 50", "sector": "Next 50", "amc": "Nippon India"},
    {"symbol": "MON100.NS", "name": "Motilal Oswal Nasdaq 100 ETF", "sector": "International", "amc": "Motilal Oswal"},
    {"symbol": "AUTOBEES.NS", "name": "Nippon India ETF Nifty Auto", "sector": "Automobile", "amc": "Nippon India"},
    {"symbol": "ITBEES.NS", "name": "Nippon India ETF Nifty IT", "sector": "Information Technology", "amc": "Nippon India"},
    {"symbol": "SILVERBEES.NS", "name": "Nippon India ETF Silver BeES", "sector": "Commodities", "amc": "Nippon India"},
    {"symbol": "CPSEETF.NS", "name": "CPSE ETF", "sector": "Public Sector", "amc": "Nippon India"},
    {"symbol": "PHARMABEES.NS", "name": "Nippon India ETF Nifty Pharma", "sector": "Healthcare", "amc": "Nippon India"},
    {"symbol": "SMALLCAP.NS", "name": "HDFC Nifty Smallcap 250 ETF", "sector": "Smallcap", "amc": "HDFC Mutual Fund"},
    {"symbol": "VAL30IETF.NS", "name": "ICICI Prudential Nifty200 Value 30 ETF", "sector": "Factor / Value", "amc": "ICICI Prudential"},
]


def _safe_float(val, default=0.0) -> float:
    """Convert any value to a JSON-safe float, replacing NaN/Inf with default."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


class YFinanceDataProvider(BaseMarketDataProvider):
    def normalize_symbol(self, symbol: str) -> str:
        s = symbol.upper().strip()
        if not s.endswith(".NS") and not s.endswith(".BO"):
            s = f"{s}.NS"
        return s

    def get_price_data(self, symbol_or_code: str) -> Dict[str, Any]:
        ticker_symbol = self.normalize_symbol(symbol_or_code)

        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="max")
            if hist.empty:
                raw_sym = symbol_or_code.upper().strip()
                ticker = yf.Ticker(raw_sym)
                hist = ticker.history(period="max")
                ticker_symbol = raw_sym
        except Exception as e:
            raise RuntimeError(f"yfinance fetch failed for {ticker_symbol}: {e}") from e

        if hist.empty:
            raise ValueError(
                f"yfinance returned no data for '{ticker_symbol}'. "
                "Check the symbol is a valid NSE ETF ticker (e.g. NIFTYBEES.NS)"
            )

        hist = hist.reset_index()
        hist["DateStr"] = hist["Date"].dt.strftime("%Y-%m-%d")

        # drop rows where Close is NaN
        hist = hist.dropna(subset=["Close"])
        hist = hist[hist["Close"] > 0]

        if hist.empty:
            raise ValueError(f"All rows were NaN/zero for {ticker_symbol}")

        history_records = []
        for _, row in hist.iterrows():
            close_val = _safe_float(row["Close"])
            if close_val > 0:
                history_records.append({
                    "date": row["DateStr"],
                    "close": close_val,
                })

        if not history_records:
            raise ValueError(f"No valid price records parsed for {ticker_symbol}")

        current_price = history_records[-1]["close"]
        prev_price = history_records[-2]["close"] if len(history_records) >= 2 else current_price

        # Enrich with live / real-time fast_info from Yahoo Finance to avoid stale historical close
        try:
            fi = ticker.fast_info
            real_last = _safe_float(getattr(fi, "last_price", 0))
            real_prev = _safe_float(getattr(fi, "previous_close", 0))
            if real_last > 0:
                current_price = real_last
                today_str = datetime.now().strftime("%Y-%m-%d")
                if history_records and history_records[-1]["date"] == today_str:
                    history_records[-1]["close"] = real_last
                else:
                    history_records.append({"date": today_str, "close": real_last})
            if real_prev > 0:
                prev_price = real_prev
        except Exception:
            pass

        # Calculate ATH & 52-week metrics with updated history
        ath_price = max([r["close"] for r in history_records])
        ath_record = next(r for r in history_records if r["close"] == ath_price)
        ath_date = ath_record["date"]

        last_250_closes = [r["close"] for r in history_records[-250:]]
        low_52w = min(last_250_closes)
        high_52w = max(last_250_closes)

        # Today's percentage change
        today_change_pct = 0.0
        if prev_price > 0:
            today_change_pct = round(((current_price - prev_price) / prev_price) * 100.0, 2)

        match = next((item for item in POPULAR_ETFS if item["symbol"] == ticker_symbol), None)
        name = match["name"] if match else ticker_symbol.replace(".NS", "")
        sector = match["sector"] if match else "Equity ETF"
        amc = match["amc"] if match else "NSE ETF"

        return {
            "symbol_or_code": ticker_symbol,
            "name": name,
            "asset_type": "ETF",
            "current_price": current_price,
            "prev_price": prev_price,
            "today_change_pct": today_change_pct,
            "ath_price": ath_price,
            "ath_date": ath_date,
            "low_52w": low_52w,
            "high_52w": high_52w,
            "history": history_records,
            "amc": amc,
            "sector": sector,
        }

    def search_assets(self, query: str) -> List[Dict[str, Any]]:
        q = query.upper().strip()
        results = []

        # 1. Add popular ETFs if they match the query
        for item in POPULAR_ETFS:
            if q in item["symbol"] or q in item["name"].upper():
                results.append({
                    "symbol_or_code": item["symbol"],
                    "name": item["name"],
                    "asset_type": "ETF",
                    "exchange": "NSE",
                })

        # 2. Query Yahoo Finance live search API to fetch actual ETFs on NSE/BSE
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}&newsCount=0"
            headers = {"User-Agent": "Mozilla/5.0"}
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for quote in data.get("quotes", []):
                        symbol = quote.get("symbol", "")
                        # Filter to NSE/BSE stocks/ETFs
                        if symbol.endswith(".NS") or symbol.endswith(".BO"):
                            name = quote.get("longname") or quote.get("shortname") or symbol
                            # Avoid duplicates
                            if not any(r["symbol_or_code"] == symbol for r in results):
                                results.append({
                                    "symbol_or_code": symbol,
                                    "name": name,
                                    "asset_type": "ETF",
                                    "exchange": "NSE" if symbol.endswith(".NS") else "BSE",
                                })
        except Exception:
            pass

        # 3. Fallback: if query looks like a potential custom ticker, add it as a direct option
        if not results and len(q) >= 3:
            sym = f"{q}.NS" if not (q.endswith(".NS") or q.endswith(".BO")) else q
            results.append({
                "symbol_or_code": sym,
                "name": f"Custom Ticker ({q})",
                "asset_type": "ETF",
                "exchange": "NSE",
            })

        return results[:15]
