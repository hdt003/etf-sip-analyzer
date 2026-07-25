from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.v1 import prices


class DummyMarketDataService:
    def __init__(self, db):
        self.db = db
        self.mf_provider = type(
            "DummyMFProvider",
            (),
            {"search_assets": staticmethod(lambda query: [])},
        )()

    def get_market_data(self, symbol_or_code, asset_type=None, force_refresh=False):
        return {
            "symbol_or_code": symbol_or_code,
            "name": "Sample Fund",
            "asset_type": "MUTUAL_FUND",
            "current_price": 123.45,
            "ath_price": 130.0,
            "today_change_pct": 1.75,
            "low_52w": 110.0,
            "high_52w": 130.0,
            "history": [{"date": "2026-07-24", "close": 121.32}],
        }


client = TestClient(app)


def test_analyze_endpoint_includes_today_change_pct(monkeypatch):
    monkeypatch.setattr(prices, "MarketDataService", DummyMarketDataService)

    response = client.get("/api/v1/prices/analyze/123456")

    assert response.status_code == 200
    payload = response.json()
    assert payload["today_change_pct"] == 1.75
    assert payload["ath_or_peak_nav"] == 130.0
