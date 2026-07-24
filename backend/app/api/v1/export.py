import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.repositories.holding_repository import HoldingRepository
from backend.app.services.market_data.market_data_service import MarketDataService
from backend.app.api.deps import get_current_user
from backend.app.models.domain import User

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/csv")
def export_portfolio_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = HoldingRepository(db)
    market_service = MarketDataService(db)
    holdings = repo.get_all_for_user(current_user.id)

    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Header
    writer.writerow([
        "Asset Type", "Symbol/Scheme Code", "Name", "Exchange",
        "Quantity/Units", "Buy Price / Avg NAV", "Total Invested",
        "Current Price / NAV", "Current Value", "Profit/Loss (INR)", "Profit/Loss (%)",
        "ATH / Peak NAV", "Down from ATH (%)", "SIP Amount"
    ])

    for h in holdings:
        mdata = market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
        cur_p = mdata.get("current_price", h.buy_price)
        ath_p = mdata.get("ath_price", cur_p)
        cur_val = h.quantity * cur_p
        tot_inv = h.quantity * h.buy_price
        profit = cur_val - tot_inv
        profit_pct = (profit / tot_inv * 100.0) if tot_inv > 0 else 0.0
        down_pct = ((ath_p - cur_p) / ath_p * 100.0) if ath_p > 0 else 0.0

        writer.writerow([
            h.asset_type, h.symbol_or_code, h.name, h.exchange,
            h.quantity, h.buy_price, round(tot_inv, 2),
            round(cur_p, 2), round(cur_val, 2), round(profit, 2), round(profit_pct, 2),
            round(ath_p, 2), round(down_pct, 2), h.sip_amount
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=etf_sip_portfolio.csv"}
    )
