from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.ai.client import AIClient
from app.ai.validators import parse_ai_json
from app.models.tables import ReportImpactItem, UsCnMappingHistory
from app.schemas.market import TopTurnoverItem
import logging

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, db: Session, ai_client: AIClient | None = None):
        self.db = db
        self.ai_client = ai_client or AIClient()

    def analyze_top_items(self, report_date: date, items: list[TopTurnoverItem]) -> list[ReportImpactItem]:
        saved_items: list[ReportImpactItem] = []
        for item in items:
            saved = self.analyze_one(report_date, item)
            if saved:
                saved_items.append(saved)
        self.db.commit()
        return saved_items

    def analyze_one(self, report_date: date, item: TopTurnoverItem) -> ReportImpactItem | None:
        payload = {
            "report_date": report_date.isoformat(),
            "trade_date": item.trade_date.isoformat(),
            "us_symbol": item.symbol,
            "us_name": item.name,
            "turnover_rank": item.rank_no,
            "pct_change": item.pct_change,
            "amount": item.amount,
            "event_candidates": [],
        }
        try:
            raw = self.ai_client.analyze_impact(payload)
        except Exception as exc:
            logger.warning("AI analysis failed for %s: %s", item.symbol, exc)
            return self._fallback_item(report_date, item)
        allowed_urls = {e["url"] for e in payload["event_candidates"] if e.get("url")}
        validated = parse_ai_json(raw, allowed_urls)
        if not validated:
            logger.warning("AI output validation failed for %s", item.symbol)
            return self._fallback_item(report_date, item)

        target_names = "/".join(target.name for target in validated.mapped_cn_targets)
        return self._upsert_item(validated, target_names)

    def _upsert_item(self, validated, target_names: str) -> ReportImpactItem:
        """Upsert a validated analysis item into report_impact_item.

        Uses INSERT ... ON DUPLICATE KEY UPDATE (via MySQL dialect) to handle
        concurrent duplicate (report_date, us_symbol) rows safely.
        """
        from sqlalchemy.dialects.mysql import insert as mysql_insert

        targets_json = [t.model_dump() for t in validated.mapped_cn_targets]
        stmt = mysql_insert(ReportImpactItem).values(
            report_date=validated.report_date,
            us_trade_date=validated.us_trade_date,
            us_symbol=validated.us_symbol,
            us_name=validated.us_name,
            turnover_rank=validated.turnover_rank,
            pct_change=validated.pct_change,
            amount=validated.amount,
            reason_category=validated.reason_category,
            event_summary=validated.event_summary,
            mapped_cn_targets=target_names,
            mapped_cn_symbols=targets_json,
            impact_direction=validated.impact_direction,
            impact_strength=validated.impact_strength,
            impact_score=validated.impact_score,
            confidence=validated.confidence,
            event_source=validated.event_source,
            source_type=validated.source_type,
            ai_model=validated.ai_model,
            raw_output=validated.raw_output,
        )
        update_dict = {c.name: stmt.inserted[c.name] for c in ReportImpactItem.__table__.c
                       if c.name not in ("id", "report_date", "us_symbol", "created_at")}
        upsert_stmt = stmt.on_duplicate_key_update(**update_dict)
        self.db.execute(upsert_stmt)
        self.db.flush()

        # Fetch the row (inserted or updated) for the caller
        row = self.db.scalar(
            select(ReportImpactItem).where(
                ReportImpactItem.report_date == validated.report_date,
                ReportImpactItem.us_symbol == validated.us_symbol,
            )
        )

        # Sync mapping targets to us_cn_mapping_history for backtest use
        self._save_mapping_history(validated)

        return row

    def _save_mapping_history(self, validated) -> None:
        """Sync AI-generated CN targets into us_cn_mapping_history for backtest."""
        for target in validated.mapped_cn_targets:
            existing = self.db.scalar(
                select(UsCnMappingHistory).where(
                    UsCnMappingHistory.report_date == validated.report_date,
                    UsCnMappingHistory.us_symbol == validated.us_symbol,
                    UsCnMappingHistory.cn_symbol == target.symbol,
                )
            )
            if existing:
                existing.cn_name = target.name
                existing.relation_type = target.relation_type
                existing.theme = target.theme
                existing.impact_direction = validated.impact_direction
                existing.impact_strength = validated.impact_strength
                existing.confidence = validated.confidence
                existing.source = "ai_analysis"
            else:
                self.db.add(UsCnMappingHistory(
                    report_date=validated.report_date,
                    us_symbol=validated.us_symbol,
                    cn_symbol=target.symbol,
                    cn_name=target.name,
                    relation_type=target.relation_type,
                    theme=target.theme,
                    impact_direction=validated.impact_direction,
                    impact_strength=validated.impact_strength,
                    confidence=validated.confidence,
                    source="ai_analysis",
                ))

    def _fallback_item(self, report_date: date, item: TopTurnoverItem) -> ReportImpactItem:
        from sqlalchemy.dialects.mysql import insert as mysql_insert

        pct_change = item.pct_change or 0
        direction = "利多" if pct_change > 0 else "利空" if pct_change < 0 else "中性"
        strength = 3 if abs(pct_change) >= 3 else 2
        stmt = mysql_insert(ReportImpactItem).values(
            report_date=report_date,
            us_trade_date=item.trade_date,
            us_symbol=item.symbol,
            us_name=item.name,
            turnover_rank=item.rank_no,
            pct_change=item.pct_change,
            amount=item.amount,
            reason_category="行情异动",
            event_summary="基于行情数据生成初步判断",
            mapped_cn_targets="",
            mapped_cn_symbols=[],
            impact_direction=direction,
            impact_strength=strength,
            impact_score=min(1.0, max(0.1, abs(pct_change) / 10)),
            confidence=0.3,
            event_source="AI分析",
            source_type="ai_analysis",
            ai_model=self.ai_client.settings.ai_model,
            raw_output={},
        )
        update_dict = {c.name: stmt.inserted[c.name] for c in ReportImpactItem.__table__.c
                       if c.name not in ("id", "report_date", "us_symbol", "created_at")}
        upsert_stmt = stmt.on_duplicate_key_update(**update_dict)
        self.db.execute(upsert_stmt)
        self.db.flush()

        row = self.db.scalar(
            select(ReportImpactItem).where(
                ReportImpactItem.report_date == report_date,
                ReportImpactItem.us_symbol == item.symbol,
            )
        )
        return row
