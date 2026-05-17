import secrets
import sys
import time
from fastapi import Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext
from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE = "overnight_session"
CSRF_COOKIE = "overnight_csrf"
_settings_cache = None


def _get_session_config():
    """Get session/rate-limit config from settings (cached)."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = get_settings()
    return _settings_cache


# Simple in-memory rate limiter for login attempts
_login_attempts: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(password, password_hash)


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key.get_secret_value(), salt="overnight-radar-session")


def create_session_token(username: str) -> str:
    return _serializer().dumps({"username": username})


def read_session_username(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        cfg = _get_session_config()
        data = _serializer().loads(token, max_age=cfg.session_max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    username = data.get("username")
    return username if isinstance(username, str) else None


def check_rate_limit(client_ip: str) -> bool:
    """Returns True if the request is allowed, False if rate-limited."""
    cfg = _get_session_config()
    now = time.time()
    attempts = _login_attempts.get(client_ip, [])
    attempts = [t for t in attempts if now - t < cfg.login_window_seconds]
    _login_attempts[client_ip] = attempts
    return len(attempts) < cfg.login_max_attempts


def record_login_attempt(client_ip: str) -> None:
    """Record a failed login attempt."""
    now = time.time()
    if client_ip not in _login_attempts:
        _login_attempts[client_ip] = []
    _login_attempts[client_ip].append(now)


def require_login(request: Request) -> str:
    username = read_session_username(request)
    if username:
        return username
    raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if not cookie_token or not secrets.compare_digest(cookie_token, csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


def login_response(username: str) -> RedirectResponse:
    cfg = _get_session_config()
    secure = cfg.app_env != "development"
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(SESSION_COOKIE, create_session_token(username), httponly=True, samesite="lax", secure=secure)
    response.set_cookie(CSRF_COOKIE, new_csrf_token(), httponly=False, samesite="lax", secure=secure)
    return response


def logout_response() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)
    return response


def template_context(request: Request) -> dict:
    csrf_token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()
    return {"request": request, "csrf_token": csrf_token, "current_user": read_session_username(request)}


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--hash-password":
        print(hash_password(sys.argv[2]))
    else:
        print("Usage: python -m app.web.auth --hash-password <password>")
