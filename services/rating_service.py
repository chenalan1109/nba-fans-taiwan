from __future__ import annotations

from pathlib import Path

from database.db import execute_query, fetch_all, fetch_one


def submit_player_rating(
    player_id: int,
    voter_id: str,
    rating: int,
    db_path: str | Path | None = None,
) -> bool:
    normalized_voter = voter_id.strip()
    if not normalized_voter or rating not in range(1, 6):
        return False
    try:
        execute_query(
            "INSERT INTO player_ratings (player_id, voter_id, rating) VALUES (?, ?, ?)",
            (player_id, normalized_voter, rating),
            db_path=db_path,
        )
        return True
    except Exception:
        return False


def has_rated_player(player_id: int, voter_id: str, db_path: str | Path | None = None) -> bool:
    row = fetch_one(
        "SELECT id FROM player_ratings WHERE player_id = ? AND voter_id = ?",
        (player_id, voter_id.strip()),
        db_path=db_path,
    )
    return row is not None


def get_player_rating(player_id: int, voter_id: str, db_path: str | Path | None = None) -> int | None:
    row = fetch_one(
        "SELECT rating FROM player_ratings WHERE player_id = ? AND voter_id = ?",
        (player_id, voter_id.strip()),
        db_path=db_path,
    )
    return int(row["rating"]) if row is not None else None


def get_player_average_rating(player_id: int, db_path: str | Path | None = None) -> float | None:
    row = fetch_one(
        "SELECT AVG(rating) AS avg_rating FROM player_ratings WHERE player_id = ?",
        (player_id,),
        db_path=db_path,
    )
    if row is None or row["avg_rating"] is None:
        return None
    return round(float(row["avg_rating"]), 1)


def get_player_rating_count(player_id: int, db_path: str | Path | None = None) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM player_ratings WHERE player_id = ?",
        (player_id,),
        db_path=db_path,
    )
    return int(row["cnt"]) if row is not None else 0


def get_ratings_for_players(
    player_ids: list[int],
    db_path: str | Path | None = None,
) -> dict[int, dict[str, object]]:
    if not player_ids:
        return {}
    placeholders = ",".join("?" for _ in player_ids)
    rows = fetch_all(
        f"""
        SELECT player_id, AVG(rating) AS avg_rating, COUNT(*) AS cnt
        FROM player_ratings
        WHERE player_id IN ({placeholders})
        GROUP BY player_id
        """,
        tuple(player_ids),
        db_path=db_path,
    )
    return {
        int(row["player_id"]): {
            "avg": round(float(row["avg_rating"]), 1),
            "count": int(row["cnt"]),
        }
        for row in rows
    }
