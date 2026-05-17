from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.tables import ReportImpactItem


def stars(strength: int | None) -> str:
    if not strength:
        return ""
    return "★" * max(1, min(5, strength))


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_items(self, order_by: str = "turnover_rank") -> list[ReportImpactItem]:
        latest_date = self.db.scalar(select(ReportImpactItem.report_date).order_by(ReportImpactItem.report_date.desc()).limit(1))
        if latest_date is None:
            return []
        return self.get_items_by_date(latest_date, order_by=order_by)

    def get_items_by_date(self, report_date, order_by: str = "turnover_rank") -> list[ReportImpactItem]:
        stmt = select(ReportImpactItem).where(ReportImpactItem.report_date == report_date)
        if order_by == "impact_strength":
            # MySQL doesn't support NULLS LAST; use COALESCE to push NULLs to end
            from sqlalchemy import func
            stmt = stmt.order_by(
                func.coalesce(ReportImpactItem.impact_strength, 0).desc(),
                ReportImpactItem.turnover_rank.asc(),
            )
        else:
            stmt = stmt.order_by(ReportImpactItem.turnover_rank.asc())
        return list(self.db.scalars(stmt).all())

    def build_wecom_markdown(self, report_date) -> str:
        """Build WeCom-compatible markdown (no table support, use font colors)."""
        settings = get_settings()
        items = self.get_items_by_date(report_date, order_by="impact_strength")[:settings.report_max_items]

        lines = [
            f"# 隔夜美股影响A股早报 {report_date}",
            f"> 共{len(items)}只标的，按影响强度排序",
            "",
        ]

        # Group by impact strength tiers
        high = [i for i in items if (i.impact_strength or 0) >= 4]
        mid = [i for i in items if (i.impact_strength or 0) in (2, 3)]
        low = [i for i in items if (i.impact_strength or 0) <= 1]

        if high:
            lines.append("**◆ 重点关注**")
            for item in high:
                lines.append(self._format_wecom_item(item, detail=True))
            lines.append("")

        if mid:
            lines.append("**◇ 中等影响**")
            for item in mid:
                lines.append(self._format_wecom_item(item, detail=False))
            lines.append("")

        if low:
            lines.append("<font color=\"comment\">◦ 影响较小</font>")
            for item in low:
                lines.append(self._format_wecom_item(item, detail=False))

        return "\n".join(lines)

    def _format_wecom_item(self, item, detail: bool = False) -> str:
        """Format a single item for WeCom markdown."""
        pct = "" if item.pct_change is None else f"{float(item.pct_change):+.1f}%"
        strength = stars(item.impact_strength)

        # WeCom only supports: info(green), comment(gray), warning(orange)
        direction = item.impact_direction or ""
        if direction in ("利空", "偏空"):
            dir_text = f'<font color="info">{direction}</font>'
        elif direction in ("利多", "偏多"):
            dir_text = f'<font color="warning">{direction}</font>'
        else:
            dir_text = f'<font color="comment">{direction or "中性"}</font>'

        line = f"**{item.us_symbol}** {pct} {strength} {dir_text}"

        if detail:
            parts = [line]
            if item.event_summary:
                parts.append(f"> {item.event_summary}")
            if item.mapped_cn_targets:
                parts.append(f"> 映射A股：{item.mapped_cn_targets}")
            return "\n".join(parts)

        # Compact: symbol + pct + direction + mapped targets
        cn = item.mapped_cn_targets or ""
        if cn:
            line += f"  →{cn[:30]}"
        return line
