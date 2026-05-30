"""帳號認證服務：註冊、登入、帳號管理。

使用 SHA-256 雜湊儲存密碼（無外部依賴）。
帳號建立時自動在 prophet_users 建立初始 500 先知幣紀錄。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from database.db import execute_query, fetch_one


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(
    username: str,
    password: str,
    nickname: str,
    db_path: str | Path | None = None,
) -> tuple[bool, str]:
    """Register a new account. Returns (success, error_message)."""
    username = username.strip()
    nickname = nickname.strip()
    password = password.strip()

    if not username:
        return False, "帳號不能為空。"
    if not password or len(password) < 4:
        return False, "密碼至少需要 4 個字元。"
    if not nickname:
        return False, "暱稱不能為空。"
    if len(username) > 30:
        return False, "帳號長度不能超過 30 字元。"
    if len(nickname) > 20:
        return False, "暱稱長度不能超過 20 字元。"

    existing = fetch_one(
        "SELECT id FROM user_accounts WHERE username = ?",
        (username,),
        db_path=db_path,
    )
    if existing:
        return False, "此帳號已被使用，請換一個。"

    nick_taken = fetch_one(
        "SELECT id FROM user_accounts WHERE nickname = ?",
        (nickname,),
        db_path=db_path,
    )
    if nick_taken:
        return False, "此暱稱已被使用，請換一個。"

    pw_hash = _hash_password(password)
    try:
        execute_query(
            "INSERT INTO user_accounts (username, password_hash, nickname) VALUES (?, ?, ?)",
            (username, pw_hash, nickname),
            db_path=db_path,
        )
        # Give the new user 1000 prophet coins
        execute_query(
            "INSERT OR IGNORE INTO prophet_users (nickname, coins) VALUES (?, 1000)",
            (nickname,),
            db_path=db_path,
        )
        return True, ""
    except Exception as exc:
        return False, f"註冊失敗：{exc}"


def login_user(
    username: str,
    password: str,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Verify credentials and return user dict, or None on failure."""
    username = username.strip()
    pw_hash = _hash_password(password.strip())
    row = fetch_one(
        "SELECT id, username, nickname FROM user_accounts WHERE username = ? AND password_hash = ?",
        (username, pw_hash),
        db_path=db_path,
    )
    if not row:
        return None
    return {"id": int(row["id"]), "username": str(row["username"]), "nickname": str(row["nickname"])}


def get_account(username: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    """Return account info (without password_hash) for the given username."""
    row = fetch_one(
        "SELECT id, username, nickname, created_at FROM user_accounts WHERE username = ?",
        (username,),
        db_path=db_path,
    )
    return dict(row) if row else None  # type: ignore[arg-type]


def is_admin_user(user: dict[str, Any] | None) -> bool:
    """Return True if the logged-in user is the configured admin account."""
    from config.settings import get_admin_username
    if not user:
        return False
    return str(user.get("username", "")).lower() == get_admin_username().lower()


def seed_admin_account(db_path: str | Path | None = None) -> None:
    """Create the admin account on first run if it doesn't already exist."""
    from config.settings import get_admin_password, get_admin_username
    username = get_admin_username()
    if fetch_one("SELECT id FROM user_accounts WHERE username = ?", (username,), db_path=db_path):
        return
    pw_hash = _hash_password(get_admin_password())
    try:
        execute_query(
            "INSERT OR IGNORE INTO user_accounts (username, password_hash, nickname) VALUES (?, ?, ?)",
            (username, pw_hash, username),
            db_path=db_path,
        )
        execute_query(
            "INSERT OR IGNORE INTO prophet_users (nickname, coins) VALUES (?, 1000)",
            (username,),
            db_path=db_path,
        )
    except Exception:
        pass


def change_password(
    username: str,
    old_password: str,
    new_password: str,
    db_path: str | Path | None = None,
) -> tuple[bool, str]:
    """Change password after verifying old password."""
    new_password = new_password.strip()
    if not new_password or len(new_password) < 4:
        return False, "新密碼至少需要 4 個字元。"
    if not login_user(username, old_password, db_path):
        return False, "舊密碼錯誤。"
    new_hash = _hash_password(new_password)
    execute_query(
        "UPDATE user_accounts SET password_hash = ? WHERE username = ?",
        (new_hash, username),
        db_path=db_path,
    )
    return True, ""


def list_all_users(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return all user accounts (id, username, nickname, created_at)."""
    from database.db import fetch_all
    rows = fetch_all(
        "SELECT id, username, nickname, created_at FROM user_accounts ORDER BY created_at DESC",
        db_path=db_path,
    )
    return [dict(r) for r in rows]  # type: ignore[arg-type]


def delete_user(username: str, db_path: str | Path | None = None) -> tuple[bool, str]:
    """Delete a user account and all associated records."""
    account = get_account(username, db_path)
    if not account:
        return False, f"找不到帳號「{username}」。"
    nickname = str(account["nickname"])
    try:
        execute_query("DELETE FROM user_accounts WHERE username = ?", (username,), db_path=db_path)
        execute_query("DELETE FROM prophet_users WHERE nickname = ?", (nickname,), db_path=db_path)
        execute_query("DELETE FROM user_player_pool WHERE username = ?", (username,), db_path=db_path)
        execute_query("DELETE FROM daily_checkins WHERE username = ?", (username,), db_path=db_path)
        return True, f"帳號「{username}」已刪除。"
    except Exception as exc:
        return False, f"刪除失敗：{exc}"


def add_coins_to_user(nickname: str, amount: int, db_path: str | Path | None = None) -> tuple[bool, str]:
    """Add (or subtract) coins from a user. Amount may be negative to deduct."""
    from database.db import fetch_one as _fetch_one
    row = _fetch_one("SELECT coins FROM prophet_users WHERE nickname = ?", (nickname,), db_path=db_path)
    if not row:
        return False, f"找不到暱稱「{nickname}」的先知幣紀錄。"
    execute_query(
        "UPDATE prophet_users SET coins = coins + ? WHERE nickname = ?",
        (amount, nickname),
        db_path=db_path,
    )
    return True, f"已為「{nickname}」{'增加' if amount >= 0 else '扣除'} {abs(amount)} 先知幣。"
