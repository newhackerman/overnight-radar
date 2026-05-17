from app.db import SessionLocal
from app.services.daily_job_service import DailyJobService


def main() -> None:
    db = SessionLocal()
    try:
        ok = DailyJobService(db).run_daily_report(push=False)
        raise SystemExit(0 if ok else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
