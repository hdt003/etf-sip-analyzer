import httpx
import math
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from backend.app.services.market_data.base import BaseMarketDataProvider


def _safe_float(val, default=0.0) -> float:
    """Convert any value to JSON-safe float — replaces NaN/Inf with default."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


class MFAPIDataProvider(BaseMarketDataProvider):
    BASE_URL = "https://api.mfapi.in/mf"

    def get_price_data(self, symbol_or_code: str) -> Dict[str, Any]:
        """
        Fetches real NAV history from MFAPI.
        symbol_or_code MUST be a numeric scheme code (e.g. '122639').
        Never returns mock data — raises on failure so callers know it failed.
        """
        scheme_code = symbol_or_code.strip()

        if not scheme_code.isdigit():
            raise ValueError(
                f"MFAPIDataProvider requires a numeric scheme code, got: '{scheme_code}'"
            )

        url = f"{self.BASE_URL}/{scheme_code}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    raise ValueError(f"MFAPI HTTP {resp.status_code} for scheme {scheme_code}")
                data = resp.json()
        except Exception as e:
            raise RuntimeError(f"MFAPI fetch failed for {scheme_code}: {e}") from e

        meta = data.get("meta", {})
        data_list = data.get("data", [])
        scheme_name = meta.get("scheme_name", f"MF Scheme {scheme_code}")
        fund_house = meta.get("fund_house", "Mutual Fund AMC")
        category = meta.get("scheme_category", "Equity")

        if not data_list:
            raise ValueError(f"MFAPI returned empty data list for scheme {scheme_code}")

        # MFAPI returns newest-first (DD-MM-YYYY)
        parsed_records = []
        for item in data_list:
            try:
                dt = datetime.strptime(item["date"], "%d-%m-%Y").strftime("%Y-%m-%d")
                nav = _safe_float(item["nav"])
                if nav > 0:
                    parsed_records.append({"date": dt, "close": nav})
            except Exception:
                continue

        if not parsed_records:
            raise ValueError(f"Could not parse any valid NAV records for scheme {scheme_code}")

        # Sort oldest → newest
        parsed_records.sort(key=lambda x: x["date"])

        df = pd.DataFrame(parsed_records)

        current_price = _safe_float(df.iloc[-1]["close"])
        prev_price = _safe_float(df.iloc[-2]["close"]) if len(df) >= 2 else current_price

        if current_price <= 0:
            raise ValueError(f"Latest NAV is zero/invalid for scheme {scheme_code}")

        # ATH = all-time maximum NAV
        max_idx = df["close"].idxmax()
        ath_price = _safe_float(df.loc[max_idx, "close"])
        ath_date = str(df.loc[max_idx, "date"])

        # 52-week metrics (~252 trading days)
        last_year_df = df.tail(252)
        low_52w = _safe_float(last_year_df["close"].min())
        high_52w = _safe_float(last_year_df["close"].max())

        # Today's % change (latest NAV vs previous NAV)
        today_change_pct = 0.0
        if prev_price > 0:
            today_change_pct = round(((current_price - prev_price) / prev_price) * 100.0, 2)

        return {
            "symbol_or_code": scheme_code,
            "name": scheme_name,
            "asset_type": "MUTUAL_FUND",
            "current_price": current_price,
            "prev_price": prev_price,
            "today_change_pct": today_change_pct,
            "ath_price": ath_price,
            "ath_date": ath_date,
            "low_52w": low_52w,
            "high_52w": high_52w,
            "history": parsed_records,
            "amc": fund_house,
            "category": category,
        }

    def search_assets(self, query: str) -> List[Dict[str, Any]]:
        """Search MFAPI — always returns numeric scheme codes, never text names."""
        query_str = query.strip()
        url = f"https://api.mfapi.in/mf/search?q={query_str}"
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    results = resp.json()
                    output = []
                    for item in results[:20]:
                        code = str(item.get("schemeCode", "")).strip()
                        name = item.get("schemeName", "").strip()
                        if code and name:
                            output.append({
                                "symbol_or_code": code,
                                "name": name,
                                "asset_type": "MUTUAL_FUND",
                                "exchange": "MFAPI",
                            })
                    return output
        except Exception:
            pass
        return []
