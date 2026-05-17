"""Tests for Tencent client parsing logic."""
from unittest.mock import patch, MagicMock
from app.data_sources.tencent_client import TencentClient


def test_normalize_symbol_us_stock():
    client = TencentClient.__new__(TencentClient)
    assert client.normalize_symbol("NVDA") == "usNVDA"
    assert client.normalize_symbol("nvda") == "usNVDA"


def test_normalize_symbol_cn_stock():
    client = TencentClient.__new__(TencentClient)
    assert client.normalize_symbol("600519") == "sh600519"
    assert client.normalize_symbol("000001") == "sz000001"


def test_normalize_symbol_already_prefixed():
    client = TencentClient.__new__(TencentClient)
    assert client.normalize_symbol("usNVDA") == "usnvda"
    assert client.normalize_symbol("sh600519") == "sh600519"


def test_parse_quote_response(mock_settings):
    """Test parsing a simulated Tencent API response."""
    # Simulated response with 38+ fields separated by ~
    fields = [""] * 50
    fields[1] = "英伟达"  # name
    fields[2] = "NVDA.OQ"  # code (with exchange suffix)
    fields[3] = "120.50"  # close
    fields[4] = "125.00"  # prev_close
    fields[6] = "50000000"  # volume
    fields[32] = "-3.60"  # pct_change
    fields[37] = "6025000000"  # amount
    payload = "~".join(fields)
    response_text = f'v_usNVDA="{payload}";'

    mock_resp = MagicMock()
    mock_resp.text = response_text
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = TencentClient()
        bar = client.get_quote("NVDA")

    assert bar is not None
    assert bar.symbol == "NVDA"  # Exchange suffix stripped
    assert bar.name == "英伟达"
    assert bar.close_price == 120.50
    assert bar.prev_close == 125.00
    assert bar.pct_change == -3.60


def test_parse_empty_response(mock_settings):
    """Empty response should return None."""
    mock_resp = MagicMock()
    mock_resp.text = 'v_usXYZ="";'
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        client = TencentClient()
        bar = client.get_quote("XYZ")

    assert bar is None
