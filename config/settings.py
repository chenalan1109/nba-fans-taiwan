from __future__ import annotations

import os
from dataclasses import dataclass


APP_MODE_ENV_VAR = "APP_MODE"
DATABASE_URL_ENV_VAR = "DATABASE_URL"
ADMIN_PASSWORD_ENV_VAR = "ADMIN_PASSWORD"
APP_MODE_LOCAL = "local"
APP_MODE_CLOUD = "cloud"


@dataclass(frozen=True)
class RuntimeSettings:
    app_mode: str
    database_backend: str
    database_label: str
    is_cloud_mode: bool
    supports_shared_voting: bool
    warning: str | None = None


def _st_secret(key: str) -> str | None:
    """Read a key from st.secrets (Streamlit Cloud) without crashing locally."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        return str(val).strip() if val else None
    except Exception:
        return None


def _get_env(key: str, default: str | None = None) -> str | None:
    """os.getenv with st.secrets fallback for Streamlit Cloud."""
    value = os.getenv(key)
    if not value:
        value = _st_secret(key)
    return value.strip() if value and value.strip() else default


def get_app_mode() -> str:
    value = (_get_env(APP_MODE_ENV_VAR) or APP_MODE_LOCAL).lower()
    return value if value in {APP_MODE_LOCAL, APP_MODE_CLOUD} else APP_MODE_LOCAL


def get_admin_password() -> str:
    return _get_env(ADMIN_PASSWORD_ENV_VAR) or "admin"


def get_database_url() -> str | None:
    return _get_env(DATABASE_URL_ENV_VAR)


def get_runtime_settings() -> RuntimeSettings:
    app_mode = get_app_mode()
    database_url = get_database_url()

    if not database_url:
        return RuntimeSettings(
            app_mode=app_mode,
            database_backend="sqlite",
            database_label="SQLite local file",
            is_cloud_mode=app_mode == APP_MODE_CLOUD,
            supports_shared_voting=False,
            warning="未設定 DATABASE_URL；投票資料只會存在目前執行環境。",
        )

    if database_url.startswith("sqlite:///"):
        return RuntimeSettings(
            app_mode=app_mode,
            database_backend="sqlite",
            database_label="SQLite via DATABASE_URL",
            is_cloud_mode=app_mode == APP_MODE_CLOUD,
            supports_shared_voting=app_mode == APP_MODE_CLOUD,
            warning="SQLite 雲端部署需要 persistent disk，否則重新部署後資料可能遺失。",
        )

    if database_url.startswith(("postgresql://", "postgres://")):
        return RuntimeSettings(
            app_mode=app_mode,
            database_backend="postgres",
            database_label="Postgres / Supabase",
            is_cloud_mode=True,
            supports_shared_voting=True,
        )

    return RuntimeSettings(
        app_mode=app_mode,
        database_backend="unknown",
        database_label="Unknown database",
        is_cloud_mode=app_mode == APP_MODE_CLOUD,
        supports_shared_voting=False,
        warning="DATABASE_URL 格式無法辨識，會回到預設 SQLite 行為。",
    )
