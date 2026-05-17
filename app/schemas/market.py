from datetime import date
from pydantic import BaseModel, Field


class MarketDailyBar(BaseModel):
    trade_date: date
    symbol: str = Field(max_length=32)
    name: str | None = Field(default=None, max_length=128)
    close_price: float | None = None
    prev_close: float | None = None
    pct_change: float | None = None
    volume: int | None = None
    amount: float | None = None
    market_cap: float | None = None
    sector: str | None = None
    source: str


class TopTurnoverItem(BaseModel):
    trade_date: date
    rank_no: int
    symbol: str
    name: str | None = None
    close_price: float | None = None
    pct_change: float | None = None
    volume: int | None = None
    amount: float | None = None
