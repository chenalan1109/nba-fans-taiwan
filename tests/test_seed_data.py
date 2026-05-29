from database.seed_data import get_seed_matchups, get_seed_players, get_seed_polls, get_seed_scoreboard


def test_seed_data_supports_milestone_one_demo() -> None:
    assert get_seed_scoreboard()
    assert get_seed_players()
    assert get_seed_polls()
    assert get_seed_matchups()
