import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.domain import Holding, Watchlist, Alert, DailySnapshot, User
from backend.app.services.market_data.market_data_service import MarketDataService

logger = logging.getLogger("scheduler")

class BackgroundSchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def sync_daily_prices(self):
        logger.info("Executing daily market price and snapshot sync...")
        db: Session = SessionLocal()
        try:
            market_service = MarketDataService(db)
            
            # Fetch all distinct holdings and watchlist symbols
            holdings = db.query(Holding).all()
            watchlist = db.query(Watchlist).all()
            
            symbols_to_sync = set()
            for h in holdings:
                symbols_to_sync.add((h.symbol_or_code, h.asset_type))
            for w in watchlist:
                symbols_to_sync.add((w.symbol_or_code, w.asset_type))

            # Force refresh cache for all assets
            for symbol, atype in symbols_to_sync:
                try:
                    market_service.get_market_data(symbol, asset_type=atype, force_refresh=True)
                except Exception as e:
                    logger.error(f"Failed to sync asset {symbol}: {str(e)}")

            # Evaluate threshold alerts
            active_alerts = db.query(Alert).filter(Alert.is_active == True).all()
            for alert in active_alerts:
                mdata = market_service.get_market_data(alert.symbol_or_code, asset_type=alert.asset_type)
                cur_p = mdata.get("current_price", 0.0)
                ath_p = mdata.get("ath_price", cur_p)
                if ath_p > 0:
                    down_pct = ((ath_p - cur_p) / ath_p) * 100.0
                    if down_pct >= alert.drop_percentage:
                        alert.last_triggered_at = datetime.utcnow()
                        logger.info(f"ALERT TRIGGERED: {alert.asset_name} is down {round(down_pct, 1)}% (Threshold: {alert.drop_percentage}%)")

            # Store Daily Snapshots for all active users
            users = db.query(User).all()
            today_date = date.today()
            
            for u in users:
                user_holdings = [h for h in holdings if h.user_id == u.id]
                if not user_holdings:
                    continue

                tot_inv = 0.0
                cur_val = 0.0
                dips = []

                for h in user_holdings:
                    mdata = market_service.get_market_data(h.symbol_or_code, asset_type=h.asset_type)
                    cp = mdata.get("current_price", h.buy_price)
                    ap = mdata.get("ath_price", cp)
                    tot_inv += h.quantity * h.buy_price
                    cur_val += h.quantity * cp
                    if ap > 0:
                        dips.append(max(0.0, ((ap - cp) / ap) * 100.0))

                tot_profit = cur_val - tot_inv
                profit_pct = (tot_profit / tot_inv * 100.0) if tot_inv > 0 else 0.0
                avg_dip = float(sum(dips)/len(dips)) if dips else 0.0

                snapshot = db.query(DailySnapshot).filter(
                    DailySnapshot.user_id == u.id,
                    DailySnapshot.date == today_date
                ).first()

                if not snapshot:
                    snapshot = DailySnapshot(user_id=u.id, date=today_date)
                    db.add(snapshot)

                snapshot.total_invested = round(tot_inv, 2)
                snapshot.current_value = round(cur_val, 2)
                snapshot.total_profit = round(tot_profit, 2)
                snapshot.profit_pct = round(profit_pct, 2)
                snapshot.avg_dip_pct = round(avg_dip, 2)

            db.commit()
            logger.info("Daily market sync completed successfully.")
        except Exception as e:
            logger.error(f"Error in daily sync: {str(e)}")
            db.rollback()
        finally:
            db.close()

    def start(self):
        # Schedule to run every day at 18:30 IST (after Indian market close)
        self.scheduler.add_job(
            self.sync_daily_prices,
            trigger='cron',
            hour=18,
            minute=30,
            id='daily_market_sync',
            replace_existing=True
        )
        self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

scheduler_service = BackgroundSchedulerService()
