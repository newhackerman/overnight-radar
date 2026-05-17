from datetime import date

from app.config import get_settings
from app.utils.tz import now_cst, today_cst
from sqlalchemy.orm import Session
from app.models.tables import JobRunLog
from app.services.analysis_service import AnalysisService
from app.services.report_service import ReportService
from app.services.us_top_turnover_service import UsTopTurnoverService
from app.services.wecom_push_service import WeComPushService


class DailyJobService:
    def __init__(self, db: Session):
        self.db = db

    def run_daily_report(self, report_date: date | None = None, push: bool = False) -> bool:
        report_date = report_date or today_cst()
        log = JobRunLog(
            job_name="daily_report",
            run_date=report_date,
            status="running",
            started_at=now_cst(),
        )
        self.db.add(log)
        self.db.commit()

        try:
            settings = get_settings()
            top_items = UsTopTurnoverService().calculate_top_turnover(settings.us_symbols)
            AnalysisService(self.db).analyze_top_items(report_date, top_items)
            if push:
                markdown = ReportService(self.db).build_wecom_markdown(report_date)
                WeComPushService().push_markdown(markdown)
            log.status = "success"
            log.finished_at = now_cst()
            self.db.commit()
            return True
        except Exception as exc:
            import logging, traceback
            logging.getLogger(__name__).error("Daily job failed: %s\n%s", exc, traceback.format_exc())
            self.db.rollback()
            log.status = "failed"
            log.error_message = str(exc)[:2000]
            log.finished_at = now_cst()
            self.db.merge(log)
            self.db.commit()
            return False
