from __future__ import annotations

from typing import Any, cast

from models.player import Player
from services import nba_api_service


def _to_player(raw_player: dict[str, Any]) -> Player:
    image_url = raw_player.get("image_url")
    return Player(
        id=int(raw_player["id"]),
        name=str(raw_player["name"]),
        team=str(raw_player.get("team") or "N/A"),
        position=str(raw_player.get("position") or "N/A"),
        points=float(raw_player.get("points") or 0.0),
        rebounds=float(raw_player.get("rebounds") or 0.0),
        assists=float(raw_player.get("assists") or 0.0),
        steals=float(raw_player.get("steals") or 0.0),
        blocks=float(raw_player.get("blocks") or 0.0),
        turnovers=float(raw_player.get("turnovers") or 0.0),
        image_url=image_url if isinstance(image_url, str) else None,
    )


def find_players(keyword: str) -> dict[str, Any]:
    response = nba_api_service.search_players(keyword)
    raw_players = cast(list[dict[str, Any]], response["items"])
    return {
        "source": response["source"],
        "items": [_to_player(player) for player in raw_players],
        "error": response.get("error"),
    }


def get_featured_players() -> list[Player]:
    response = find_players("")
    return cast(list[Player], response["items"])


def get_player_detail(player_id: int) -> dict[str, Any]:
    response = nba_api_service.get_player_profile(player_id)
    items = cast(list[dict[str, Any]], response["items"])
    player = _to_player(items[0]) if items else None
    return {
        "source": response["source"],
        "item": player,
        "error": response.get("error"),
    }


def get_player_per_game_stats(player_id: int) -> dict[str, Any]:
    return get_player_chart_data(player_id)


def get_player_chart_data(player_id: int) -> dict[str, Any]:
    response = nba_api_service.get_player_season_stats(player_id)
    return {
        "source": response["source"],
        "items": response["items"],
        "error": response.get("error"),
    }


def get_player_data_quality(player: Player | None, stats: list[dict[str, Any]]) -> dict[str, Any]:
    missing_fields: list[str] = []
    if player is None:
        missing_fields.append("player")
    else:
        if player.team == "N/A":
            missing_fields.append("team")
        if player.position == "N/A":
            missing_fields.append("position")
        if player.points == 0.0 and player.rebounds == 0.0 and player.assists == 0.0:
            missing_fields.append("latest_stats")

    if not stats:
        missing_fields.append("season_stats")

    if not missing_fields:
        status = "complete"
        label = "完整資料"
    elif stats and missing_fields != ["season_stats"]:
        status = "partial"
        label = "部分資料"
    else:
        status = "limited"
        label = "資料不足"

    return {
        "status": status,
        "label": label,
        "missing_fields": missing_fields,
    }


def get_searchable_players(keyword: str = "") -> list[Player]:
    """Return players from seed pool + API search results merged. Seed players retain full stats."""
    seed_players = get_featured_players()
    if not keyword:
        return seed_players
    result = find_players(keyword)
    api_players = cast(list[Player], result["items"])
    seed_map = {p.id: p for p in seed_players}
    merged: dict[int, Player] = {}
    for p in api_players:
        merged[p.id] = seed_map.get(p.id, p)
    # Also include seed players that match the keyword (covers seed-mode filtering)
    for p in seed_players:
        if keyword.lower() in p.name.lower():
            merged[p.id] = p
    return list(merged.values())


def get_player_pool(
    keyword: str = "",
    team: str = "",
    position: str = "",
) -> list[Player]:
    all_players = get_featured_players()
    result = all_players
    if keyword:
        kw = keyword.lower()
        result = [p for p in result if kw in p.name.lower()]
    if team:
        result = [p for p in result if p.team == team]
    if position:
        result = [p for p in result if p.position == position]
    return result


def calculate_fantasy_score(player: Player) -> float:
    return (
        player.points
        + player.rebounds * 1.2
        + player.assists * 1.5
        + player.steals * 2
        + player.blocks * 2
        - player.turnovers
    )
