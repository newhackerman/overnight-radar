from datetime import date
import httpx
from app.config import get_settings
from app.schemas.market import MarketDailyBar
from app.utils.tz import today_cst


class TencentClient:
    source = "tencent"
    base_url = "https://qt.gtimg.cn/q="

    def __init__(self) -> None:
        self.settings = get_settings()

    def normalize_symbol(self, symbol: str) -> str:
        raw = symbol.strip().lower()
        if raw.startswith(("sh", "sz", "hk", "us")):
            return raw
        if raw.isdigit() and len(raw) == 6:
            return f"sh{raw}" if raw.startswith("6") else f"sz{raw}"
        return f"us{raw.upper()}"

    def get_quote(self, symbol: str) -> MarketDailyBar | None:
        query_symbol = self.normalize_symbol(symbol)
        url = f"{self.base_url}{query_symbol}"
        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            resp = client.get(url)
            resp.raise_for_status()
        text = resp.text.strip()
        if "~" not in text:
            return None
        payload = text.split('="', 1)[-1].rstrip('";')
        parts = payload.split("~")
        if len(parts) < 38:
            return None

        name = parts[1] or None
        code = parts[2] or symbol
        # Strip exchange suffix from US stocks (e.g. NVDA.OQ -> NVDA)
        if query_symbol.startswith("us") and "." in code:
            code = code.split(".")[0]
        close = self._to_float(parts[3])
        prev_close = self._to_float(parts[4])
        volume = self._to_int(parts[6])
        amount = self._to_float(parts[37])
        pct_change = self._to_float(parts[32])

        return MarketDailyBar(
            trade_date=today_cst(),
            symbol=code.upper(),
            name=name,
            close_price=close,
            prev_close=prev_close,
            pct_change=pct_change,
            volume=volume,
            amount=amount,
            source=self.source,
        )

    @staticmethod
    def _to_float(value: str) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: str) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
