from __future__ import annotations

import os
from typing import Any

import requests

from database.seed_data import get_seed_boxscore, get_seed_officials, get_seed_player_stats, get_seed_players, get_seed_recent_games, get_seed_scoreboard


NBA_CDN_SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
NBA_REQUEST_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
}
DATA_MODE_ENV_VAR = "NBA_DATA_MODE"
DATA_MODE_AUTO = "auto"
DATA_MODE_SEED = "seed"


def get_data_mode() -> str:
    configured_mode = os.getenv(DATA_MODE_ENV_VAR, DATA_MODE_AUTO).strip().lower()
    return configured_mode if configured_mode in {DATA_MODE_AUTO, DATA_MODE_SEED} else DATA_MODE_AUTO


def _is_seed_mode() -> bool:
    return get_data_mode() == DATA_MODE_SEED


def _seed_response(items: list[dict[str, Any]], error: str | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {
        "source": "seed",
        "items": items,
    }
    if error:
        response["error"] = error
    return response


def _api_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source": "api",
        "items": items,
    }


def _partial_api_response(items: list[dict[str, Any]], error: str | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {
        "source": "partial_api",
        "items": items,
    }
    if error:
        response["error"] = error
    return response


_NBA_HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png"


def _normalize_seed_player(raw_player: dict[str, Any]) -> dict[str, Any]:
    player_id = int(raw_player["id"])
    image_url = raw_player.get("image_url") or _NBA_HEADSHOT_URL.format(player_id=player_id)
    return {
        "id": player_id,
        "name": str(raw_player["name"]),
        "team": str(raw_player.get("team") or "N/A"),
        "position": str(raw_player.get("position") or "N/A"),
        "points": float(raw_player.get("points") or 0.0),
        "rebounds": float(raw_player.get("rebounds") or 0.0),
        "assists": float(raw_player.get("assists") or 0.0),
        "steals": float(raw_player.get("steals") or 0.0),
        "blocks": float(raw_player.get("blocks") or 0.0),
        "turnovers": float(raw_player.get("turnovers") or 0.0),
        "image_url": image_url,
    }


def get_scoreboard() -> dict[str, Any]:
    """Return scoreboard data in a stable app format."""
    if _is_seed_mode():
        return _seed_response(get_seed_scoreboard(), f"{DATA_MODE_ENV_VAR}=seed")

    errors: list[str] = []

    try:
        return _api_response(_get_scoreboard_from_cdn())
    except Exception as exc:
        errors.append(f"cdn.nba.com: {exc}")

    try:
        from nba_api.live.nba.endpoints import scoreboard
        board = scoreboard.ScoreBoard()
        games_data = board.games.get_dict()
        games = games_data if isinstance(games_data, list) else games_data.get("games", [])
        return _api_response(_normalize_games(games))
    except Exception as exc:
        errors.append(f"nba_api live scoreboard: {exc}")

    return _seed_response(get_seed_scoreboard(), " | ".join(errors))


def search_players(keyword: str) -> dict[str, Any]:
    keyword = keyword.strip()
    seed_players = [_normalize_seed_player(player) for player in get_seed_players()]

    if _is_seed_mode():
        items = seed_players if not keyword else _filter_seed_players(keyword, seed_players)
        return _seed_response(items, f"{DATA_MODE_ENV_VAR}=seed")

    if not keyword:
        return _seed_response(seed_players)

    try:
        from nba_api.stats.static import players

        api_players = players.find_players_by_full_name(keyword)
        items = [
            {
                "id": int(player["id"]),
                "name": str(player["full_name"]),
                "team": "N/A",
                "position": "N/A",
                "points": 0.0,
                "rebounds": 0.0,
                "assists": 0.0,
                "steals": 0.0,
                "blocks": 0.0,
                "turnovers": 0.0,
                "image_url": None,
            }
            for player in api_players
        ]
        return _api_response(items) if items else _seed_response(_filter_seed_players(keyword, seed_players))
    except Exception as exc:
        return _seed_response(_filter_seed_players(keyword, seed_players), str(exc))


def get_player_profile(player_id: int) -> dict[str, Any]:
    seed_player = _find_seed_player(player_id)

    if _is_seed_mode():
        return _seed_response([seed_player] if seed_player else [], f"{DATA_MODE_ENV_VAR}=seed")

    static_player: dict[str, Any] | None = None
    try:
        from nba_api.stats.static import players

        player = players.find_player_by_id(player_id)
        if player:
            static_player = {
                "id": int(player["id"]),
                "name": str(player["full_name"]),
                "team": "N/A",
                "position": "N/A",
                "points": 0.0,
                "rebounds": 0.0,
                "assists": 0.0,
                "steals": 0.0,
                "blocks": 0.0,
                "turnovers": 0.0,
                "image_url": None,
            }
    except Exception:
        static_player = None

    profile_errors: list[str] = []
    common_info = _get_common_player_info(player_id, profile_errors)
    stats_response = get_player_season_stats(player_id)
    stats_items = stats_response.get("items", [])
    latest_stats = stats_items[-1] if stats_items else None

    if static_player is None and seed_player is None:
        return _seed_response([], "player not found")

    base_player = dict(static_player or seed_player or {})
    if common_info:
        base_player.update(common_info)
    if latest_stats:
        base_player.update(
            {
                "team": common_info.get("team") if common_info and common_info.get("team") != "N/A" else latest_stats.get("team", "N/A"),
                "points": latest_stats.get("points", 0.0),
                "rebounds": latest_stats.get("rebounds", 0.0),
                "assists": latest_stats.get("assists", 0.0),
                "steals": latest_stats.get("steals", 0.0),
                "blocks": latest_stats.get("blocks", 0.0),
                "turnovers": latest_stats.get("turnovers", 0.0),
            }
        )

    has_complete_profile = base_player.get("team") != "N/A" and base_player.get("position") != "N/A"
    has_api_stats = stats_response.get("source") == "api"
    if has_complete_profile and has_api_stats:
        return _api_response([base_player])
    if has_api_stats or static_player is not None:
        error = " | ".join(profile_errors) if profile_errors else None
        return _partial_api_response([base_player], error)

    try:
        from nba_api.stats.static import players

        player = players.find_player_by_id(player_id)
        if not player:
            return _seed_response([seed_player] if seed_player else [])

        detail = {
            "id": int(player["id"]),
            "name": str(player["full_name"]),
            "team": seed_player["team"] if seed_player else "N/A",
            "position": seed_player["position"] if seed_player else "N/A",
            "points": seed_player["points"] if seed_player else 0.0,
            "rebounds": seed_player["rebounds"] if seed_player else 0.0,
            "assists": seed_player["assists"] if seed_player else 0.0,
            "steals": seed_player["steals"] if seed_player else 0.0,
            "blocks": seed_player["blocks"] if seed_player else 0.0,
            "turnovers": seed_player["turnovers"] if seed_player else 0.0,
            "image_url": None,
        }
        return _api_response([detail])
    except Exception as exc:
        return _seed_response([seed_player] if seed_player else [], str(exc))


def get_player_season_stats(player_id: int) -> dict[str, Any]:
    if _is_seed_mode():
        return _seed_response(get_seed_player_stats(player_id), f"{DATA_MODE_ENV_VAR}=seed")

    try:
        from nba_api.stats.endpoints import playercareerstats

        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        data_frame = career.get_data_frames()[0]
        items = [_normalize_career_row(row) for row in data_frame.tail(5).to_dict("records")]
        return _api_response(items)
    except Exception as exc:
        return _seed_response(get_seed_player_stats(player_id), str(exc))


def _filter_seed_players(keyword: str, seed_players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_keyword = keyword.casefold()
    return [
        player
        for player in seed_players
        if normalized_keyword in str(player["name"]).casefold()
        or normalized_keyword in str(player["team"]).casefold()
        or normalized_keyword in str(player["position"]).casefold()
    ]


def _find_seed_player(player_id: int) -> dict[str, Any] | None:
    for player in get_seed_players():
        if int(player["id"]) == player_id:
            return _normalize_seed_player(player)
    return None


def _get_common_player_info(player_id: int, errors: list[str]) -> dict[str, Any] | None:
    try:
        from nba_api.stats.endpoints import commonplayerinfo

        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        data_frame = info.get_data_frames()[0]
        records = data_frame.to_dict("records")
        if not records:
            return None
        row = records[0]
        return {
            "team": str(row.get("TEAM_ABBREVIATION") or "N/A"),
            "position": str(row.get("POSITION") or "N/A"),
        }
    except Exception as exc:
        errors.append(f"common player info unavailable: {exc}")
        return None


def _safe_per_game(row: dict[str, Any], key: str, games_played: float) -> float:
    if games_played <= 0:
        return 0.0
    return round(float(row.get(key) or 0.0) / games_played, 1)


def _normalize_career_row(row: dict[str, Any]) -> dict[str, Any]:
    games_played = float(row.get("GP") or 0.0)
    return {
        "season": str(row.get("SEASON_ID") or ""),
        "team": str(row.get("TEAM_ABBREVIATION") or "N/A"),
        "games": int(games_played),
        "points": _safe_per_game(row, "PTS", games_played),
        "rebounds": _safe_per_game(row, "REB", games_played),
        "assists": _safe_per_game(row, "AST", games_played),
        "steals": _safe_per_game(row, "STL", games_played),
        "blocks": _safe_per_game(row, "BLK", games_played),
        "turnovers": _safe_per_game(row, "TOV", games_played),
    }


def _get_scoreboard_from_cdn() -> list[dict[str, Any]]:
    response = requests.get(
        NBA_CDN_SCOREBOARD_URL,
        headers=NBA_REQUEST_HEADERS,
        timeout=8,
    )
    response.raise_for_status()

    if not response.text.strip():
        raise ValueError("empty response body")

    payload = response.json()
    scoreboard = payload.get("scoreboard", {})
    games = scoreboard.get("games", [])
    if not isinstance(games, list):
        raise TypeError("scoreboard.games is not a list")

    return _normalize_games(games)


def _normalize_games(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_normalize_live_game(game) for game in games]


def get_game_boxscore(game_id: str) -> dict[str, Any]:
    """Return player-level box score for a game."""
    if not game_id:
        return _seed_response([], "no game_id provided")

    if _is_seed_mode():
        return _seed_response(get_seed_boxscore(game_id), f"{DATA_MODE_ENV_VAR}=seed")

    try:
        from nba_api.live.nba.endpoints import boxscore as boxscore_ep

        board = boxscore_ep.BoxScore(game_id=game_id)
        home_players = _normalize_boxscore_players(board.home_team.get_dict(), "home")
        away_players = _normalize_boxscore_players(board.away_team.get_dict(), "away")
        return _api_response(home_players + away_players)
    except Exception as exc:
        pass

    try:
        cdn_url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
        response = requests.get(cdn_url, headers=NBA_REQUEST_HEADERS, timeout=8)
        response.raise_for_status()
        payload = response.json()
        game_data = payload.get("game", {})
        home_players = _normalize_boxscore_players(game_data.get("homeTeam", {}), "home")
        away_players = _normalize_boxscore_players(game_data.get("awayTeam", {}), "away")
        return _api_response(home_players + away_players)
    except Exception as exc:
        return _seed_response(get_seed_boxscore(game_id), str(exc))


def _normalize_boxscore_players(team_data: dict[str, Any], side: str) -> list[dict[str, Any]]:
    team_abbr = str(team_data.get("teamTricode") or team_data.get("teamAbbreviation") or "")
    players = team_data.get("players", [])
    result = []
    for p in players:
        stats = p.get("statistics", p)
        minutes_raw = str(stats.get("minutesCalculated") or stats.get("minutes") or "0:00")
        minutes = minutes_raw.replace("PT", "").replace("M", ":").rstrip("S") if minutes_raw.startswith("PT") else minutes_raw

        def _pct(made: str, attempted: str) -> float:
            m = float(stats.get(made) or 0)
            a = float(stats.get(attempted) or 0)
            return round(m / a * 100, 1) if a > 0 else 0.0

        result.append({
            "player_id": int(p.get("personId") or 0),
            "player_name": str(p.get("name") or p.get("nameI") or ""),
            "team": team_abbr,
            "side": side,
            "minutes": minutes,
            "points": int(stats.get("points") or 0),
            "rebounds": int(stats.get("reboundsTotal") or stats.get("rebounds") or 0),
            "assists": int(stats.get("assists") or 0),
            "steals": int(stats.get("steals") or 0),
            "blocks": int(stats.get("blocks") or 0),
            "fg_pct": _pct("fieldGoalsMade", "fieldGoalsAttempted"),
            "fg3_pct": _pct("threePointersMade", "threePointersAttempted"),
            "turnovers": int(stats.get("turnovers") or 0),
        })
    return result


def get_game_officials(game_id: str) -> list[dict[str, Any]]:
    """Return officials for a game, with seed fallback and Stats API backup."""
    if not game_id:
        return []
    if game_id.startswith("seed") or _is_seed_mode():
        return get_seed_officials(game_id)

    # Try Live BoxScore first (works for live / today's games)
    try:
        from nba_api.live.nba.endpoints import boxscore as boxscore_ep
        board = boxscore_ep.BoxScore(game_id=game_id)
        raw = board.officials.get_dict()
        officials = raw if isinstance(raw, list) else raw.get("officials", [])
        result = [
            {
                "name": str(o.get("name") or o.get("nameI") or ""),
                "jersey_num": str(o.get("jerseyNum") or ""),
            }
            for o in officials
            if o.get("name") or o.get("nameI")
        ]
        if result:
            return result
    except Exception:
        pass

    # Fallback: Stats BoxScoreSummaryV3 (works for completed games, data from 2025 onwards)
    try:
        from nba_api.stats.endpoints import boxscoresummaryv3
        summary = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, timeout=10)
        df = summary.officials.get_data_frame()
        result = []
        for _, row in df.iterrows():
            name = str(row.get("name") or "").strip()
            if not name:
                first = str(row.get("firstName") or "")
                last = str(row.get("familyName") or "")
                name = f"{first} {last}".strip()
            jersey = str(row.get("jerseyNum") or "")
            if name:
                result.append({"name": name, "jersey_num": jersey})
        return result
    except Exception:
        return []


def _normalize_live_game(game: dict[str, Any]) -> dict[str, Any]:
    home_team = game.get("homeTeam", {})
    away_team = game.get("awayTeam", {})
    return {
        "game_id": str(game.get("gameId") or ""),
        "game_date": str(game.get("gameTimeUTC") or game.get("gameDate") or ""),
        "home_team": str(home_team.get("teamName") or home_team.get("teamCity") or "Home"),
        "away_team": str(away_team.get("teamName") or away_team.get("teamCity") or "Away"),
        "status": str(game.get("gameStatusText") or game.get("gameStatus") or ""),
        "home_score": home_team.get("score"),
        "away_score": away_team.get("score"),
    }


def _current_season() -> str:
    from datetime import datetime
    now = datetime.now()
    year, month = now.year, now.month
    return f"{year}-{str(year + 1)[-2:]}" if month >= 10 else f"{year - 1}-{str(year)[-2:]}"


def _normalize_gamelog(df: Any) -> list[dict[str, Any]]:
    games: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        gid = str(row.get("GAME_ID", ""))
        if not gid:
            continue
        matchup = str(row.get("MATCHUP", ""))
        team_name = str(row.get("TEAM_NAME", ""))
        pts = int(row.get("PTS", 0) or 0)
        game_date = str(row.get("GAME_DATE", "") or "")
        if gid not in games:
            games[gid] = {
                "game_id": gid,
                "game_date": game_date,
                "home_team": "",
                "away_team": "",
                "home_score": 0,
                "away_score": 0,
                "status": "Final",
            }
        if "vs." in matchup:
            games[gid]["home_team"] = team_name
            games[gid]["home_score"] = pts
        elif "@" in matchup:
            games[gid]["away_team"] = team_name
            games[gid]["away_score"] = pts
    result = [g for g in games.values() if g["home_team"] and g["away_team"]]
    result.sort(key=lambda g: g["game_date"], reverse=True)
    return result


def get_recent_games(days: int = 7) -> dict[str, Any]:
    """Return completed games from the past `days` days."""
    from datetime import datetime, timedelta

    if _is_seed_mode():
        return _seed_response(get_seed_recent_games(), f"{DATA_MODE_ENV_VAR}=seed")

    date_from = (datetime.now() - timedelta(days=days)).strftime("%m/%d/%Y")
    errors: list[str] = []

    try:
        from nba_api.stats.endpoints import leaguegamelog
        log = leaguegamelog.LeagueGameLog(
            season=_current_season(),
            date_from_nullable=date_from,
            direction="DESC",
            league_id="00",
            timeout=10,
        )
        df = log.get_data_frames()[0]
        if not df.empty:
            items = _normalize_gamelog(df)
            if items:
                return _api_response(items)
    except Exception as exc:
        errors.append(f"leaguegamelog: {exc}")

    return _seed_response(get_seed_recent_games(), " | ".join(errors) if errors else "no games returned")
