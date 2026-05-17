from datetime import date, datetime
from sqlalchemy import Date, DateTime, DECIMAL, Integer, BigInteger, String, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from app.utils.tz import now_cst


class ReportImpactItem(Base):
    __tablename__ = "report_impact_item"
    __table_args__ = (
        UniqueConstraint("report_date", "us_symbol", name="uk_report_symbol"),
        Index("idx_report_date", "report_date"),
        Index("idx_us_trade_date", "us_trade_date"),
        Index("idx_direction_strength", "impact_direction", "impact_strength"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    us_trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    us_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    us_name: Mapped[str | None] = mapped_column(String(128))
    turnover_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    pct_change: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    amount: Mapped[float | None] = mapped_column(DECIMAL(24, 4))
    reason_category: Mapped[str | None] = mapped_column(String(64))
    event_summary: Mapped[str | None] = mapped_column(String(512))
    mapped_cn_targets: Mapped[str | None] = mapped_column(Text)
    mapped_cn_symbols: Mapped[list | None] = mapped_column(JSON)
    impact_direction: Mapped[str | None] = mapped_column(String(16))
    impact_strength: Mapped[int | None] = mapped_column(Integer)
    impact_score: Mapped[float | None] = mapped_column(DECIMAL(5, 4))
    confidence: Mapped[float | None] = mapped_column(DECIMAL(5, 4))
    event_source: Mapped[str | None] = mapped_column(String(1024))
    source_type: Mapped[str | None] = mapped_column(String(32))
    ai_model: Mapped[str | None] = mapped_column(String(64))
    raw_output: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst)


class EventReference(Base):
    __tablename__ = "event_reference"
    __table_args__ = (Index("idx_event_ref", "trade_date", "us_symbol"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    us_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    source: Mapped[str | None] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(String(1024))
    authority_level: Mapped[str | None] = mapped_column(String(32))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst)


class UsCnMappingHistory(Base):
    __tablename__ = "us_cn_mapping_history"
    __table_args__ = (
        Index("idx_mapping_date", "report_date"),
        Index("idx_us_symbol", "us_symbol"),
        Index("idx_cn_symbol", "cn_symbol"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    us_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    cn_symbol: Mapped[str | None] = mapped_column(String(32))
    cn_name: Mapped[str | None] = mapped_column(String(128))
    relation_type: Mapped[str | None] = mapped_column(String(64))
    theme: Mapped[str | None] = mapped_column(String(128))
    impact_direction: Mapped[str | None] = mapped_column(String(16))
    impact_strength: Mapped[int | None] = mapped_column(Integer)
    impact_score: Mapped[float | None] = mapped_column(DECIMAL(5, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(DECIMAL(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst)


class CnMarketDaily(Base):
    __tablename__ = "cn_market_daily"
    __table_args__ = (UniqueConstraint("trade_date", "symbol", name="uk_cn_daily"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(128))
    close_price: Mapped[float | None] = mapped_column(DECIMAL(18, 4))
    prev_close: Mapped[float | None] = mapped_column(DECIMAL(18, 4))
    pct_change: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    amount: Mapped[float | None] = mapped_column(DECIMAL(24, 4))
    source: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst)


class BacktestResult(Base):
    __tablename__ = "backtest_result"
    __table_args__ = (UniqueConstraint("event_date", "us_symbol", "cn_symbol", name="uk_backtest"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    cn_trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    us_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    cn_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    t_return: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    t1_return: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    t3_return: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    t5_return: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    t10_return: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    current_return: Mapped[float | None] = mapped_column(DECIMAL(10, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst)


class JobRunLog(Base):
    __tablename__ = "job_run_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(128), nullable=False)
    run_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_cst)
