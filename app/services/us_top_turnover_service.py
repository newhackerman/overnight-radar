from app.schemas.market import MarketDailyBar, TopTurnoverItem
from app.data_sources.tencent_client import TencentClient
from app.data_sources.yfinance_client import YFinanceClient


class UsTopTurnoverService:
    def __init__(self, tc_client: TencentClient | None = None, yf_client: YFinanceClient | None = None):
        self.tc_client = tc_client or TencentClient()
        self.yf_client = yf_client or YFinanceClient()

    def calculate_top_turnover(self, symbols: list[str], limit: int | None = None) -> list[TopTurnoverItem]:
        bars = self._fetch_bars(symbols)
        valid_bars = [bar for bar in bars if bar.amount is not None]
        valid_bars.sort(key=lambda bar: bar.amount or 0, reverse=True)
        return [self._to_top_item(bar, index + 1) for index, bar in enumerate(valid_bars[:limit])]

    def _fetch_bars(self, symbols: list[str]) -> list[MarketDailyBar]:
        """Try TencentClient first (faster, no rate limit); fall back to YFinance."""
        bars: list[MarketDailyBar] = []
        failed: list[str] = []
        for symbol in symbols:
            try:
                bar = self.tc_client.get_quote(symbol)
                if bar and bar.close_price is not None:
                    bars.append(bar)
                    continue
            except Exception:
                pass
            failed.append(symbol)

        if failed:
            try:
                fallback = self.yf_client.get_daily_bars(failed)
                bars.extend(fallback)
            except Exception:
                pass

        return bars

    @staticmethod
    def _to_top_item(bar: MarketDailyBar, rank_no: int) -> TopTurnoverItem:
        return TopTurnoverItem(
            trade_date=bar.trade_date,
            rank_no=rank_no,
            symbol=bar.symbol,
            name=bar.name,
            close_price=bar.close_price,
            pct_change=bar.pct_change,
            volume=bar.volume,
            amount=bar.amount,
        )
