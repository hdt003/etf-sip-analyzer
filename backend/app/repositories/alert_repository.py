from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.app.models.domain import Alert
from backend.app.schemas.alert import AlertCreate

class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_for_user(self, user_id: int) -> List[Alert]:
        return self.db.query(Alert).filter(Alert.user_id == user_id).all()

    def get_active_alerts(self) -> List[Alert]:
        return self.db.query(Alert).filter(Alert.is_active == True).all()

    def create(self, user_id: int, alert_in: AlertCreate) -> Alert:
        alert = Alert(
            user_id=user_id,
            symbol_or_code=alert_in.symbol_or_code.strip(),
            asset_name=alert_in.asset_name.strip(),
            asset_type=alert_in.asset_type.upper(),
            target_type=alert_in.target_type,
            drop_percentage=alert_in.drop_percentage,
            is_active=True
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def toggle_active(self, alert_id: int, user_id: int) -> Optional[Alert]:
        alert = self.db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user_id).first()
        if alert:
            alert.is_active = not alert.is_active
            self.db.commit()
            self.db.refresh(alert)
        return alert

    def delete(self, alert_id: int, user_id: int) -> bool:
        alert = self.db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user_id).first()
        if alert:
            self.db.delete(alert)
            self.db.commit()
            return True
        return False

    def mark_triggered(self, alert_id: int):
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.last_triggered_at = datetime.utcnow()
            self.db.commit()
