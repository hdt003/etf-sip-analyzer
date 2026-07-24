from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.schemas.alert import AlertCreate, AlertResponse
from backend.app.repositories.alert_repository import AlertRepository
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = AlertRepository(db)
    return repo.get_all_for_user(current_user.id)

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert_in: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = AlertRepository(db)
    return repo.create(current_user.id, alert_in)

@router.put("/{alert_id}/toggle", response_model=AlertResponse)
def toggle_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = AlertRepository(db)
    alert = repo.toggle_active(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = AlertRepository(db)
    success = repo.delete(alert_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert deleted successfully"}
