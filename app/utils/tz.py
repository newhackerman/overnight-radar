from datetime import date, datetime, timezone, timedelta

_CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    return datetime.now(_CST)


def today_cst() -> date:
    return now_cst().date()
