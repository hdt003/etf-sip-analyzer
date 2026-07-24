import pytest
from backend.app.services.buy_score_service import BuyScoreService

def test_buy_score_strong_buy():
    # Down 20% from ATH (250 vs 200), near 52W low
    current_p = 200.0
    ath_p = 250.0
    low_52w = 195.0
    high_52w = 250.0
    history = [{"close": 200.0 + (i % 5)} for i in range(30)]

    score, rec, reasons = BuyScoreService.calculate_buy_score(
        current_p, ath_p, low_52w, high_52w, history
    )

    assert score >= 70
    assert rec in ["Strong Buy", "Buy"]
    assert any("below ATH" in r for r in reasons)

def test_buy_score_avoid():
    # At ATH (250 vs 250), at 52W high
    current_p = 250.0
    ath_p = 250.0
    low_52w = 150.0
    high_52w = 250.0
    history = [{"close": 250.0} for _ in range(30)]

    score, rec, reasons = BuyScoreService.calculate_buy_score(
        current_p, ath_p, low_52w, high_52w, history
    )

    assert score < 60
    assert rec in ["Hold", "Avoid"]
