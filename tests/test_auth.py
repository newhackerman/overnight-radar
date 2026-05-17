"""Tests for auth utilities."""
import time
from app.web.auth import (
    check_rate_limit,
    record_login_attempt,
    _login_attempts,
    _get_session_config,
)


def test_rate_limit_allows_initial_attempts(mock_settings):
    ip = "192.168.1.100"
    _login_attempts.pop(ip, None)
    assert check_rate_limit(ip) is True


def test_rate_limit_blocks_after_max_attempts(mock_settings):
    ip = "192.168.1.200"
    _login_attempts.pop(ip, None)
    max_attempts = mock_settings.login_max_attempts
    for _ in range(max_attempts):
        record_login_attempt(ip)
    assert check_rate_limit(ip) is False


def test_rate_limit_resets_after_window(mock_settings):
    ip = "192.168.1.201"
    _login_attempts.pop(ip, None)
    max_attempts = mock_settings.login_max_attempts
    # Simulate old attempts outside the window
    _login_attempts[ip] = [time.time() - 400] * max_attempts
    assert check_rate_limit(ip) is True
