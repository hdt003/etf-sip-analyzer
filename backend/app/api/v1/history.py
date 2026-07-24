from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.analytics_service import AnalyticsService
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(prefix="/history", tags=["Historical Charts"])

@router.get("/{symbol_or_code}")
def get_chart_history(
    symbol_or_code: str,
    timeframe: str = Query("1Y", description="1M, 3M, 6M, 1Y, 5Y, Max"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AnalyticsService(db)
    return service.get_historical_chart(symbol_or_code, timeframe=timeframe, user_id=current_user.id)
