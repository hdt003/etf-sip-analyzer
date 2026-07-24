from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.core.exceptions import UnauthorizedException
from backend.app.models.domain import User
from backend.app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not token:
        # For demo/seamless usage if unauthenticated, return default demo user or raise 401
        user_repo = UserRepository(db)
        demo_user = user_repo.get_by_email("demo@investor.in")
        if not demo_user:
            from backend.app.schemas.user import UserCreate
            demo_user = user_repo.create(UserCreate(
                email="demo@investor.in",
                password="demopassword123",
                full_name="Quantitative Investor"
            ))
        return demo_user

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedException("Invalid authentication credentials")

    user_repo = UserRepository(db)
    user = user_repo.get_by_email(payload["sub"])
    if not user:
        raise UnauthorizedException("User not found")
    
    return user
