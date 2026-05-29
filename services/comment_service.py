from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import get_admin_password
from database.db import execute_query, fetch_all, fetch_one


def add_comment(
    game_id: str,
    voter_id: str,
    content: str,
    db_path: str | Path | None = None,
) -> bool:
    voter_id = voter_id.strip()
    content = content.strip()
    if not voter_id or not content or not game_id:
        return False
    try:
        execute_query(
            "INSERT INTO game_comments (game_id, voter_id, content) VALUES (?, ?, ?)",
            (game_id, voter_id, content),
            db_path=db_path,
        )
        return True
    except Exception:
        return False


def get_comments(game_id: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT gc.id, gc.voter_id, gc.content, gc.created_at,
               COUNT(cl.id) AS like_count
        FROM game_comments gc
        LEFT JOIN comment_likes cl ON cl.comment_id = gc.id
        WHERE gc.game_id = ?
        GROUP BY gc.id
        ORDER BY gc.created_at ASC
        """,
        (game_id,),
        db_path=db_path,
    )
    return [
        {
            "id": int(row["id"]),
            "voter_id": str(row["voter_id"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
            "like_count": int(row["like_count"]),
        }
        for row in rows
    ]


def delete_comment(
    comment_id: int,
    voter_id: str,
    db_path: str | Path | None = None,
) -> bool:
    voter_id = voter_id.strip()
    is_admin = bool(voter_id) and voter_id == get_admin_password()
    try:
        if is_admin:
            execute_query(
                "DELETE FROM game_comments WHERE id = ?",
                (comment_id,),
                db_path=db_path,
            )
        else:
            execute_query(
                "DELETE FROM game_comments WHERE id = ? AND voter_id = ?",
                (comment_id, voter_id),
                db_path=db_path,
            )
        return True
    except Exception:
        return False


def like_comment(
    comment_id: int,
    voter_id: str,
    db_path: str | Path | None = None,
) -> bool:
    voter_id = voter_id.strip()
    if not voter_id:
        return False
    try:
        execute_query(
            "INSERT INTO comment_likes (comment_id, voter_id) VALUES (?, ?)",
            (comment_id, voter_id),
            db_path=db_path,
        )
        return True
    except Exception:
        return False


def unlike_comment(
    comment_id: int,
    voter_id: str,
    db_path: str | Path | None = None,
) -> bool:
    voter_id = voter_id.strip()
    if not voter_id:
        return False
    try:
        execute_query(
            "DELETE FROM comment_likes WHERE comment_id = ? AND voter_id = ?",
            (comment_id, voter_id),
            db_path=db_path,
        )
        return True
    except Exception:
        return False


def has_liked_comment(
    comment_id: int,
    voter_id: str,
    db_path: str | Path | None = None,
) -> bool:
    if not voter_id.strip():
        return False
    row = fetch_one(
        "SELECT id FROM comment_likes WHERE comment_id = ? AND voter_id = ?",
        (comment_id, voter_id.strip()),
        db_path=db_path,
    )
    return row is not None
