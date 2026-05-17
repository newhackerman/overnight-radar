import json
import logging
from functools import lru_cache
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Default US stock symbols for tracking — covers major tech, semis, EV, China ADR, finance, energy
DEFAULT_US_SYMBOLS_LIST = [
    # Big Tech
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX",
    # Semiconductors
    "AMD", "MU", "INTC", "AVGO", "QCOM", "SMCI", "ASML", "AMAT",
    # AI / Software
    "PLTR", "ORCL", "CRM", "SNOW",
    # Crypto-related
    "COIN", "MSTR",
    # China ADR
    "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI",
    # Finance
    "JPM", "GS",
    # Energy
    "XOM",
]


class Settings(BaseSettings):
    app_name: str = "Overnight Radar"
    app_env: str = "development"
    debug: bool = False
    secret_key: SecretStr = Field(default=SecretStr("change-me-in-env"))
    admin_username: str = "admin"
    admin_password_hash: SecretStr = Field(default=SecretStr(""))

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "overnight_radar"
    mysql_password: SecretStr = Field(default=SecretStr(""))
    mysql_database: str = "overnight_radar"

    # AI settings
    ai_api_key: SecretStr = Field(default=SecretStr(""))
    ai_base_url: str = ""
    ai_model: str = "claude-sonnet-4-6"
    ai_temperature: float = 0.2
    ai_timeout_seconds: float = 90.0

    # Push settings
    wecom_webhook: SecretStr = Field(default=SecretStr(""))
    wecom_max_bytes: int = 4096

    # Scheduler
    daily_job_time: str = "06:00"
    daily_push_time: str = "08:00"

    # Data fetching
    request_timeout_seconds: float = 15.0
    yfinance_period: str = "15d"

    # Report settings
    us_symbols_json: str = ""  # JSON array override, e.g. '["NVDA","TSLA"]'
    top_turnover_limit: int = 50
    report_max_items: int = 20

    # Backtest
    max_backtest_days: int = 3650
    backtest_history_days: int = 30  # Days of CN history to fetch for multi-day returns

    # Session
    session_max_age_seconds: int = 86400 * 7  # 7 days
    login_max_attempts: int = 5
    login_window_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def _check_secret_key_in_production(self):
        if self.app_env != "development" and self.secret_key.get_secret_value() == "change-me-in-env":
            raise ValueError("SECRET_KEY must be set to a secure value in non-development environments")
        return self

    @property
    def us_symbols(self) -> list[str]:
        """Return configured US symbols list. Supports override via US_SYMBOLS_JSON env var."""
        if self.us_symbols_json:
            try:
                symbols = json.loads(self.us_symbols_json)
                if isinstance(symbols, list) and all(isinstance(s, str) for s in symbols):
                    return symbols
            except (json.JSONDecodeError, TypeError):
                logger.warning("Invalid US_SYMBOLS_JSON, using defaults")
        return DEFAULT_US_SYMBOLS_LIST

    @property
    def database_url(self) -> str:
        password = self.mysql_password.get_secret_value()
        return (
            f"mysql+pymysql://{self.mysql_user}:{password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
