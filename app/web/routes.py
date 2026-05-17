from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db
from app.models.tables import JobRunLog
from app.services.backtest_service import BacktestService
from app.services.daily_job_service import DailyJobService
from app.services.mapping_service import MappingService
from app.services.report_service import ReportService, stars
from app.services.wecom_push_service import WeComPushService
from app.web.auth import (
    CSRF_COOKIE,
    check_rate_limit,
    login_response,
    logout_response,
    record_login_attempt,
    require_login,
    template_context,
    verify_csrf,
    verify_password,
)

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    from app.web.auth import new_csrf_token
    # Always issue a fresh CSRF token on the login page to avoid stale-cookie mismatches
    csrf = new_csrf_token()
    context = template_context(request) | {"csrf_token": csrf}
    response = request.app.state.templates.TemplateResponse("login.html", context)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, samesite="lax")
    return response


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    _: None = Depends(verify_csrf),
):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        context = template_context(request) | {"error": "登录尝试过于频繁，请5分钟后再试"}
        return request.app.state.templates.TemplateResponse("login.html", context, status_code=429)

    settings = get_settings()
    expected_hash = settings.admin_password_hash.get_secret_value()
    if username == settings.admin_username and verify_password(password, expected_hash):
        return login_response(username, request)

    record_login_attempt(client_ip)
    context = template_context(request) | {"error": "用户名或密码错误"}
    return request.app.state.templates.TemplateResponse("login.html", context, status_code=401)


@router.post("/logout")
def logout(_: str = Depends(require_login), __: None = Depends(verify_csrf)):
    return logout_response()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), _: str = Depends(require_login)):
    service = ReportService(db)
    items = service.get_latest_items(order_by="impact_strength")
    report_date = items[0].report_date if items else date.today()
    return request.app.state.templates.TemplateResponse(
        "daily_report.html",
        template_context(request) | {"items": items, "report_date": report_date, "stars": stars},
    )


@router.get("/reports/{report_date}")
def report_by_date(report_date: date, request: Request, db: Session = Depends(get_db), _: str = Depends(require_login)):
    service = ReportService(db)
    items = service.get_items_by_date(report_date, order_by="impact_strength")
    return request.app.state.templates.TemplateResponse(
        "daily_report.html",
        template_context(request) | {"items": items, "report_date": report_date, "stars": stars},
    )


@router.post("/reports/open")
def open_report(report_date: date = Form(...), _: str = Depends(require_login), __: None = Depends(verify_csrf)):
    return RedirectResponse(url=f"/reports/{report_date}", status_code=303)


@router.post("/reports/run")
def run_report(
    report_date: date = Form(...),
    push: bool = Form(False),
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    __: None = Depends(verify_csrf),
):
    DailyJobService(db).run_daily_report(report_date=report_date, push=push)
    return RedirectResponse(url=f"/reports/{report_date}", status_code=303)


@router.post("/reports/{report_date}/push")
def push_report(
    report_date: date,
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    __: None = Depends(verify_csrf),
):
    markdown = ReportService(db).build_wecom_markdown(report_date)
    WeComPushService().push_markdown(markdown)
    return RedirectResponse(url=f"/reports/{report_date}", status_code=303)


@router.get("/backtest")
def backtest_page(request: Request, db: Session = Depends(get_db), _: str = Depends(require_login)):
    available_dates = _get_backtest_dates(db)
    return request.app.state.templates.TemplateResponse(
        "backtest.html",
        template_context(request) | {"results": [], "event_date": None, "stars": stars, "available_dates": available_dates, "stats": {}},
    )


