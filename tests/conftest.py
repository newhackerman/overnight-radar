import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base


@pytest.fixture
def db_session():
    """In-memory SQLite session for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_settings(monkeypatch):
    """Patch get_settings to return test-safe defaults."""
    from app.config import Settings
    settings = Settings(
        ai_api_key="test-key",
        ai_base_url="http://localhost:9999/v1",
        ai_model="test-model",
        mysql_host="localhost",
        mysql_password="test",
        wecom_webhook="http://localhost:9999/webhook",
        secret_key="test-secret-key",
        admin_password_hash="$2b$12$LJ3m4sMKfRzG4verL5ARE.Fy0UtFnpMTL.RTGEZ8JQgoTV6X3u3hK",
    )
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    return settings
