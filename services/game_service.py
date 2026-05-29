from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from database.db import fetch_all, fetch_one, get_connection
from models.player import Player
from services.player_service import calculate_fantasy_score


def calculate_team_score(players: list[Player]) -> float:
    if not players:
        raise ValueError("Team must include at least one player")

    return round(sum(calculate_fantasy_score(player) for player in players), 2)


def calculate_team_averages(players: list[Player]) -> dict[str, float]:
    if not players:
        raise ValueError("Team must include at least one player")

    count = len(players)
    return {
        "points": round(sum(player.points for player in players) / count, 1),
        "rebounds": round(sum(player.rebounds for player in players) / count, 1),
        "assists": round(sum(player.assists for player in players) / count, 1),
        "steals": round(sum(player.steals for player in players) / count, 1),
        "blocks": round(sum(player.blocks for player in players) / count, 1),
    }


def calculate_team_power(players: list[Player]) -> float:
    averages = calculate_team_averages(players)
    defense_score = averages["steals"] * 2 + averages["blocks"] * 2
    return round(
        averages["points"] * 0.4
        + averages["rebounds"] * 0.2
        + averages["assists"] * 0.2
        + defense_score * 0.2,
        2,
    )


def compare_teams(team_a: list[Player], team_b: list[Player]) -> dict[str, Any]:
    team_a_score = calculate_team_score(team_a)
    team_b_score = calculate_team_score(team_b)
    winner = "Team A" if team_a_score >= team_b_score else "Team B"

    return {
        "team_a_score": team_a_score,
        "team_b_score": team_b_score,
        "team_a_averages": calculate_team_averages(team_a),
        "team_b_averages": calculate_team_averages(team_b),
        "winner": winner,
    }


def simulate_matchup(team_a: list[Player], team_b: list[Player]) -> dict[str, Any]:
    team_a_power = calculate_team_power(team_a)
    team_b_power = calculate_team_power(team_b)
    total_power = team_a_power + team_b_power
    team_a_win_rate = round(team_a_power / total_power * 100, 1) if total_power else 50.0
    team_b_win_rate = round(100 - team_a_win_rate, 1)
    winner = "Team A" if team_a_power >= team_b_power else "Team B"

    return {
        "team_a_score": team_a_power,
        "team_b_score": team_b_power,
        "team_a_win_rate": team_a_win_rate,
        "team_b_win_rate": team_b_win_rate,
        "winner": winner,
        "reason": _build_matchup_reason(team_a_power, team_b_power),
    }


_SALARY_CAP = 100.0
_MAX_SAME_POSITION = 3
_REQUIRED_ROSTER_SIZE = 5


def calculate_player_salary(player: Player) -> float:
    """Fantasy score 正比換算成 salary（總 cap 100，基準分約 40 分對應 salary 10）。"""
    score = calculate_fantasy_score(player)
    return round(max(1.0, score / 4), 1)


def calculate_total_salary(players: list[Player]) -> float:
    return round(sum(calculate_player_salary(p) for p in players), 1)


def validate_fantasy_roster(
    players: list[Player], salary_cap: float | None = None
) -> list[str]:
    """回傳違規說明清單；空列表代表合法陣容。salary_cap=None 表示無上限。"""
    errors: list[str] = []
    if len(players) != _REQUIRED_ROSTER_SIZE:
        errors.append(f"必須選滿 {_REQUIRED_ROSTER_SIZE} 名球員（目前 {len(players)} 名）。")

    ids = [p.id for p in players]
    if len(ids) != len(set(ids)):
        errors.append("陣容中有重複的球員。")

    if salary_cap is not None:
        total_salary = calculate_total_salary(players)
        if total_salary > salary_cap:
            errors.append(f"總 Salary {total_salary:.1f} 超過上限 {salary_cap:.0f}。")

    position_counts: dict[str, int] = {}
    for p in players:
        position_counts[p.position] = position_counts.get(p.position, 0) + 1
    for pos, count in position_counts.items():
        if count > _MAX_SAME_POSITION:
            errors.append(f"同一位置（{pos}）最多 {_MAX_SAME_POSITION} 名，目前有 {count} 名。")

    return errors


def validate_matchup_lineup(team_a: list[Player], team_b: list[Player]) -> list[str]:
    errors: list[str] = []
    if not (1 <= len(team_a) <= 5):
        errors.append(f"Team A must include 1–5 players; got {len(team_a)}.")
    if not (1 <= len(team_b) <= 5):
        errors.append(f"Team B must include 1–5 players; got {len(team_b)}.")
    if 1 <= len(team_a) <= 5 and 1 <= len(team_b) <= 5 and len(team_a) != len(team_b):
        errors.append(f"Both teams must have the same number of players (Team A: {len(team_a)}, Team B: {len(team_b)}).")

    team_a_ids = {player.id for player in team_a}
    team_b_ids = {player.id for player in team_b}
    if team_a_ids & team_b_ids:
        errors.append("The same player cannot appear on both teams.")

    return errors


def get_matchup_explanation() -> str:
    return (
        "team_power = avg_points * 0.4 + avg_rebounds * 0.2 "
        "+ avg_assists * 0.2 + defense_score * 0.2\n"
        "defense_score = avg_steals * 2 + avg_blocks * 2\n\n"
        "This is a simplified course-project model. It compares roster profiles; "
        "it is not a real NBA prediction model."
    )


