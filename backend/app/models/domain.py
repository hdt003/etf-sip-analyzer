from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Date, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    holdings = relationship("Holding", back_populates="user", cascade="all, delete-orphan")
    watchlist = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    snapshots = relationship("DailySnapshot", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)  # 'ETF' or 'MUTUAL_FUND'
    symbol_or_code = Column(String(50), nullable=False, index=True)  # e.g., 'NIFTYBEES.NS' or '122639'
    name = Column(String(255), nullable=False)
    
    # Position details
    quantity = Column(Float, default=0.0)  # Quantity for ETF or Units for MF
    buy_price = Column(Float, default=0.0)  # Buy Price for ETF or Avg NAV for MF
    total_invested = Column(Float, default=0.0)
    
    # SIP details (if applicable)
    sip_amount = Column(Float, default=0.0)
    sip_date = Column(Integer, nullable=True)  # Day of month e.g. 5th, 10th
    
    exchange = Column(String(20), default="NSE")  # NSE or BSE
    sector = Column(String(100), default="General")
    amc = Column(String(100), default="Other")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="holdings")
    transactions = relationship("Transaction", back_populates="holding", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    holding_id = Column(Integer, ForeignKey("holdings.id"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)  # 'BUY', 'SELL', 'SIP'
    quantity = Column(Float, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_date = Column(Date, default=date.today)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    holding = relationship("Holding", back_populates="transactions")

class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)  # 'ETF' or 'MUTUAL_FUND'
    symbol_or_code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="watchlist")
    __table_args__ = (UniqueConstraint('user_id', 'symbol_or_code', name='_user_watchlist_uc'),)

class HistoricalPrice(Base):
    __tablename__ = "historical_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol_or_code = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close_or_nav = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint('symbol_or_code', 'date', name='_asset_date_uc'),)

class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, default=date.today, index=True)
    total_invested = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    profit_pct = Column(Float, default=0.0)
    avg_dip_pct = Column(Float, default=0.0)

    user = relationship("User", back_populates="snapshots")
    __table_args__ = (UniqueConstraint('user_id', 'date', name='_user_snapshot_date_uc'),)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol_or_code = Column(String(50), nullable=False)
    asset_name = Column(String(255), nullable=False)
    asset_type = Column(String(20), nullable=False)
    target_type = Column(String(20), default="ATH_DROP")  # 'ATH_DROP' or 'PEAK_NAV_DROP'
    drop_percentage = Column(Float, nullable=False)  # 5, 10, 15, 20
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")

class PriceCache(Base):
    __tablename__ = "price_cache"

    symbol_or_code = Column(String(50), primary_key=True, index=True)
    asset_name = Column(String(255), nullable=False)
    asset_type = Column(String(20), nullable=False)
    current_price = Column(Float, nullable=False, default=0.0)
    ath_price = Column(Float, nullable=False, default=0.0)
    ath_date = Column(Date, nullable=True)
    down_from_ath_pct = Column(Float, nullable=False, default=0.0)
    high_52w = Column(Float, nullable=True)
    low_52w = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    buy_score = Column(Integer, default=50)
    buy_recommendation = Column(String(50), default="Hold")
    score_reasons = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ETFMaster(Base):
    __tablename__ = "etf_master"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    exchange = Column(String(20), default="NSE")
    sector = Column(String(100), default="Broad Market")
    amc = Column(String(100), default="Nippon India")

class MutualFundMaster(Base):
    __tablename__ = "mutual_fund_master"

    id = Column(Integer, primary_key=True, index=True)
    scheme_code = Column(String(50), unique=True, index=True, nullable=False)
    scheme_name = Column(String(255), nullable=False)
    category = Column(String(100), default="Equity")
    amc = Column(String(100), default="Direct Plan")
