from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.schemas.watchlist import WatchlistCreate, WatchlistResponse
from backend.app.repositories.watchlist_repository import WatchlistRepository
from backend.app.services.market_data.market_data_service import MarketDataService
from backend.app.services.buy_score_service import BuyScoreService
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

@router.get("", response_model=List[WatchlistResponse])
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = WatchlistRepository(db)
    market_service = MarketDataService(db)
    items = repo.get_all_for_user(current_user.id)
    
    responses = []
    for item in items:
        mdata = market_service.get_market_data(item.symbol_or_code, asset_type=item.asset_type)
        cur_p = mdata.get("current_price", 0.0)
        ath_p = mdata.get("ath_price", cur_p)
        
        down_pct = 0.0
        if ath_p > 0:
            down_pct = max(0.0, round(((ath_p - cur_p) / ath_p) * 100.0, 2))

        history = mdata.get("history", [])
        b_score, b_rec, _ = BuyScoreService.calculate_buy_score(
            cur_p, ath_p, mdata.get("low_52w", cur_p*0.85), mdata.get("high_52w", ath_p), history
        )

        responses.append(WatchlistResponse(
            id=item.id,
            user_id=item.user_id,
            asset_type=item.asset_type,
            symbol_or_code=item.symbol_or_code,
            name=item.name,
            current_price=round(cur_p, 2),
            ath_price=round(ath_p, 2),
            down_from_ath_pct=down_pct,
            buy_score=b_score,
            buy_recommendation=b_rec,
            created_at=item.created_at
        ))

    return responses

@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    item_in: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = WatchlistRepository(db)
    item = repo.create(current_user.id, item_in)
    
    market_service = MarketDataService(db)
    mdata = market_service.get_market_data(item.symbol_or_code, asset_type=item.asset_type)
    cur_p = mdata.get("current_price", 0.0)
    ath_p = mdata.get("ath_price", cur_p)
    
    down_pct = round(((ath_p - cur_p) / ath_p * 100.0), 2) if ath_p > 0 else 0.0

    return WatchlistResponse(
        id=item.id,
        user_id=item.user_id,
        asset_type=item.asset_type,
        symbol_or_code=item.symbol_or_code,
        name=item.name,
        current_price=round(cur_p, 2),
        ath_price=round(ath_p, 2),
        down_from_ath_pct=down_pct,
        buy_score=50,
        buy_recommendation="Hold",
        created_at=item.created_at
    )

@router.delete("/{watchlist_id}")
def remove_from_watchlist(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = WatchlistRepository(db)
    success = repo.delete(watchlist_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"message": "Removed from watchlist"}
