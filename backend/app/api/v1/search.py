from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.market_data.market_data_service import MarketDataService

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("")
def search_assets(
    q: str = Query(..., min_length=2, description="Search symbol, scheme code or asset name"),
    db: Session = Depends(get_db)
):
    service = MarketDataService(db)
    return service.search_assets(q)
