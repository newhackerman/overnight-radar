"""Tests for AI output validation logic."""
from app.ai.validators import parse_ai_json


def test_parse_valid_ai_output():
    raw = {
        "report_date": "2026-05-17",
        "us_trade_date": "2026-05-15",
        "us_symbol": "NVDA",
        "us_name": "英伟达",
        "turnover_rank": 1,
        "pct_change": -4.42,
        "amount": 41150000000,
        "reason_category": "股价大跌",
        "event_summary": "英伟达股价下跌超4%",
        "mapped_cn_targets": [
            {"symbol": "603501", "name": "韦尔股份", "relation_type": "产业链", "theme": "半导体"}
        ],
        "impact_direction": "偏空",
        "impact_strength": 3,
        "impact_score": 0.44,
        "confidence": 0.7,
        "event_source": "AI分析",
        "source_type": "ai_analysis",
        "ai_model": "test-model",
    }
    result = parse_ai_json(raw, set())
    assert result is not None
    assert result.us_symbol == "NVDA"
    assert result.impact_direction == "偏空"
    assert result.impact_strength == 3


def test_parse_clamps_impact_score_over_1():
    raw = {
        "report_date": "2026-05-17",
        "us_trade_date": "2026-05-15",
        "us_symbol": "TSLA",
        "us_name": "特斯拉",
        "turnover_rank": 2,
        "pct_change": -4.75,
        "amount": 22450000000,
        "reason_category": "股价大跌",
        "event_summary": "特斯拉下跌",
        "mapped_cn_targets": [],
        "impact_direction": "偏空",
        "impact_strength": 2,
        "impact_score": 47,  # Should be clamped to 0.47
        "confidence": 70,  # Should be clamped to 0.70
        "event_source": "AI分析",
        "source_type": "ai_analysis",
        "ai_model": "test-model",
    }
    result = parse_ai_json(raw, set())
    assert result is not None
    assert result.impact_score <= 1.0
    assert result.confidence <= 1.0


def test_parse_strips_exchange_suffix_from_cn_symbols():
    raw = {
        "report_date": "2026-05-17",
        "us_trade_date": "2026-05-15",
        "us_symbol": "AAPL",
        "us_name": "苹果",
        "turnover_rank": 5,
        "pct_change": 0.68,
        "amount": 16480000000,
        "reason_category": "股价小幅波动",
        "event_summary": "苹果股价微涨",
        "mapped_cn_targets": [
            {"symbol": "002475.SZ", "name": "立讯精密", "relation_type": "供应链", "theme": "消费电子"}
        ],
        "impact_direction": "利多",
        "impact_strength": 1,
        "impact_score": 0.1,
        "confidence": 0.5,
        "event_source": "AI分析",
        "source_type": "ai_analysis",
        "ai_model": "test-model",
    }
    result = parse_ai_json(raw, set())
    assert result is not None
    assert result.mapped_cn_targets[0].symbol == "002475"


def test_parse_rejects_invalid_event_source_url():
    raw = {
        "report_date": "2026-05-17",
        "us_trade_date": "2026-05-15",
        "us_symbol": "META",
        "us_name": "Meta",
        "turnover_rank": 9,
        "pct_change": -0.68,
        "amount": 8160000000,
        "reason_category": "股价小幅波动",
        "event_summary": "META小幅下跌",
        "mapped_cn_targets": [],
        "impact_direction": "中性",
        "impact_strength": 1,
        "impact_score": 0.07,
        "confidence": 0.4,
        "event_source": "https://fake-news.example.com/article",
        "source_type": "url",
        "ai_model": "test-model",
    }
    # URL not in allowed set should be replaced with "AI分析"
    allowed = {"https://reuters.com/article/123"}
    result = parse_ai_json(raw, allowed)
    assert result is not None
    assert result.event_source == "AI分析"
    assert result.source_type == "ai_analysis"


def test_parse_returns_none_for_garbage():
    result = parse_ai_json({"garbage": True}, set())
    assert result is None


def test_parse_normalizes_nonstandard_source_type():
    raw = {
        "report_date": "2026-05-17",
        "us_trade_date": "2026-05-15",
        "us_symbol": "MSFT",
        "us_name": "微软",
        "turnover_rank": 4,
        "pct_change": 3.05,
        "amount": 21420000000,
        "reason_category": "AI业务增长",
        "event_summary": "微软AI业务强劲",
        "mapped_cn_targets": [],
        "impact_direction": "利多",
        "impact_strength": 4,
        "impact_score": 0.3,
        "confidence": 0.8,
        "event_source": "AI分析",
        "source_type": "news_article",  # non-standard, should become ai_analysis
        "ai_model": "test-model",
    }
    result = parse_ai_json(raw, set())
    assert result is not None
    assert result.source_type == "ai_analysis"
