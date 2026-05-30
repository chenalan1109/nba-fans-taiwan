"""球員市場服務：定價、購買、球員池管理。

先知幣來自 prophet_users 表（帳號建立時給予 500 枚）。
購買後球員進入 user_player_pool，Fantasy Team 只能使用池內球員。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from database.db import execute_query, fetch_all, fetch_one, get_connection
from models.player import Player
from services.player_service import calculate_fantasy_score


def get_player_price(player: Player) -> int:
    """Calculate purchase price in prophet coins based on fantasy score."""
    score = calculate_fantasy_score(player)
    return max(30, int(score * 3))


def get_user_coins(nickname: str, db_path: str | Path | None = None) -> int:
    """Return current coin balance for a user's nickname in prophet_users."""
    row = fetch_one(
        "SELECT coins FROM prophet_users WHERE nickname = ?",
        (nickname,),
        db_path=db_path,
    )
    return int(row["coins"]) if row else 0


def has_player(username: str, player_id: int, db_path: str | Path | None = None) -> bool:
    """Return True if the user already owns this player."""
    row = fetch_one(
        "SELECT id FROM user_player_pool WHERE username = ? AND player_id = ?",
        (username, player_id),
        db_path=db_path,
    )
    return row is not None


def buy_player(
    username: str,
    nickname: str,
    player: Player,
    db_path: str | Path | None = None,
) -> tuple[bool, str]:
    """Deduct coins and add player to user's pool. Returns (success, message)."""
    if has_player(username, player.id, db_path):
        return False, f"你已擁有 {player.name}。"

    price = get_player_price(player)
    coins = get_user_coins(nickname, db_path)
    if coins < price:
        return False, f"先知幣不足（需要 {price} 枚，目前 {coins} 枚）。"

    try:
        with get_connection(db_path) as conn:
            conn.execute(
                "UPDATE prophet_users SET coins = coins - ? WHERE nickname = ?",
                (price, nickname),
            )
        execute_query(
            "INSERT OR IGNORE INTO user_player_pool (username, player_id, player_name) VALUES (?, ?, ?)",
            (username, player.id, player.name),
            db_path=db_path,
        )
        return True, f"成功購買 {player.name}！花費 {price} 先知幣。"
    except Exception as exc:
        return False, f"購買失敗：{exc}"


def get_user_player_pool_ids(username: str, db_path: str | Path | None = None) -> set[int]:
    """Return set of player_ids owned by this user."""
    rows = fetch_all(
        "SELECT player_id FROM user_player_pool WHERE username = ?",
        (username,),
        db_path=db_path,
    )
    return {int(r["player_id"]) for r in rows}


def get_user_pool_records(username: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return all pool records for this user."""
    rows = fetch_all(
        "SELECT player_id, player_name, purchased_at FROM user_player_pool WHERE username = ? ORDER BY purchased_at DESC",
        (username,),
        db_path=db_path,
    )
    return [dict(r) for r in rows]  # type: ignore[arg-type]
