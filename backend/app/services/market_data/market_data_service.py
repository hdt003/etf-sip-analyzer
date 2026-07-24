from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from backend.app.models.domain import PriceCache
from backend.app.services.market_data.mfapi import MFAPIDataProvider
from backend.app.services.market_data.yfinance_provider import YFinanceDataProvider


class MarketDataService:
    def __init__(self, db: Session):
        self.db = db
        self.mf_provider = MFAPIDataProvider()
        self.etf_provider = YFinanceDataProvider()

    def is_mutual_fund(self, symbol_or_code: str) -> bool:
        """Scheme codes from MFAPI are pure numeric strings (e.g. '122639')."""
        return symbol_or_code.strip().isdigit()

    def get_market_data(
        self,
        symbol_or_code: str,
        asset_type: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        symbol_clean = symbol_or_code.strip()

        # Serve from cache if fresh (< 4 hours) and not forcing refresh
        if not force_refresh:
            cached = (
                self.db.query(PriceCache)
                .filter(PriceCache.symbol_or_code == symbol_clean)
                .first()
            )
            if (
                cached
                and cached.last_updated
                and (datetime.utcnow() - cached.last_updated) < timedelta(hours=4)
                and cached.current_price is not None
                and cached.current_price > 0
            ):
                return {
                    "symbol_or_code": cached.symbol_or_code,
                    "name": cached.asset_name,
                    "asset_type": cached.asset_type,
                    "current_price": cached.current_price,
                    "ath_price": cached.ath_price,
                    "ath_date": str(cached.ath_date) if cached.ath_date else None,
                    "down_from_ath_pct": cached.down_from_ath_pct,
                    "low_52w": cached.low_52w or cached.current_price * 0.85,
                    "high_52w": cached.high_52w or cached.ath_price,
                    "buy_score": cached.buy_score,
                    "buy_recommendation": cached.buy_recommendation,
                    "score_reasons": cached.score_reasons,
                    "history": [],   # history not cached in DB — fetched fresh for charts
                }

        # Route to correct provider — MFAPI for MFs, yfinance for ETFs
        if asset_type == "MUTUAL_FUND" or self.is_mutual_fund(symbol_clean):
            data = self.mf_provider.get_price_data(symbol_clean)
            resolved_asset_type = "MUTUAL_FUND"
        else:
            data = self.etf_provider.get_price_data(symbol_clean)
            resolved_asset_type = "ETF"

        current_p = data.get("current_price", 0.0)
        ath_p = data.get("ath_price", current_p)

        if current_p <= 0:
            raise ValueError(
                f"Provider returned invalid current_price={current_p} for {symbol_clean}"
            )

        down_pct = 0.0
        if ath_p > 0:
            down_pct = round(((ath_p - current_p) / ath_p) * 100.0, 2)

        # Persist in cache
        cached = (
            self.db.query(PriceCache)
            .filter(PriceCache.symbol_or_code == symbol_clean)
            .first()
        )
        if not cached:
            cached = PriceCache(symbol_or_code=symbol_clean)
            self.db.add(cached)

        cached.asset_name = data.get("name", symbol_clean)
        cached.asset_type = resolved_asset_type
        cached.current_price = current_p
        cached.ath_price = ath_p
        cached.down_from_ath_pct = down_pct
        cached.high_52w = data.get("high_52w", ath_p)
        cached.low_52w = data.get("low_52w", current_p * 0.85)
        cached.last_updated = datetime.utcnow()

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        data["asset_type"] = resolved_asset_type
        data["down_from_ath_pct"] = down_pct
        return data

    def search_assets(self, query: str) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) < 2:
            return []
        # MFAPI search returns scheme codes as symbol_or_code (numeric), not text names
        mf_results = self.mf_provider.search_assets(query)
        etf_results = self.etf_provider.search_assets(query)
        return mf_results + etf_results
