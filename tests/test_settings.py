from pathlib import Path
from typing import Any

from config import settings
from database.db import get_default_db_path


def test_runtime_settings_default_to_local_sqlite(monkeypatch: Any) -> None:
    monkeypatch.delenv(settings.APP_MODE_ENV_VAR, raising=False)
    monkeypatch.delenv(settings.DATABASE_URL_ENV_VAR, raising=False)

    runtime = settings.get_runtime_settings()

    assert runtime.app_mode == "local"
    assert runtime.database_backend == "sqlite"
    assert runtime.supports_shared_voting is False


def test_runtime_settings_detect_cloud_sqlite(monkeypatch: Any) -> None:
    monkeypatch.setenv(settings.APP_MODE_ENV_VAR, "cloud")
    monkeypatch.setenv(settings.DATABASE_URL_ENV_VAR, "sqlite:///data/cloud_demo.db")

    runtime = settings.get_runtime_settings()

    assert runtime.app_mode == "cloud"
    assert runtime.database_backend == "sqlite"
    assert runtime.supports_shared_voting is True


def test_runtime_settings_detect_postgres_intent(monkeypatch: Any) -> None:
    monkeypatch.setenv(settings.APP_MODE_ENV_VAR, "cloud")
    monkeypatch.setenv(settings.DATABASE_URL_ENV_VAR, "postgresql://user:pass@example.com/db")

    runtime = settings.get_runtime_settings()

    assert runtime.database_backend == "postgres"
    assert runtime.supports_shared_voting is False
    assert runtime.warning is not None


def test_default_db_path_can_use_sqlite_database_url(monkeypatch: Any) -> None:
    monkeypatch.setenv(settings.DATABASE_URL_ENV_VAR, "sqlite:///data/custom_demo.db")

    assert get_default_db_path() == Path("data/custom_demo.db")
