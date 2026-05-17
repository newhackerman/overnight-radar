import ipaddress
from urllib.parse import urlparse

ALLOWED_EVENT_SCHEMES = {"https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def mask_secret(value: str | None, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * 8}"


def is_safe_external_url(url: str, allowed_domains: set[str] | None = None) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ALLOWED_EVENT_SCHEMES:
        return False
    if not parsed.hostname:
        return False

    hostname = parsed.hostname.lower()
    if hostname in BLOCKED_HOSTS:
        return False

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass

    if allowed_domains and not any(hostname == d or hostname.endswith(f".{d}") for d in allowed_domains):
        return False

    return True


def choose_event_source(candidate_url: str | None, allowed_urls: set[str]) -> tuple[str, str]:
    if candidate_url and candidate_url in allowed_urls and is_safe_external_url(candidate_url):
        return candidate_url, "url"
    return "AI分析", "ai_analysis"
