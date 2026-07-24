from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.sip_tracker_service import SipTrackerService
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(tags=["Portfolio & Dashboard"])

@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AnalyticsService(db)
    return service.get_dashboard_summary(current_user.id)

@router.get("/peak-analysis")
def get_peak_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AnalyticsService(db)
    return service.get_peak_analysis(current_user.id)

@router.get("/portfolio/allocations")
def get_allocations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AnalyticsService(db)
    return service.get_allocation_breakdown(current_user.id)

@router.get("/portfolio/sip-summary")
def get_sip_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = SipTrackerService(db)
    return service.get_sip_summary(current_user.id)

@router.get("/portfolio/statistics/{holding_id}")
def get_holding_statistics(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AnalyticsService(db)
    try:
        return service.get_holding_statistics(holding_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
