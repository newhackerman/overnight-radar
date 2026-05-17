"""Tests for report service."""
from datetime import date
from app.models.tables import ReportImpactItem
from app.services.report_service import ReportService, stars


def test_stars_function():
    assert stars(None) == ""
    assert stars(0) == ""
    assert stars(1) == "★"
    assert stars(3) == "★★★"
    assert stars(5) == "★★★★★"
    assert stars(10) == "★★★★★"  # clamped to 5


def test_build_wecom_markdown(db_session):
    report_date = date(2026, 5, 17)
    item = ReportImpactItem(
        id=1,
        report_date=report_date,
        us_trade_date=date(2026, 5, 15),
        us_symbol="NVDA",
        us_name="英伟达",
        turnover_rank=1,
        pct_change=-4.42,
        amount=41150000000,
        reason_category="股价大跌",
        event_summary="英伟达下跌超4%",
        mapped_cn_targets="韦尔股份/中芯国际",
        mapped_cn_symbols=[],
        impact_direction="偏空",
        impact_strength=3,
        impact_score=0.44,
        confidence=0.7,
        event_source="AI分析",
        source_type="ai_analysis",
        ai_model="test-model",
        raw_output={},
    )
    db_session.add(item)
    db_session.commit()

    svc = ReportService(db_session)
    md = svc.build_wecom_markdown(report_date)

    assert "隔夜美股影响A股早报" in md
    assert "NVDA" in md
    assert "偏空" in md
    assert "韦尔股份/中芯国际" in md


def test_get_items_by_date_empty(db_session):
    svc = ReportService(db_session)
    items = svc.get_items_by_date(date(2020, 1, 1))
    assert items == []
