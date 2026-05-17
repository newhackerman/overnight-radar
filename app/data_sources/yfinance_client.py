from datetime import date
import pandas as pd
import yfinance as yf
from app.config import get_settings
from app.schemas.market import MarketDailyBar


class YFinanceClient:
    source = "yfinance"

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_daily_bar(self, symbol: str, trade_date: date | None = None) -> MarketDailyBar | None:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=self.settings.yfinance_period, auto_adjust=False)
        if hist.empty:
            return None

        hist = hist.reset_index()
        hist["DateOnly"] = pd.to_datetime(hist["Date"]).dt.date
        if trade_date:
            rows = hist[hist["DateOnly"] == trade_date]
            if rows.empty:
                return None
            row = rows.iloc[-1]
            prev_rows = hist[hist["DateOnly"] < trade_date]
            prev_close = float(prev_rows.iloc[-1]["Close"]) if not prev_rows.empty else None
        else:
            row = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else None

        close = float(row["Close"])
        volume = int(row["Volume"])
        pct_change = ((close - prev_close) / prev_close * 100) if prev_close else None

        info = {}
        try:
            info = ticker.fast_info or {}
        except Exception:
            info = {}

        return MarketDailyBar(
            trade_date=row["DateOnly"],
            symbol=symbol.upper(),
            name=None,
            close_price=close,
            prev_close=prev_close,
            pct_change=pct_change,
            volume=volume,
            amount=close * volume,
            market_cap=float(info.get("market_cap")) if info.get("market_cap") else None,
            source=self.source,
        )

    def get_daily_bars(self, symbols: list[str], trade_date: date | None = None) -> list[MarketDailyBar]:
        bars: list[MarketDailyBar] = []
        for symbol in symbols:
            try:
                bar = self.get_daily_bar(symbol, trade_date)
            except Exception:
                bar = None
            if bar:
                bars.append(bar)
        return bars
