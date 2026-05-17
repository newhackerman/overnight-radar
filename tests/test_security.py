"""Tests for security utilities."""
from app.security import choose_event_source, is_safe_external_url, mask_secret


def test_is_safe_url_allows_https():
    assert is_safe_external_url("https://reuters.com/article/123") is True


def test_is_safe_url_blocks_http():
    assert is_safe_external_url("http://example.com") is False


def test_is_safe_url_blocks_private_ip():
    assert is_safe_external_url("https://192.168.1.1/admin") is False
    assert is_safe_external_url("https://10.0.0.1/secret") is False
    assert is_safe_external_url("https://127.0.0.1/") is False


def test_is_safe_url_blocks_localhost():
    assert is_safe_external_url("https://localhost/admin") is False


def test_is_safe_url_blocks_non_url():
    assert is_safe_external_url("not-a-url") is False
    assert is_safe_external_url("") is False


def test_choose_event_source_with_allowed_url():
    allowed = {"https://reuters.com/article/123"}
    source, stype = choose_event_source("https://reuters.com/article/123", allowed)
    assert source == "https://reuters.com/article/123"
    assert stype == "url"


def test_choose_event_source_rejects_unlisted_url():
    allowed = {"https://reuters.com/article/123"}
    source, stype = choose_event_source("https://fake.com/bad", allowed)
    assert source == "AI分析"
    assert stype == "ai_analysis"


def test_choose_event_source_ai_analysis_passthrough():
    source, stype = choose_event_source("AI分析", set())
    assert source == "AI分析"
    assert stype == "ai_analysis"


def test_mask_secret_short():
    assert mask_secret("ab") == "**"


def test_mask_secret_normal():
    result = mask_secret("my-secret-key-12345")
    assert result.startswith("my-")
    assert result.endswith("****")
    assert "secret" not in result
