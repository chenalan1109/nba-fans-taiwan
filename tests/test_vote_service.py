from pathlib import Path

from database.db import init_db
from database.seed_data import get_seed_polls
from services.vote_service import (
    create_poll,
    ensure_seed_polls,
    get_selected_option,
    get_vote_summary,
    has_voted,
    list_active_polls,
    submit_vote,
)


def test_create_poll_and_list_options(tmp_path: Path) -> None:
    db_path = tmp_path / "votes.db"
    init_db(db_path)

    poll_id = create_poll("MVP 預測", ["A", "B"], "mvp", db_path)
    polls = list_active_polls(db_path)

    assert poll_id > 0
    assert polls == [{"id": poll_id, "title": "MVP 預測", "category": "mvp", "options": ["A", "B"]}]


def test_submit_vote_prevents_duplicate_voter(tmp_path: Path) -> None:
    db_path = tmp_path / "votes.db"
    init_db(db_path)
    poll_id = create_poll("總冠軍預測", ["Lakers", "Celtics"], "champion", db_path)

    assert submit_vote(poll_id, "maurice", "Lakers", db_path) is True
    assert submit_vote(poll_id, "maurice", "Celtics", db_path) is False
    assert has_voted(poll_id, "maurice", db_path) is True
    assert get_selected_option(poll_id, "maurice", db_path) == "Lakers"


def test_vote_summary_counts_each_option(tmp_path: Path) -> None:
    db_path = tmp_path / "votes.db"
    init_db(db_path)
    poll_id = create_poll("單場勝負", ["Warriors", "Nuggets"], "match", db_path)

    submit_vote(poll_id, "user-1", "Warriors", db_path)
    submit_vote(poll_id, "user-2", "Nuggets", db_path)
    submit_vote(poll_id, "user-3", "Nuggets", db_path)

    assert get_vote_summary(poll_id, db_path) == {"Warriors": 1, "Nuggets": 2}


def test_invalid_vote_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "votes.db"
    init_db(db_path)
    poll_id = create_poll("MVP 預測", ["A", "B"], "mvp", db_path)

    assert submit_vote(poll_id, "maurice", "Unknown", db_path) is False
    assert submit_vote(poll_id, "", "A", db_path) is False
    assert get_vote_summary(poll_id, db_path) == {"A": 0, "B": 0}


def test_ensure_seed_polls_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "votes.db"
    init_db(db_path)

    ensure_seed_polls(db_path)
    ensure_seed_polls(db_path)

    polls = list_active_polls(db_path)
    assert len(polls) == len(get_seed_polls())
