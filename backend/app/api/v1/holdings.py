from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.core.database import get_db
from backend.app.schemas.holding import HoldingCreate, HoldingUpdate, HoldingResponse
from backend.app.repositories.holding_repository import HoldingRepository
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(prefix="/holdings", tags=["Holdings"])


@router.get("", response_model=List[HoldingResponse])
def get_holdings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = HoldingRepository(db)
    holdings = repo.get_all_for_user(current_user.id)
    results = []
    for h in holdings:
        results.append(HoldingResponse(
            id=h.id, user_id=h.user_id, asset_type=h.asset_type,
            symbol_or_code=h.symbol_or_code, name=h.name,
            quantity=h.quantity, buy_price=h.buy_price,
            total_invested=h.total_invested, sip_amount=h.sip_amount,
            sip_date=h.sip_date, exchange=h.exchange, sector=h.sector, amc=h.amc,
            current_price=h.buy_price, current_value=h.quantity * h.buy_price,
            gain_loss=0.0, gain_loss_pct=0.0,
            ath_price=h.buy_price, down_from_ath_pct=0.0,
            buy_score=50, buy_recommendation="Hold",
            created_at=h.created_at, updated_at=h.updated_at,
        ))
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def create_holding(
    # Accept BOTH form-encoded (HTMX) and JSON body via Form parameters
    symbol_or_code: str = Form(...),
    name: str = Form(""),
    asset_type: str = Form("MUTUAL_FUND"),
    quantity: float = Form(100.0),
    buy_price: float = Form(50.0),
    sip_amount: Optional[float] = Form(0.0),
    exchange: Optional[str] = Form("MFAPI"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a Mutual Fund or ETF to the watch/peak analysis table.
    Called from the HTMX form on the frontend.
    """
    repo = HoldingRepository(db)

    # Deduplicate: don't add same symbol twice for same user
    existing = repo.get_all_for_user(current_user.id)
    for h in existing:
        if h.symbol_or_code.strip() == symbol_or_code.strip():
            return {"message": "Already tracked", "id": h.id, "symbol_or_code": h.symbol_or_code}

    holding_in = HoldingCreate(
        asset_type=asset_type,
        symbol_or_code=symbol_or_code.strip(),
        name=name.strip() or symbol_or_code.strip(),
        quantity=quantity,
        buy_price=buy_price,
        sip_amount=sip_amount or 0.0,
        exchange=exchange or "MFAPI",
    )
    h = repo.create(current_user.id, holding_in)
    return {"message": "Added successfully", "id": h.id, "symbol_or_code": h.symbol_or_code, "name": h.name}


@router.delete("/{holding_id}")
def delete_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = HoldingRepository(db)
    h = repo.get_by_id(holding_id, current_user.id)
    if not h:
        raise HTTPException(status_code=404, detail="Holding not found")
    repo.delete(h)
    return {"message": "Removed from watch table"}
