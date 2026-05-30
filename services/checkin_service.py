"""每日簽到服務：每天一次，給予 150 先知幣。"""
from __future__ import annotations

import datetime

from database.db import execute_query, fetch_one

_DAILY_COINS = 50


def can_checkin_today(username: str) -> bool:
    today = datetime.date.today().isoformat()
    row = fetch_one(
        "SELECT id FROM daily_checkins WHERE username=? AND checkin_date=?",
        (username, today),
    )
    return row is None


def do_checkin(username: str, nickname: str) -> tuple[bool, str]:
    today = datetime.date.today().isoformat()
    try:
        execute_query(
            "INSERT INTO daily_checkins (username, checkin_date, coins_earned) VALUES (?, ?, ?)",
            (username, today, _DAILY_COINS),
        )
    except Exception:
        return False, "今天已經簽到過了！"
    execute_query(
        "UPDATE prophet_users SET coins = coins + ? WHERE nickname = ?",
        (_DAILY_COINS, nickname),
    )
    return True, f"簽到成功！獲得 {_DAILY_COINS} 先知幣"


def get_checkin_count(username: str) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM daily_checkins WHERE username=?",
        (username,),
    )
    return int(row["cnt"]) if row else 0
