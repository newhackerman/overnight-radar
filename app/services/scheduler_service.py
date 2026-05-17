import logging

from apscheduler.schedulers.background import BackgroundScheduler
from app.db import SessionLocal
from app.services.daily_job_service import DailyJobService
from app.services.report_service import ReportService
from app.services.wecom_push_service import WeComPushService
from app.utils.tz import today_cst

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def run_daily_analysis() -> None:
    db = SessionLocal()
    try:
        DailyJobService(db).run_daily_report(report_date=today_cst(), push=False)
    except Exception as exc:
        logger.error("Scheduled daily analysis failed: %s", exc, exc_info=True)
    finally:
        db.close()


def run_daily_push() -> None:
    db = SessionLocal()
    try:
        report_date = today_cst()
        markdown = ReportService(db).build_wecom_markdown(report_date)
        WeComPushService().push_markdown(markdown)
    except Exception as exc:
        logger.error("Scheduled daily push failed: %s", exc, exc_info=True)
    finally:
        db.close()


def start_scheduler(daily_job_time: str, daily_push_time: str) -> None:
    hour, minute = [int(part) for part in daily_job_time.split(":", 1)]
    scheduler.add_job(run_daily_analysis, "cron", hour=hour, minute=minute, id="daily_analysis", replace_existing=True)

    push_hour, push_minute = [int(part) for part in daily_push_time.split(":", 1)]
    scheduler.add_job(run_daily_push, "cron", hour=push_hour, minute=push_minute, id="daily_push", replace_existing=True)

    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
