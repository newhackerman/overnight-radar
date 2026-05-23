from datetime import date, timedelta
import logging

import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.data_sources.tencent_client import TencentClient
from app.models.tables import BacktestResult, UsCnMappingHistory
from app.config import get_settings

logger = logging.getLogger(__name__)

# Trading days offset for each return period
RETURN_PERIODS = {"t1_return": 1, "t3_return": 3, "t5_return": 5, "t10_return": 10}


class BacktestService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def run(self, event_date: date, force: bool = False) -> list[dict]:
        """Run backtest for mappings on event_date, computing A-share returns.

        If cached results exist and are complete (T+10 filled), return them directly.
        Use force=True to always refresh from market data.
        """
        stmt = (
            select(UsCnMappingHistory)
            .where(UsCnMappingHistory.report_date == event_date)
            .order_by(UsCnMappingHistory.created_at.desc())
        )
        mappings = list(self.db.scalars(stmt).all())
        if not mappings:
            return []

        # Check if we can use cached results
        if not force:
            cached = self._load_cached_results(event_date, mappings)
            if cached is not None:
                return cached

        tencent = TencentClient()
        results: list[dict] = []

        # Collect unique CN symbols for batch historical fetch
        cn_symbols = list({m.cn_symbol for m in mappings if m.cn_symbol})
        history_cache = self._fetch_cn_history(cn_symbols, event_date)

        for m in mappings:
            if not m.cn_symbol:
                continue

            quote = tencent.get_quote(m.cn_symbol)
            if not quote or not quote.close_price or not quote.prev_close:
                results.append(self._row(m, t_return=None))
                continue

            t_return = (quote.close_price - quote.prev_close) / quote.prev_close * 100 if quote.prev_close else None

            # Compute multi-day returns from historical data
            multi_returns = self._compute_multi_day_returns(m.cn_symbol, event_date, history_cache)

            existing = self.db.scalar(
                select(BacktestResult).where(
                    BacktestResult.event_date == event_date,
                    BacktestResult.us_symbol == m.us_symbol,
                    BacktestResult.cn_symbol == m.cn_symbol,
                )
            )
            if existing:
                existing.t_return = t_return
                existing.cn_trade_date = quote.trade_date
                existing.t1_return = multi_returns.get("t1_return")
                existing.t3_return = multi_returns.get("t3_return")
                existing.t5_return = multi_returns.get("t5_return")
                existing.t10_return = multi_returns.get("t10_return")
                existing.current_return = multi_returns.get("current_return")
            else:
                self.db.add(BacktestResult(
                    event_date=event_date,
                    cn_trade_date=quote.trade_date,
                    us_symbol=m.us_symbol,
                    cn_symbol=m.cn_symbol,
                    t_return=t_return,
                    t1_return=multi_returns.get("t1_return"),
                    t3_return=multi_returns.get("t3_return"),
                    t5_return=multi_returns.get("t5_return"),
                    t10_return=multi_returns.get("t10_return"),
                    current_return=multi_returns.get("current_return"),
                ))
            self.db.flush()
            results.append(self._row(m, t_return=t_return, **multi_returns))

        self.db.commit()
        return results

    def _load_cached_results(self, event_date: date, mappings: list) -> list[dict] | None:
        """Return cached backtest results if they exist and are sufficiently complete.

        Returns None if cache is missing or incomplete (needs refresh).
        Complete means: T+10 data is filled OR event is too recent (< 3 calendar days).
        For intermediate dates, check individual period completeness based on elapsed days.
        """
        cached_rows = list(self.db.scalars(
            select(BacktestResult).where(BacktestResult.event_date == event_date)
        ).all())

        if not cached_rows:
            return None

        days_since = (date.today() - event_date).days

        # Rough mapping: calendar days needed to have enough trading days for each period
        # (weekends + potential holidays considered)
        PERIOD_MIN_DAYS = {
            "t1_return": 3,
            "t3_return": 7,
            "t5_return": 12,
            "t10_return": 18,
        }

        if days_since > 15:
            # All periods should be filled
            complete = all(r.t10_return is not None for r in cached_rows)
            if not complete:
                return None  # Need refresh to fill missing periods
        elif days_since >= 3:
            # Check each period: if enough time has passed but data is missing, refresh
            for field, min_days in PERIOD_MIN_DAYS.items():
                if days_since >= min_days:
                    if any(getattr(r, field) is None for r in cached_rows):
                        return None

        # Build result dicts from cached data, joining with mapping info
        mapping_lookup = {}
        for m in mappings:
            if m.cn_symbol:
                mapping_lookup[(m.us_symbol, m.cn_symbol)] = m

        results = []
        for r in cached_rows:
            m = mapping_lookup.get((r.us_symbol, r.cn_symbol))
            if not m:
                continue
            results.append(self._row(
                m,
                t_return=float(r.t_return) if r.t_return is not None else None,
                t1_return=float(r.t1_return) if r.t1_return is not None else None,
                t3_return=float(r.t3_return) if r.t3_return is not None else None,
                t5_return=float(r.t5_return) if r.t5_return is not None else None,
                t10_return=float(r.t10_return) if r.t10_return is not None else None,
                current_return=float(r.current_return) if r.current_return is not None else None,
            ))

        logger.info("Using cached backtest for %s (%d rows)", event_date, len(results))
        return results

    def _fetch_cn_history(self, cn_symbols: list[str], event_date: date) -> dict[str, pd.DataFrame]:
        """Fetch historical price data for CN symbols using yfinance.

        CN A-share symbols need suffix: 6xxxxx -> .SS (Shanghai), others -> .SZ (Shenzhen).
        """
        cache: dict[str, pd.DataFrame] = {}
        for symbol in cn_symbols:
            yf_symbol = self._to_yf_cn_symbol(symbol)
            if not yf_symbol:
                continue
            try:
                ticker = yf.Ticker(yf_symbol)
                # Fetch enough history to cover T+10 trading days after event_date
                start = event_date - timedelta(days=5)
                end = event_date + timedelta(days=self.settings.backtest_history_days)
                hist = ticker.history(start=start, end=end, auto_adjust=False)
                if not hist.empty:
                    hist = hist.reset_index()
                    hist["DateOnly"] = pd.to_datetime(hist["Date"]).dt.date
                    cache[symbol] = hist
            except Exception as exc:
                logger.debug("Failed to fetch CN history for %s: %s", symbol, exc)
        return cache

    def _compute_multi_day_returns(
        self, cn_symbol: str, event_date: date, history_cache: dict[str, pd.DataFrame]
    ) -> dict:
        """Compute T+1/3/5/10 and current returns relative to event_date close."""
        result: dict = {}
        hist = history_cache.get(cn_symbol)
        if hist is None or hist.empty:
            return result

        # Find the base close price: the close on event_date (T day)
        t_day_rows = hist[hist["DateOnly"] == event_date]
        if t_day_rows.empty:
            # Try the first trading day after event_date as base
            after_event = hist[hist["DateOnly"] > event_date].sort_values("DateOnly")
            if after_event.empty:
                return result
            base_close = float(after_event.iloc[0]["Close"])
            base_date = after_event.iloc[0]["DateOnly"]
        else:
            base_close = float(t_day_rows.iloc[-1]["Close"])
            base_date = event_date

        if base_close <= 0:
            return result

        # Get trading days after base_date
        future_days = hist[hist["DateOnly"] > base_date].sort_values("DateOnly")
        if future_days.empty:
            return result

        for field, offset in RETURN_PERIODS.items():
            if len(future_days) >= offset:
                target_close = float(future_days.iloc[offset - 1]["Close"])
                result[field] = round((target_close - base_close) / base_close * 100, 4)

        # current_return: use the latest available close
        latest_close = float(future_days.iloc[-1]["Close"])
        result["current_return"] = round((latest_close - base_close) / base_close * 100, 4)

        return result

    @staticmethod
    def _to_yf_cn_symbol(symbol: str) -> str | None:
        """Convert CN symbol to yfinance format (e.g. 600519 -> 600519.SS)."""
        raw = symbol.strip().upper()
        # Remove existing suffix if present
        if "." in raw:
            raw = raw.split(".")[0]
        if not raw.isdigit() or len(raw) != 6:
            return None
        if raw.startswith("6"):
            return f"{raw}.SS"
        elif raw.startswith(("0", "3")):
            return f"{raw}.SZ"
        elif raw.startswith(("4", "8")):
            return f"{raw}.BJ"
        return None

    @staticmethod
    def _row(m: UsCnMappingHistory, **overrides) -> dict:
        base = {
            "us_symbol": m.us_symbol,
            "cn_symbol": m.cn_symbol or "",
            "cn_name": m.cn_name or "",
            "theme": m.theme or "",
            "impact_direction": m.impact_direction or "",
            "impact_strength": m.impact_strength or 0,
            "confidence": float(m.confidence) if m.confidence is not None else None,
            "t1_return": None,
            "t3_return": None,
            "t5_return": None,
            "t10_return": None,
            "current_return": None,
        }
        base.update(overrides)
        return base