def save_fantasy_team(
    owner_name: str,
    team_name: str,
    players: list[Player],
    db_path: str | Path | None = None,
) -> int:
    normalized_owner = owner_name.strip()
    normalized_team = team_name.strip()
    if not normalized_owner or not normalized_team:
        raise ValueError("Owner name and team name are required")
    if len(players) != 5:
        raise ValueError("Fantasy team must include exactly 5 players")

    total_score = calculate_team_score(players)
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO fantasy_teams (owner_name, team_name, total_score)
            VALUES (?, ?, ?)
            """,
            (normalized_owner, normalized_team, total_score),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to create fantasy team")
        fantasy_team_id = cursor.lastrowid

        for player in players:
            connection.execute(
                """
                INSERT INTO fantasy_team_players (fantasy_team_id, player_id, player_name)
                VALUES (?, ?, ?)
                """,
                (fantasy_team_id, player.id, player.name),
            )

    return fantasy_team_id


def submit_matchup_vote(
    matchup_id: str,
    voter_id: str,
    selected_side: str,
    db_path: str | Path | None = None,
) -> bool:
    normalized_matchup = matchup_id.strip()
    normalized_voter = voter_id.strip()
    normalized_side = selected_side.strip().upper()
    if not normalized_matchup or not normalized_voter or normalized_side not in {"A", "B"}:
        return False

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO matchup_votes (matchup_id, voter_id, selected_side)
                VALUES (?, ?, ?)
                """,
                (normalized_matchup, normalized_voter, normalized_side),
            )
        return True
    except Exception:
        return False


def has_voted_matchup(matchup_id: str, voter_id: str, db_path: str | Path | None = None) -> bool:
    row = fetch_one(
        "SELECT id FROM matchup_votes WHERE matchup_id = ? AND voter_id = ?",
        (matchup_id.strip(), voter_id.strip()),
        db_path=db_path,
    )
    return row is not None


def get_matchup_selected_side(
    matchup_id: str,
    voter_id: str,
    db_path: str | Path | None = None,
) -> str | None:
    row = fetch_one(
        "SELECT selected_side FROM matchup_votes WHERE matchup_id = ? AND voter_id = ?",
        (matchup_id.strip(), voter_id.strip()),
        db_path=db_path,
    )
    return str(row["selected_side"]) if row is not None else None


def get_matchup_vote_summary(matchup_id: str, db_path: str | Path | None = None) -> dict[str, int]:
    summary = {"A": 0, "B": 0}
    rows = fetch_all(
        """
        SELECT selected_side, COUNT(*) AS vote_count
        FROM matchup_votes
        WHERE matchup_id = ?
        GROUP BY selected_side
        """,
        (matchup_id.strip(),),
        db_path=db_path,
    )
    for row in rows:
        summary[str(row["selected_side"])] = int(row["vote_count"])
    return summary


def save_custom_matchup(
    title: str,
    team_a_name: str,
    team_b_name: str,
    team_a_players: list[str],
    team_b_players: list[str],
    creator_id: str = "",
    db_path: str | Path | None = None,
) -> str:
    matchup_id = f"custom-{int(time.time() * 1000)}"
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO custom_matchups (id, title, team_a_name, team_b_name, team_a_players, team_b_players, creator_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (matchup_id, title.strip(), team_a_name.strip(), team_b_name.strip(), json.dumps(team_a_players), json.dumps(team_b_players), creator_id.strip()),
        )
    return matchup_id


def get_matchup_creator(matchup_id: str, db_path: str | Path | None = None) -> str | None:
    row = fetch_one(
        "SELECT creator_id FROM custom_matchups WHERE id = ?",
        (matchup_id.strip(),),
        db_path=db_path,
    )
    return str(row["creator_id"]) if row and row["creator_id"] else None


def delete_custom_matchup(matchup_id: str, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM matchup_votes WHERE matchup_id = ?", (matchup_id,))
        conn.execute("DELETE FROM custom_matchups WHERE id = ?", (matchup_id,))


def get_all_matchup_vote_counts(db_path: str | Path | None = None) -> dict[str, int]:
    rows = fetch_all(
        "SELECT matchup_id, COUNT(*) AS vote_count FROM matchup_votes GROUP BY matchup_id",
        db_path=db_path,
    )
    return {str(row["matchup_id"]): int(row["vote_count"]) for row in rows}


def get_custom_matchups(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT id, title, team_a_name, team_b_name, team_a_players, team_b_players, creator_id FROM custom_matchups ORDER BY created_at DESC",
        db_path=db_path,
    )
    return [
        {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "team_a_name": str(row["team_a_name"]),
            "team_b_name": str(row["team_b_name"]),
            "team_a_players": json.loads(str(row["team_a_players"])),
            "team_b_players": json.loads(str(row["team_b_players"])),
            "creator_id": str(row["creator_id"]) if row["creator_id"] else "",
        }
        for row in rows
    ]


def _build_matchup_reason(team_a_power: float, team_b_power: float) -> str:
    if team_a_power == team_b_power:
        return "兩隊模型分數相同，這會是一場接近的對決。"
    winner = "Team A" if team_a_power > team_b_power else "Team B"
    gap = abs(team_a_power - team_b_power)
    return f"{winner} 在綜合得分、籃板、助攻與防守權重中領先 {gap:.2f} 分。"
