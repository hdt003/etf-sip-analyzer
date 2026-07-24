from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.models.domain import Watchlist
from backend.app.schemas.watchlist import WatchlistCreate

class WatchlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_for_user(self, user_id: int) -> List[Watchlist]:
        return self.db.query(Watchlist).filter(Watchlist.user_id == user_id).all()

    def get_by_symbol(self, symbol_or_code: str, user_id: int) -> Optional[Watchlist]:
        return self.db.query(Watchlist).filter(
            Watchlist.symbol_or_code == symbol_or_code,
            Watchlist.user_id == user_id
        ).first()

    def create(self, user_id: int, item_in: WatchlistCreate) -> Watchlist:
        item = Watchlist(
            user_id=user_id,
            asset_type=item_in.asset_type.upper(),
            symbol_or_code=item_in.symbol_or_code.strip(),
            name=item_in.name.strip()
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item_id: int, user_id: int) -> bool:
        item = self.db.query(Watchlist).filter(Watchlist.id == item_id, Watchlist.user_id == user_id).first()
        if item:
            self.db.delete(item)
            self.db.commit()
            return True
        return False
