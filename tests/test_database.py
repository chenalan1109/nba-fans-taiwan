from database.db import fetch_all, init_db
from pathlib import Path


def test_init_db_creates_mvp_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test_nba_fans_taiwan.db"

    init_db(db_path)

    rows = fetch_all(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name",
        db_path=db_path,
    )
    table_names = {row["name"] for row in rows}

    assert "users" in table_names
    assert "polls" in table_names
    assert "poll_options" in table_names
    assert "votes" in table_names
    assert "fantasy_teams" in table_names
    assert "matchup_votes" in table_names
