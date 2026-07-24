from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.market_data.market_data_service import MarketDataService
from backend.app.services.buy_score_service import BuyScoreService

router = APIRouter(prefix="/prices", tags=["Market Data & Prices"])


@router.get("/{symbol_or_code}")
def get_price_details(
    symbol_or_code: str,
    asset_type: str = Query(None, description="ETF or MUTUAL_FUND"),
    db: Session = Depends(get_db)
):
    service = MarketDataService(db)
    try:
        return service.get_market_data(symbol_or_code, asset_type=asset_type, force_refresh=True)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/analyze/{symbol_or_code}")
def analyze_asset_on_the_fly(
    symbol_or_code: str,
    db: Session = Depends(get_db),
):
    """
    Analyze any Mutual Fund or ETF by:
      - Numeric input  → treated as MFAPI scheme code directly
      - Text input     → searched against MFAPI first, then resolved to scheme code
    Always returns REAL data from MFAPI / Yahoo Finance — never mock data.
    """
    service = MarketDataService(db)
    input_clean = symbol_or_code.strip()

    # Step 1: If it's not a numeric code, search MFAPI for the best match
    resolved_code = input_clean
    resolved_asset_type = None

    if not input_clean.isdigit():
        # Try MFAPI search first (covers Mutual Funds by name)
        mf_results = service.mf_provider.search_assets(input_clean)
        if mf_results:
            resolved_code = mf_results[0]["symbol_or_code"]   # Top match numeric code
            resolved_asset_type = "MUTUAL_FUND"
        else:
            # Fall back to ETF (yfinance) with the original symbol
            resolved_asset_type = "ETF"

    # Step 2: Fetch real market data
    try:
        mdata = service.get_market_data(resolved_code, asset_type=resolved_asset_type, force_refresh=True)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch real data for '{symbol_or_code}': {e}"
        )

    cur_p = mdata.get("current_price", 0.0)
    ath_p = mdata.get("ath_price", cur_p)

    if cur_p <= 0 or ath_p <= 0:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid price data returned for '{symbol_or_code}'. Verify the scheme code."
        )

    down_pct = round(((ath_p - cur_p) / ath_p * 100.0), 2) if ath_p > 0 else 0.0

    if down_pct <= 5.0:
        color_status = "Green"
    elif down_pct <= 15.0:
        color_status = "Yellow"
    else:
        color_status = "Red"

    history = mdata.get("history", [])
    resolved_type = mdata.get("asset_type", resolved_asset_type or "MUTUAL_FUND")
    b_score, b_rec, b_reasons = BuyScoreService.calculate_buy_score(
        cur_p, ath_p,
        mdata.get("low_52w", cur_p * 0.85),
        mdata.get("high_52w", ath_p),
        history,
        asset_type=resolved_type
    )

    return {
        "symbol_or_code": mdata.get("symbol_or_code", resolved_code),
        "name": mdata.get("name", resolved_code),
        "asset_type": mdata.get("asset_type", resolved_asset_type or "MUTUAL_FUND"),
        "current_price": round(cur_p, 4),
        "ath_or_peak_nav": round(ath_p, 4),
        "ath_date": mdata.get("ath_date"),
        "down_pct": down_pct,
        "color_status": color_status,
        "buy_score": b_score,
        "buy_recommendation": b_rec,
        "score_reasons": ", ".join(b_reasons),
        "history_count": len(history),
        "data_source": "MFAPI" if (mdata.get("asset_type") == "MUTUAL_FUND") else "Yahoo Finance",
    }
