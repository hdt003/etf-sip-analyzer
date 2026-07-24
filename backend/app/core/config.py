from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Buy the Dip Dashboard - Indian Mutual Funds & ETFs"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    SECRET_KEY: str = "super-secret-jwt-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    # SQLite default, PostgreSQL for Supabase production
    DATABASE_URL: str = "sqlite:///./etf_sip_analyzer.db"
    
    ENABLE_SCHEDULER: bool = True
    DAILY_SYNC_HOUR: int = 18
    DAILY_SYNC_MINUTE: int = 30
    
    CORS_ORIGINS: str = "*"

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