@router.post("/backtest/run")
def run_backtest(
    request: Request,
    event_date: date = Form(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    __: None = Depends(verify_csrf),
):
    results = BacktestService(db).run(event_date)
    stats = _compute_backtest_stats(results)
    available_dates = _get_backtest_dates(db)
    return request.app.state.templates.TemplateResponse(
        "backtest.html",
        template_context(request) | {"results": results, "event_date": event_date, "stars": stars, "available_dates": available_dates, "stats": stats},
    )


def _get_backtest_dates(db: Session) -> list[date]:
    """Get dates that have mapping data available for backtest."""
    from sqlalchemy import func
    from app.models.tables import UsCnMappingHistory
    rows = db.execute(
        select(UsCnMappingHistory.report_date)
        .group_by(UsCnMappingHistory.report_date)
        .order_by(UsCnMappingHistory.report_date.desc())
        .limit(20)
    ).scalars().all()
    return list(rows)


def _compute_backtest_stats(results: list[dict]) -> dict:
    """Compute summary statistics for backtest results."""
    if not results:
        return {"win_rate": 0, "avg_return": 0, "direction_accuracy": 0}
    returns = [r.get("t_return") for r in results if r.get("t_return") is not None]
    if not returns:
        return {"win_rate": 0, "avg_return": 0, "direction_accuracy": 0}

    wins = sum(1 for r in returns if r > 0)
    win_rate = wins / len(returns) * 100

    avg_return = sum(returns) / len(returns)

    # Direction accuracy: did the predicted direction match actual movement?
    correct = 0
    total = 0
    for r in results:
        t_ret = r.get("t_return")
        direction = r.get("impact_direction", "")
        if t_ret is None:
            continue
        total += 1
        if direction in ("利多", "偏多") and t_ret > 0:
            correct += 1
        elif direction in ("利空", "偏空") and t_ret < 0:
            correct += 1
        elif direction == "中性" and abs(t_ret) < 1:
            correct += 1
    direction_accuracy = (correct / total * 100) if total > 0 else 0

    return {"win_rate": round(win_rate, 1), "avg_return": round(avg_return, 4), "direction_accuracy": round(direction_accuracy, 1)}


@router.get("/mappings")
def mappings_page(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    us_symbol: str = Query(default=""),
    cn_symbol: str = Query(default=""),
    theme: str = Query(default=""),
    report_date_start: Optional[date] = Query(default=None),
    report_date_end: Optional[date] = Query(default=None),
):
    svc = MappingService(db)
    has_filter = any([us_symbol, cn_symbol, theme, report_date_start, report_date_end])
    mappings = svc.search(
        us_symbol=us_symbol or None,
        cn_symbol=cn_symbol or None,
        theme=theme or None,
        report_date_start=report_date_start,
        report_date_end=report_date_end,
    ) if has_filter else svc.list_recent()
    return request.app.state.templates.TemplateResponse(
        "mappings.html",
        template_context(request) | {
            "mappings": mappings,
            "stars": stars,
            "filters": {
                "us_symbol": us_symbol,
                "cn_symbol": cn_symbol,
                "theme": theme,
                "report_date_start": report_date_start or "",
                "report_date_end": report_date_end or "",
            },
        },
    )


@router.post("/mappings/create")
def create_mapping(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    __: None = Depends(verify_csrf),
    report_date: date = Form(...),
    us_symbol: str = Form(...),
    cn_symbol: str = Form(""),
    cn_name: str = Form(""),
    theme: str = Form(""),
    relation_type: str = Form(""),
    impact_direction: str = Form(""),
    impact_strength: int = Form(0),
    confidence: float = Form(0),
):
    MappingService(db).create(
        report_date=report_date,
        us_symbol=us_symbol,
        cn_symbol=cn_symbol or None,
        cn_name=cn_name or None,
        theme=theme or None,
        relation_type=relation_type or None,
        impact_direction=impact_direction or None,
        impact_strength=impact_strength or None,
        confidence=confidence or None,
    )
    db.commit()
    return RedirectResponse(url="/mappings", status_code=303)


@router.post("/mappings/{mapping_id}/edit")
def edit_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    __: None = Depends(verify_csrf),
    report_date: date = Form(...),
    us_symbol: str = Form(...),
    cn_symbol: str = Form(""),
    cn_name: str = Form(""),
    theme: str = Form(""),
    relation_type: str = Form(""),
    impact_direction: str = Form(""),
    impact_strength: int = Form(0),
    confidence: float = Form(0),
):
    MappingService(db).update(
        mapping_id,
        report_date=report_date,
        us_symbol=us_symbol,
        cn_symbol=cn_symbol or None,
        cn_name=cn_name or None,
        theme=theme or None,
        relation_type=relation_type or None,
        impact_direction=impact_direction or None,
        impact_strength=impact_strength or None,
        confidence=confidence or None,
    )
    db.commit()
    return RedirectResponse(url="/mappings", status_code=303)


@router.post("/mappings/{mapping_id}/delete")
def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_login),
    __: None = Depends(verify_csrf),
):
    MappingService(db).delete(mapping_id)
    db.commit()
    return RedirectResponse(url="/mappings", status_code=303)


@router.get("/jobs")
def jobs_page(request: Request, db: Session = Depends(get_db), _: str = Depends(require_login)):
    logs = list(db.scalars(select(JobRunLog).order_by(JobRunLog.created_at.desc()).limit(100)).all())
    return request.app.state.templates.TemplateResponse("jobs.html", template_context(request) | {"logs": logs})
