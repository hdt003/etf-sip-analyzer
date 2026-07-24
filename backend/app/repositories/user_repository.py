from sqlalchemy.orm import Session
from typing import Optional
from backend.app.models.domain import User
from backend.app.schemas.user import UserCreate
from backend.app.core.security import hash_password

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower().strip()).first()

    def create(self, user_in: UserCreate) -> User:
        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
