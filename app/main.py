import logging
import sys
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.web.routes import router as web_router

_APP_DIR = Path(__file__).resolve().parent


def configure_logging() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    logging.getLogger("yfinance").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    start_scheduler(settings.daily_job_time, settings.daily_push_time)
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(_APP_DIR / "static")), name="static")
    app.state.templates = Jinja2Templates(directory=str(_APP_DIR / "templates"))
    app.include_router(web_router)

    @app.get("/health")
    def health_check():
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
