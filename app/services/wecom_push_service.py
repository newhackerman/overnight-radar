import httpx
from app.config import get_settings


class WeComPushService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def push_markdown(self, markdown: str) -> bool:
        webhook = self.settings.wecom_webhook.get_secret_value()
        if not webhook:
            return False

        max_bytes = self.settings.wecom_max_bytes
        content = self._truncate_to_bytes(markdown, max_bytes)

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            resp = client.post(webhook, json=payload)
            resp.raise_for_status()
        data = resp.json()
        return data.get("errcode") == 0

    @staticmethod
    def _truncate_to_bytes(text: str, max_bytes: int) -> str:
        """Truncate text to fit within max_bytes in UTF-8 encoding."""
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        # Truncate bytes and decode safely (ignore partial chars at the end)
        truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
        return truncated
