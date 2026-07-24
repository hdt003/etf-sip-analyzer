from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.models.domain import Holding, Transaction
from backend.app.schemas.holding import HoldingCreate, HoldingUpdate

class HoldingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, holding_id: int, user_id: int) -> Optional[Holding]:
        return self.db.query(Holding).filter(Holding.id == holding_id, Holding.user_id == user_id).first()

    def get_all_for_user(self, user_id: int) -> List[Holding]:
        return self.db.query(Holding).filter(Holding.user_id == user_id).all()

    def get_by_symbol(self, symbol_or_code: str, user_id: int) -> Optional[Holding]:
        return self.db.query(Holding).filter(
            Holding.symbol_or_code == symbol_or_code,
            Holding.user_id == user_id
        ).first()

    def create(self, user_id: int, holding_in: HoldingCreate) -> Holding:
        total_inv = float(holding_in.quantity) * float(holding_in.buy_price)
        holding = Holding(
            user_id=user_id,
            asset_type=holding_in.asset_type.upper(),
            symbol_or_code=holding_in.symbol_or_code.strip(),
            name=holding_in.name.strip(),
            quantity=holding_in.quantity,
            buy_price=holding_in.buy_price,
            total_invested=total_inv,
            sip_amount=holding_in.sip_amount,
            sip_date=holding_in.sip_date,
            exchange=holding_in.exchange,
            sector=holding_in.sector,
            amc=holding_in.amc
        )
        self.db.add(holding)
        self.db.commit()
        self.db.refresh(holding)

        # Log initial buy transaction if quantity > 0
        if holding.quantity > 0:
            tx = Transaction(
                user_id=user_id,
                holding_id=holding.id,
                transaction_type="BUY",
                quantity=holding.quantity,
                price_per_unit=holding.buy_price,
                amount=total_inv,
                notes="Initial purchase position"
            )
            self.db.add(tx)
            self.db.commit()

        return holding

    def update(self, holding: Holding, holding_in: HoldingUpdate) -> Holding:
        update_data = holding_in.dict(exclude_unset=True)
        for field, val in update_data.items():
            setattr(holding, field, val)
        holding.total_invested = holding.quantity * holding.buy_price
        self.db.commit()
        self.db.refresh(holding)
        return holding

    def delete(self, holding: Holding) -> bool:
        self.db.delete(holding)
        self.db.commit()
        return True
