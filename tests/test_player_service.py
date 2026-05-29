import math
from typing import Any, cast

from models.player import Player
from services import player_service
from services.player_service import calculate_fantasy_score, find_players, get_player_chart_data, get_player_data_quality


def test_find_players_filters_seed_data_when_api_is_unavailable(monkeypatch: Any) -> None:
    def fake_search_players(keyword: str) -> dict[str, object]:
        return {
            "source": "seed",
            "items": [
                {
                    "id": 201939,
                    "name": "Stephen Curry",
                    "team": "GSW",
                    "position": "PG",
                    "points": 26.4,
                    "rebounds": 4.5,
                    "assists": 5.1,
                    "steals": 0.9,
                    "blocks": 0.4,
                    "turnovers": 2.8,
                    "image_url": None,
                }
            ],
        }

    monkeypatch.setattr(player_service.nba_api_service, "search_players", fake_search_players)

    result = find_players("Curry")

    assert result["source"] == "seed"
    players = cast(list[Player], result["items"])
    assert players
    assert all(isinstance(player, Player) for player in players)
    assert players[0].name == "Stephen Curry"


def test_get_player_chart_data_falls_back_to_seed_data(monkeypatch: Any) -> None:
    def fake_get_player_season_stats(player_id: int) -> dict[str, object]:
        return {
            "source": "seed",
            "items": [
                {
                    "season": "2024-25",
                    "points": 26.4,
                    "rebounds": 4.5,
                    "assists": 5.1,
                }
            ],
        }

    monkeypatch.setattr(player_service.nba_api_service, "get_player_season_stats", fake_get_player_season_stats)

    result = get_player_chart_data(201939)

    assert result["source"] == "seed"
    stats = cast(list[dict[str, object]], result["items"])
    assert stats
    assert {"season", "points", "rebounds", "assists"}.issubset(stats[0].keys())


def test_calculate_fantasy_score_uses_project_formula() -> None:
    player = Player(
        id=1,
        name="Test Player",
        team="TST",
        position="G",
        points=20.0,
        rebounds=10.0,
        assists=5.0,
        steals=2.0,
        blocks=1.0,
        turnovers=3.0,
    )

    assert math.isclose(calculate_fantasy_score(player), 42.5)


def test_get_player_data_quality_reports_missing_profile_fields() -> None:
    player = Player(
        id=1,
        name="Partial Player",
        team="N/A",
        position="N/A",
        points=12.0,
        rebounds=4.0,
        assists=3.0,
    )
    stats = [{"season": "2024-25", "points": 12.0, "rebounds": 4.0, "assists": 3.0}]

    result = get_player_data_quality(player, stats)

    assert result["status"] == "partial"
    assert result["missing_fields"] == ["team", "position"]
