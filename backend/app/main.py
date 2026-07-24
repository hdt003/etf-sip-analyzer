import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.api.v1 import auth, holdings, portfolio, prices, alerts, watchlist, history, search, calculators, export
from backend.app.services.scheduler_service import scheduler_service
from backend.app.services.market_data.market_data_service import MarketDataService
from backend.app.repositories.holding_repository import HoldingRepository
from backend.app.core.database import SessionLocal

# Create database tables automatically if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade Quantitative Fintech Web App for Indian Mutual Funds (SIPs) and ETFs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files and Templates
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "static")
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Include API V1 Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(holdings.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(watchlist.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(calculators.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")

@app.on_event("startup")
def startup_event():
    if settings.ENABLE_SCHEDULER:
        try:
            scheduler_service.start()
        except Exception:
            pass

    # Populate initial sample holdings for demo user if DB is empty
    db = SessionLocal()
    try:
        from backend.app.repositories.user_repository import UserRepository
        from backend.app.schemas.user import UserCreate
        from backend.app.schemas.holding import HoldingCreate

        user_repo = UserRepository(db)
        demo_user = user_repo.get_by_email("demo@investor.in")
        if not demo_user:
            demo_user = user_repo.create(UserCreate(
                email="demo@investor.in",
                password="demopassword123",
                full_name="Quantitative Investor"
            ))

        holding_repo = HoldingRepository(db)
        user_holdings = holding_repo.get_all_for_user(demo_user.id)
        if not user_holdings:
            # Seed initial popular sample portfolio: requested Mutual Funds & ETFs
            funds = [
                ("ETF", "HDFCSILVER.NS", "HDFC Silver ETF", "NSE", "Commodities", "HDFC Mutual Fund"),
                ("ETF", "METALIETF.NS", "ICICI Prudential Nifty Metal ETF", "NSE", "Thematic", "ICICI Prudential Mutual Fund"),
                ("ETF", "GOLDETF.NS", "Mirae Asset Gold ETF", "NSE", "Commodities", "Mirae Asset Mutual Fund"),
                ("ETF", "MON100.NS", "Motilal Oswal NASDAQ 100 ETF", "NSE", "International", "Motilal Oswal Mutual Fund"),
                ("ETF", "GROWWPOWER.NS", "Groww BSE Power ETF", "NSE", "Thematic", "Groww Mutual Fund"),
                ("ETF", "MOCAPITAL.NS", "Motilal Oswal Nifty Capital Market ETF", "NSE", "Thematic", "Motilal Oswal Mutual Fund"),
                ("ETF", "MASPTOP50.NS", "Mirae Asset S&P 500 Top 50 ETF", "NSE", "International", "Mirae Asset Mutual Fund"),
                ("ETF", "VAL30IETF.NS", "ICICI Prudential Nifty200 Value 30 ETF", "NSE", "Factor / Value", "ICICI Prudential Mutual Fund"),
                ("MUTUAL_FUND", "125494", "SBI Small Cap Fund - Regular Plan - Growth", "MFAPI", "Small Cap", "SBI Mutual Fund"),
                ("MUTUAL_FUND", "144548", "Tata Flexi Cap Fund - Regular Plan - Growth", "MFAPI", "Flexi Cap", "Tata Mutual Fund"),
                ("MUTUAL_FUND", "118955", "HDFC Flexi Cap Fund - Direct Plan - Growth", "MFAPI", "Flexi Cap", "HDFC Mutual Fund"),
                ("MUTUAL_FUND", "147844", "Aditya Birla Sun Life PSU Equity Fund - Direct - Growth", "MFAPI", "Thematic", "Aditya Birla Sun Life Mutual Fund"),
                ("MUTUAL_FUND", "147946", "Bandhan Small Cap Fund - Direct Plan - Growth", "MFAPI", "Small Cap", "Bandhan Mutual Fund"),
                ("MUTUAL_FUND", "140228", "Edelweiss Mid Cap Fund - Direct Plan - Growth", "MFAPI", "Mid Cap", "Edelweiss Mutual Fund"),
                ("MUTUAL_FUND", "147701", "Motilal Oswal Large and Midcap Fund - Regular Plan - Growth", "MFAPI", "Large & Mid Cap", "Motilal Oswal Mutual Fund")
            ]
            for asset_type, sym, name, exch, sec, amc in funds:
                holding_repo.create(demo_user.id, HoldingCreate(
                    asset_type=asset_type,
                    symbol_or_code=sym,
                    name=name,
                    quantity=100.0,
                    buy_price=50.0,
                    sip_amount=0.0,
                    exchange=exch,
                    sector=sec,
                    amc=amc
                ))
    except Exception as e:
        db.rollback()
    finally:
        db.close()

@app.on_event("shutdown")
def shutdown_event():
    scheduler_service.stop()

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"app_name": settings.APP_NAME})
