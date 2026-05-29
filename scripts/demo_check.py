from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import fetch_all, init_db
from services import nba_api_service
from services.game_service import (
    get_matchup_vote_summary,
    save_fantasy_team,
    simulate_matchup,
    submit_matchup_vote,
)
from services.player_service import get_featured_players
from services.vote_service import ensure_seed_polls, get_vote_summary, list_active_polls, submit_vote


def main() -> None:
    db_path = Path(tempfile.gettempdir()) / "nba_fans_taiwan_demo_check.db"
    if db_path.exists():
        db_path.unlink()

    init_db(db_path)
    _check_database_tables(db_path)
    _check_seed_mode()
    _check_vote_flow(db_path)
    _check_game_flow(db_path)

    print("demo check passed")


def _check_database_tables(db_path: Path) -> None:
    rows = fetch_all("SELECT name FROM sqlite_master WHERE type = 'table'", db_path=db_path)
    table_names = {str(row["name"]) for row in rows}
    required_tables = {
        "users",
        "polls",
        "poll_options",
        "votes",
        "fantasy_teams",
        "fantasy_team_players",
        "matchup_votes",
    }
    missing_tables = required_tables - table_names
    if missing_tables:
        raise RuntimeError(f"missing tables: {sorted(missing_tables)}")


def _check_seed_mode() -> None:
    previous_mode = os.environ.get(nba_api_service.DATA_MODE_ENV_VAR)
    os.environ[nba_api_service.DATA_MODE_ENV_VAR] = nba_api_service.DATA_MODE_SEED
    try:
        scoreboard = nba_api_service.get_scoreboard()
        players = nba_api_service.search_players("Curry")
        stats = nba_api_service.get_player_season_stats(201939)
    finally:
        if previous_mode is None:
            os.environ.pop(nba_api_service.DATA_MODE_ENV_VAR, None)
        else:
            os.environ[nba_api_service.DATA_MODE_ENV_VAR] = previous_mode

    if scoreboard["source"] != "seed" or not scoreboard["items"]:
        raise RuntimeError("seed scoreboard check failed")
    if players["source"] != "seed" or not players["items"]:
        raise RuntimeError("seed player search check failed")
    if stats["source"] != "seed" or not stats["items"]:
        raise RuntimeError("seed player stats check failed")


def _check_vote_flow(db_path: Path) -> None:
    ensure_seed_polls(db_path)
    polls = list_active_polls(db_path)
    if not polls:
        raise RuntimeError("seed polls were not created")

    poll = polls[0]
    option = str(poll["options"][0])
    if not submit_vote(int(poll["id"]), "demo-user", option, db_path):
        raise RuntimeError("vote submit failed")

    summary = get_vote_summary(int(poll["id"]), db_path)
    if summary[option] != 1:
        raise RuntimeError("vote summary check failed")


def _check_game_flow(db_path: Path) -> None:
    players = get_featured_players()
    if len(players) < 6:
        raise RuntimeError("not enough seed players for game demo")

    fantasy_team_id = save_fantasy_team("demo", "Demo Five", players[:5], db_path)
    if fantasy_team_id <= 0:
        raise RuntimeError("fantasy team save failed")

    matchup = simulate_matchup(players[:3], players[3:6])
    if "winner" not in matchup:
        raise RuntimeError("matchup simulation failed")

    if not submit_matchup_vote("demo-matchup", "demo-user", "A", db_path):
        raise RuntimeError("matchup vote failed")
    if get_matchup_vote_summary("demo-matchup", db_path) != {"A": 1, "B": 0}:
        raise RuntimeError("matchup vote summary failed")


if __name__ == "__main__":
    main()
