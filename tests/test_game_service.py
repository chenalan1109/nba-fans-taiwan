from pathlib import Path

import pytest

from database.db import fetch_all, init_db
from models.player import Player
from services.game_service import (
    calculate_team_score,
    compare_teams,
    get_matchup_selected_side,
    get_matchup_vote_summary,
    get_matchup_explanation,
    has_voted_matchup,
    save_fantasy_team,
    simulate_matchup,
    submit_matchup_vote,
    validate_matchup_lineup,
)


def _player(
    player_id: int,
    name: str,
    points: float,
    rebounds: float = 5.0,
    assists: float = 5.0,
    steals: float = 1.0,
    blocks: float = 1.0,
    turnovers: float = 2.0,
) -> Player:
    return Player(
        id=player_id,
        name=name,
        team="TST",
        position="G",
        points=points,
        rebounds=rebounds,
        assists=assists,
        steals=steals,
        blocks=blocks,
        turnovers=turnovers,
    )


def test_calculate_team_score_requires_players() -> None:
    with pytest.raises(ValueError):
        calculate_team_score([])


def test_compare_teams_returns_expected_winner() -> None:
    team_a = [_player(1, "A1", 30), _player(2, "A2", 25)]
    team_b = [_player(3, "B1", 10), _player(4, "B2", 12)]

    result = compare_teams(team_a, team_b)

    assert result["winner"] == "Team A"
    assert result["team_a_score"] > result["team_b_score"]


def test_simulate_matchup_contains_scores_and_win_rates() -> None:
    team_a = [_player(1, "A1", 30)]
    team_b = [_player(2, "B1", 20)]

    result = simulate_matchup(team_a, team_b)

    assert result["winner"] == "Team A"
    assert result["team_a_score"] > result["team_b_score"]
    assert result["team_a_win_rate"] + result["team_b_win_rate"] == 100.0


def test_save_fantasy_team_writes_team_and_players(tmp_path: Path) -> None:
    db_path = tmp_path / "game.db"
    init_db(db_path)
    players = [_player(index, f"Player {index}", 20 + index) for index in range(1, 6)]

    team_id = save_fantasy_team("maurice", "Taipei Shooters", players, db_path)
    team_rows = fetch_all("SELECT * FROM fantasy_teams WHERE id = ?", (team_id,), db_path)
    player_rows = fetch_all("SELECT * FROM fantasy_team_players WHERE fantasy_team_id = ?", (team_id,), db_path)

    assert team_rows[0]["owner_name"] == "maurice"
    assert team_rows[0]["team_name"] == "Taipei Shooters"
    assert len(player_rows) == 5


def test_matchup_vote_prevents_duplicate_voter(tmp_path: Path) -> None:
    db_path = tmp_path / "game.db"
    init_db(db_path)

    assert submit_matchup_vote("old-vs-new", "maurice", "A", db_path) is True
    assert submit_matchup_vote("old-vs-new", "maurice", "B", db_path) is False
    assert has_voted_matchup("old-vs-new", "maurice", db_path) is True
    assert get_matchup_selected_side("old-vs-new", "maurice", db_path) == "A"
    assert get_matchup_vote_summary("old-vs-new", db_path) == {"A": 1, "B": 0}


def test_validate_matchup_lineup_requires_five_players_per_team() -> None:
    team_a = [_player(index, f"A{index}", 20) for index in range(1, 6)]
    team_b = [_player(index + 10, f"B{index}", 20) for index in range(1, 5)]

    errors = validate_matchup_lineup(team_a, team_b)

    assert errors == ["Team B must include exactly 5 players; got 4."]


def test_validate_matchup_lineup_rejects_duplicate_players() -> None:
    shared = _player(1, "Shared", 20)
    team_a = [shared] + [_player(index, f"A{index}", 20) for index in range(2, 6)]
    team_b = [shared] + [_player(index + 10, f"B{index}", 20) for index in range(2, 6)]

    errors = validate_matchup_lineup(team_a, team_b)

    assert errors == ["The same player cannot appear on both teams."]


def test_get_matchup_explanation_includes_formula() -> None:
    explanation = get_matchup_explanation()

    assert "team_power" in explanation
    assert "defense_score" in explanation
