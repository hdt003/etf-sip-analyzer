from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, verify_password
from backend.app.schemas.user import UserCreate, UserResponse, LoginRequest, Token
from backend.app.repositories.user_repository import UserRepository
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    existing = repo.get_by_email(user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = repo.create(user_in)
    access_token = create_access_token(data={"sub": user.email, "id": user.id})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.from_orm(user))

@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": user.email, "id": user.id})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.from_orm(user))

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)

@router.post("/logout")
def logout():
    return {"message": "Successfully logged out"}
