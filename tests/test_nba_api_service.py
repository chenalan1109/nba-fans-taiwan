from typing import Any

import pytest

from services import nba_api_service


class FakeResponse:
    def __init__(self, payload: dict[str, Any], text: str = "{}", status_error: Exception | None = None) -> None:
        self._payload = payload
        self.text = text
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error:
            raise self._status_error

    def json(self) -> dict[str, Any]:
        return self._payload


def test_get_scoreboard_uses_cdn_response(monkeypatch: Any) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(
            {
                "scoreboard": {
                    "games": [
                        {
                            "gameTimeUTC": "2026-05-16T00:00:00Z",
                            "gameStatusText": "Final",
                            "homeTeam": {"teamName": "Lakers", "score": 112},
                            "awayTeam": {"teamName": "Warriors", "score": 108},
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(nba_api_service.requests, "get", fake_get)

    result = nba_api_service.get_scoreboard()

    assert result["source"] == "api"
    assert result["items"][0]["home_team"] == "Lakers"
    assert result["items"][0]["away_score"] == 108


def test_get_scoreboard_falls_back_to_seed_when_api_paths_fail(monkeypatch: Any) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        raise TimeoutError("cdn timeout")

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "nba_api.live.nba.endpoints":
            raise ImportError("nba_api live unavailable")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr(nba_api_service.requests, "get", fake_get)
    monkeypatch.setattr("builtins.__import__", fake_import)

    result = nba_api_service.get_scoreboard()

    assert result["source"] == "seed"
    assert result["items"]
    assert "cdn timeout" in result["error"]
    assert "nba_api live unavailable" in result["error"]


def test_data_mode_seed_forces_seed_responses(monkeypatch: Any) -> None:
    monkeypatch.setenv(nba_api_service.DATA_MODE_ENV_VAR, nba_api_service.DATA_MODE_SEED)

    scoreboard = nba_api_service.get_scoreboard()
    players = nba_api_service.search_players("Curry")
    stats = nba_api_service.get_player_season_stats(201939)

    assert nba_api_service.get_data_mode() == "seed"
    assert scoreboard["source"] == "seed"
    assert players["source"] == "seed"
    assert stats["source"] == "seed"


def test_normalize_career_row_converts_totals_to_per_game() -> None:
    row = {
        "SEASON_ID": "2024-25",
        "TEAM_ABBREVIATION": "SAS",
        "GP": 10,
        "PTS": 250,
        "REB": 100,
        "AST": 50,
        "STL": 20,
        "BLK": 30,
        "TOV": 40,
    }

    result = nba_api_service._normalize_career_row(row)

    assert result == {
        "season": "2024-25",
        "team": "SAS",
        "games": 10,
        "points": 25.0,
        "rebounds": 10.0,
        "assists": 5.0,
        "steals": 2.0,
        "blocks": 3.0,
        "turnovers": 4.0,
    }
