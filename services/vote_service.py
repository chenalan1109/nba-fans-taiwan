from __future__ import annotations

import datetime
import os
import time
from pathlib import Path
from typing import Any

from database.db import fetch_all, fetch_one, get_connection
from database.seed_data import get_seed_players, get_seed_polls

_last_refresh: float = 0.0
_REFRESH_INTERVAL: float = 3600.0  # refresh at most once per hour
_cached_phase: str = ""

_last_game_poll_refresh: float = 0.0
_GAME_POLL_INTERVAL: float = 3600.0  # ensure_tomorrow_game_polls at most once per hour

# Series confirmed as concluded — skip even if API reports them as still active
_COMPLETED_SERIES: frozenset[frozenset[str]] = frozenset({
    frozenset({"Oklahoma City Thunder", "San Antonio Spurs"}),
})


def ensure_playoff_polls(
    db_path: str | Path | None = None,
    phase: str | None = None,
    series_list: list[dict[str, Any]] | None = None,
) -> str:
    """Main entry point for voting page.

    Accepts pre-fetched phase/series_list from the page (already cached via
    st.cache_data) to avoid redundant NBA API calls. Falls back to direct
    service calls if not provided. Rate-limited to once per hour.
    Returns the current phase string.
    """
    global _last_refresh, _cached_phase

    global _last_game_poll_refresh
    now_ts = time.time()
    if now_ts - _last_game_poll_refresh >= _GAME_POLL_INTERVAL:
        ensure_tomorrow_game_polls(db_path)
        _last_game_poll_refresh = now_ts

    now = time.time()
    if now - _last_refresh < _REFRESH_INTERVAL:
        return _cached_phase
    _last_refresh = now

    from services.season_service import SeasonPhase as _Phase, detect_season_phase, get_playoff_series

    if phase is not None:
        _cached_phase = phase
        current_phase = _Phase(phase)
    else:
        current_phase = detect_season_phase()
        _cached_phase = current_phase.value

    if current_phase == _Phase.PLAYOFFS:
        _deactivate_completed_series_polls(db_path)
        resolved = series_list if series_list is not None else get_playoff_series()
        _complete_finished_polls(resolved, db_path)
        active_series = [s for s in resolved if s["status"] == "ongoing"]
        if active_series:
            _sync_series_polls_from_season(active_series, db_path)
        else:
            _ensure_champion_polls(db_path)
    elif current_phase == _Phase.PLAY_IN:
        _deactivate_nongame_polls(db_path)
        _ensure_playin_polls(db_path)
    elif current_phase == _Phase.REGULAR_SEASON:
        _deactivate_nongame_polls(db_path)
        _ensure_regular_season_polls(db_path)
    elif current_phase == _Phase.OFF_SEASON:
        _deactivate_nongame_polls(db_path)

    return _cached_phase


def _deactivate_completed_series_polls(db_path: str | Path | None = None) -> None:
    """Deactivate series polls for matchups in _COMPLETED_SERIES."""
    for pair in _COMPLETED_SERIES:
        teams = list(pair)
        for a, b in [(teams[0], teams[1]), (teams[1], teams[0])]:
            with get_connection(db_path) as conn:
                conn.execute(
                    "UPDATE polls SET is_active = 0 WHERE category = 'series' AND title LIKE ? AND title LIKE ?",
                    (f"%{a}%", f"%{b}%"),
                )


def _complete_finished_polls(series_list: list[dict[str, Any]], db_path: str | Path | None = None) -> None:
    """Mark series prediction polls as completed when a winner is known."""
    for s in series_list:
        winner = s.get("winner")
        if not winner:
            continue
        team_a, team_b = s["team_a"], s["team_b"]
        row = fetch_one(
            "SELECT id FROM polls WHERE category = 'series' AND title LIKE ? AND title LIKE ? AND correct_answer IS NULL",
            (f"%{team_a}%", f"%{team_b}%"),
            db_path=db_path,
        )
        if row:
            with get_connection(db_path) as conn:
                conn.execute(
                    "UPDATE polls SET correct_answer = ?, completed_at = ?, is_active = 0 WHERE id = ?",
                    (winner, datetime.datetime.now().isoformat(), int(row["id"])),
                )


def _sync_series_polls_from_season(
    active_series: list[dict[str, Any]],
    db_path: str | Path | None = None,
) -> None:
    """Create/update polls for ongoing series using season_service data."""
    seed_players = get_seed_players()
    active_titles: set[str] = set()
    is_finals = len(active_series) == 1 and active_series[0].get("conference") == "Finals"

    for series in active_series:
        team_a = series["team_a"]
        team_b = series["team_b"]
        if frozenset({team_a, team_b}) in _COMPLETED_SERIES:
            continue

        winner_title = (
            f"{team_a} vs {team_b}，誰會奪得 NBA 總冠軍？"
            if is_finals
            else f"{team_a} vs {team_b}，誰會晉級？"
        )
        create_poll(title=winner_title, category="series", options=[team_a, team_b], db_path=db_path)
        active_titles.add(winner_title)

    # Deactivate series polls not in current active set
    with get_connection(db_path) as conn:
        if active_titles:
            placeholders = ",".join("?" * len(active_titles))
            conn.execute(
                f"UPDATE polls SET is_active = 0 WHERE category = 'series' AND correct_answer IS NULL AND title NOT IN ({placeholders})",
                list(active_titles),
            )
        else:
            conn.execute("UPDATE polls SET is_active = 0 WHERE category = 'series' AND correct_answer IS NULL")

    with get_connection(db_path) as conn:
        for title in active_titles:
            conn.execute("UPDATE polls SET is_active = 1 WHERE title = ?", (title,))


def _ensure_champion_polls(db_path: str | Path | None = None) -> None:
    """Show champion/MVP polls when playoffs are over but results aren't final."""
    for poll in get_seed_polls():
        if poll["category"] in ("champion", "finals", "mvp"):
            create_poll(
                title=str(poll["title"]),
                category=str(poll["category"]),
                options=[str(o) for o in poll["options"]],
                db_path=db_path,
            )


def _ensure_regular_season_polls(db_path: str | Path | None = None) -> None:
    """Generate polls appropriate for the regular season."""
    polls = [
        {
            "title": "2025-26 球季 MVP 你的選擇",
            "category": "mvp",
            "options": ["Shai Gilgeous-Alexander", "Nikola Jokic", "Giannis Antetokounmpo", "Luka Doncic"],
        },
        {
            "title": "2025-26 東區第一種子預測",
            "category": "season",
            "options": ["Cleveland Cavaliers", "New York Knicks", "Boston Celtics", "Milwaukee Bucks"],
        },
        {
            "title": "2025-26 西區第一種子預測",
            "category": "season",
            "options": ["Oklahoma City Thunder", "Houston Rockets", "Los Angeles Lakers", "Golden State Warriors"],
        },
        {
            "title": "2025-26 年度最佳新秀",
            "category": "season",
            "options": ["Alexandre Sarr", "Zaccharie Risacher", "Stephon Castle", "Matas Buzelis"],
        },
    ]
    for poll in polls:
        create_poll(title=poll["title"], category=poll["category"], options=poll["options"], db_path=db_path)
    with get_connection(db_path) as conn:
        conn.execute("UPDATE polls SET is_active = 1 WHERE category IN ('mvp', 'season')")


def _ensure_playin_polls(db_path: str | Path | None = None) -> None:
    """Generate polls for play-in tournament matchups from current standings."""
    try:
        from services.season_service import get_standings
        standings = get_standings()
        for conf_name, teams in standings.items():
            conf_label = "東區" if conf_name == "East" else "西區"
            seeds = {t["rank"]: t["team"] for t in teams if t["rank"] in (7, 8, 9, 10)}
            if 7 in seeds and 8 in seeds:
                title = f"{conf_label}附加賽：{seeds[7]} vs {seeds[8]}，誰能拿到第7種子？"
                create_poll(title=title, category="playin", options=[seeds[7], seeds[8]], db_path=db_path)
            if 9 in seeds and 10 in seeds:
                title = f"{conf_label}附加賽：{seeds[9]} vs {seeds[10]}，誰能存活？"
                create_poll(title=title, category="playin", options=[seeds[9], seeds[10]], db_path=db_path)
    except Exception:
        pass
    with get_connection(db_path) as conn:
        conn.execute("UPDATE polls SET is_active = 1 WHERE category = 'playin'")


def _deactivate_nongame_polls(db_path: str | Path | None = None) -> None:
    """Deactivate all non-game polls (series, season, mvp, playin, etc.)."""
    with get_connection(db_path) as conn:
        conn.execute("UPDATE polls SET is_active = 0 WHERE category NOT IN ('game', 'referee')")


def get_completed_polls(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return polls that have a known correct answer, newest first."""
    rows = fetch_all(
        "SELECT id, title, category, correct_answer, completed_at FROM polls WHERE correct_answer IS NOT NULL ORDER BY completed_at DESC LIMIT 20",
        db_path=db_path,
    )
    return [
        {
            "id": int(row["id"]),
            "title": str(row["title"]),
            "category": str(row["category"]),
            "correct_answer": str(row["correct_answer"]),
            "completed_at": str(row.get("completed_at") or ""),
        }
        for row in rows
    ]


def _fetch_active_playoff_series() -> list[dict[str, str]]:
    """Return active (unfinished) playoff series for the current NBA season.

    Uses LeagueGameFinder to aggregate win counts per matchup. A series is
    considered active when neither team has reached 4 wins.
    """
    from nba_api.stats.endpoints import leaguegamefinder
    from nba_api.stats.static import teams as nba_teams

    today = datetime.date.today()
    season_year = today.year if today.month >= 10 else today.year - 1
    season = f"{season_year}-{str(season_year + 1)[-2:]}"

    all_nba_teams = nba_teams.get_teams()
    abbr_to_id: dict[str, int] = {str(t["abbreviation"]): int(t["id"]) for t in all_nba_teams}
    id_to_full: dict[int, str] = {int(t["id"]): str(t["full_name"]) for t in all_nba_teams}
    id_to_abbr: dict[int, str] = {int(t["id"]): str(t["abbreviation"]) for t in all_nba_teams}

    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Playoffs",
        timeout=15,
    )
    df = finder.get_data_frames()[0]
    if df.empty:
        return []

    series_wins: dict[frozenset, dict[int, int]] = {}

    for _, row in df.iterrows():
        matchup = str(row.get("MATCHUP", ""))
        wl = str(row.get("WL", ""))
        team_id = int(row.get("TEAM_ID", 0))

        if " vs. " in matchup:
            opp_abbr = matchup.split(" vs. ")[-1].strip()
        elif " @ " in matchup:
            opp_abbr = matchup.split(" @ ")[-1].strip()
        else:
            continue

        opp_id = abbr_to_id.get(opp_abbr)
        if opp_id is None or team_id == 0:
            continue

        key: frozenset = frozenset([team_id, opp_id])
        if key not in series_wins:
            series_wins[key] = {}
        if wl == "W":
            series_wins[key][team_id] = series_wins[key].get(team_id, 0) + 1

    active: list[dict[str, str]] = []
    for key, wins in series_wins.items():
        ids = list(key)
        if wins.get(ids[0], 0) < 4 and wins.get(ids[1], 0) < 4:
            active.append({
                "team_a": id_to_full.get(ids[0], str(ids[0])),
                "team_b": id_to_full.get(ids[1], str(ids[1])),
                "abbr_a": id_to_abbr.get(ids[0], ""),
                "abbr_b": id_to_abbr.get(ids[1], ""),
            })
    return active


def _sync_series_polls(series_list: list[dict[str, str]], db_path: str | Path | None = None) -> None:
    """Create/update polls for active series; deactivate polls for finished ones."""
    is_finals = len(series_list) == 1
    active_titles: set[str] = set()
    seed_players = get_seed_players()

    for series in series_list:
        team_a, team_b = series["team_a"], series["team_b"]
        abbr_a, abbr_b = series["abbr_a"], series["abbr_b"]

        if frozenset({team_a, team_b}) in _COMPLETED_SERIES:
            continue

        winner_title = (
            f"{team_a} vs {team_b}，誰會奪得 NBA 總冠軍？"
            if is_finals
            else f"{team_a} vs {team_b}，誰會晉級？"
        )
        create_poll(title=winner_title, category="series", options=[team_a, team_b], db_path=db_path)
        active_titles.add(winner_title)

        # FMVP poll: top scorers from each team's seed players
        stars_a = sorted(
            [p for p in seed_players if str(p.get("team")) == abbr_a],
            key=lambda p: float(p.get("points", 0)),
            reverse=True,
        )[:2]
        stars_b = sorted(
            [p for p in seed_players if str(p.get("team")) == abbr_b],
            key=lambda p: float(p.get("points", 0)),
            reverse=True,
        )[:2]
        fmvp_options = [str(p["name"]) for p in stars_a + stars_b]
        if len(fmvp_options) >= 2:
            fmvp_label = "Finals MVP" if is_finals else "系列賽最佳球員"
            fmvp_title = f"{team_a} vs {team_b} {fmvp_label} 預測"
            create_poll(title=fmvp_title, category="series", options=fmvp_options, db_path=db_path)
            active_titles.add(fmvp_title)

    with get_connection(db_path) as conn:
        if active_titles:
            placeholders = ",".join("?" * len(active_titles))
            conn.execute(
                f"UPDATE polls SET is_active = 0 WHERE category = 'series' AND title NOT IN ({placeholders})",
                list(active_titles),
            )
        else:
            conn.execute("UPDATE polls SET is_active = 0 WHERE category = 'series'")

    with get_connection(db_path) as conn:
        for title in active_titles:
            conn.execute("UPDATE polls SET is_active = 1 WHERE title = ?", (title,))


def ensure_seed_polls(db_path: str | Path | None = None) -> None:
    seed_titles = {str(poll["title"]) for poll in get_seed_polls()}

    # Deactivate non-game polls that are no longer in the current seed list
    with get_connection(db_path) as conn:
        if seed_titles:
            placeholders = ",".join("?" * len(seed_titles))
            conn.execute(
                f"UPDATE polls SET is_active = 0 WHERE category != 'game' AND title NOT IN ({placeholders})",
                list(seed_titles),
            )
        else:
            conn.execute("UPDATE polls SET is_active = 0 WHERE category != 'game'")

    for poll in get_seed_polls():
        create_poll(
            title=str(poll["title"]),
            category=str(poll["category"]),
            options=[str(option) for option in poll["options"]],
            db_path=db_path,
        )

    # Reactivate seed polls in case they were previously deactivated
    with get_connection(db_path) as conn:
        for title in seed_titles:
            conn.execute("UPDATE polls SET is_active = 1 WHERE title = ?", (title,))


def ensure_tomorrow_game_polls(db_path: str | Path | None = None) -> None:
    # Query date for NBA API (US Eastern)
    tomorrow_us = datetime.date.today() + datetime.timedelta(days=1)
    # NBA games start 7-10 PM Eastern → next morning in Taiwan (UTC+8, 13h ahead)
    tomorrow_tw = tomorrow_us + datetime.timedelta(days=1)
    tw_date_str = tomorrow_tw.strftime("%Y-%m-%d")

    # Deactivate game polls that don't match the Taiwan-date prefix
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE polls SET is_active = 0 WHERE category = 'game' AND title NOT LIKE ?",
            (f"{tw_date_str}%",),
        )

    # Skip API call if polls for this Taiwan date already exist
    existing = fetch_all(
        "SELECT id FROM polls WHERE category = 'game' AND title LIKE ? AND is_active = 1",
        (f"{tw_date_str}%",),
        db_path=db_path,
    )
    if existing:
        return

    for game in _fetch_tomorrow_games(tomorrow_us):
        home = game["home_team"]
        away = game["away_team"]
        title = f"{tw_date_str}（台灣時間）：{away} @ {home}，誰會贏？"
        create_poll(title=title, category="game", options=[away, home], db_path=db_path)


def _fetch_tomorrow_games(date: datetime.date) -> list[dict[str, str]]:
    if os.getenv("NBA_DATA_MODE", "auto").strip().lower() == "seed":
        return _seed_tomorrow_games()

    try:
        from nba_api.stats.endpoints import scoreboardv2
        from nba_api.stats.static import teams as nba_teams_static

        board = scoreboardv2.ScoreboardV2(game_date=date.strftime("%m/%d/%Y"), timeout=10)
        df = board.game_header.get_data_frame()
        games: list[dict[str, str]] = []
        for _, row in df.iterrows():
            home_id = int(row.get("HOME_TEAM_ID") or 0)
            visitor_id = int(row.get("VISITOR_TEAM_ID") or 0)
            home_info = nba_teams_static.find_team_by_id(home_id)
            visitor_info = nba_teams_static.find_team_by_id(visitor_id)
            if home_info and visitor_info:
                games.append({
                    "home_team": str(home_info["full_name"]),
                    "away_team": str(visitor_info["full_name"]),
                })
        return games if games else _seed_tomorrow_games()
    except Exception:
        return _seed_tomorrow_games()


def _seed_tomorrow_games() -> list[dict[str, str]]:
    return [
        {"home_team": "Oklahoma City Thunder", "away_team": "San Antonio Spurs"},
    ]


def create_poll(
    title: str,
    options: list[str],
    category: str = "general",
    db_path: str | Path | None = None,
) -> int:
    existing_poll = fetch_one(
        "SELECT id FROM polls WHERE title = ? AND category = ?",
        (title, category),
        db_path=db_path,
    )
    if existing_poll is not None:
        poll_id = int(existing_poll["id"])
        _ensure_poll_options(poll_id, options, db_path)
        return poll_id

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO polls (title, category) VALUES (?, ?)",
            (title, category),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to create poll")
        poll_id = cursor.lastrowid

    _ensure_poll_options(poll_id, options, db_path)
    return poll_id


def list_active_polls(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    poll_rows = fetch_all(
        "SELECT id, title, category FROM polls WHERE is_active = 1 ORDER BY id",
        db_path=db_path,
    )
    if not poll_rows:
        return []

    # Fetch all options in one query to avoid N+1
    poll_ids = [int(r["id"]) for r in poll_rows]
    placeholders = ",".join("?" * len(poll_ids))
    option_rows = fetch_all(
        f"SELECT poll_id, option_text FROM poll_options WHERE poll_id IN ({placeholders}) ORDER BY id",
        tuple(poll_ids),
        db_path=db_path,
    )
    options_by_poll: dict[int, list[str]] = {pid: [] for pid in poll_ids}
    for opt in option_rows:
        options_by_poll[int(opt["poll_id"])].append(str(opt["option_text"]))

    return [
        {
            "id": int(row["id"]),
            "title": str(row["title"]),
            "category": str(row["category"]),
            "options": options_by_poll.get(int(row["id"]), []),
        }
        for row in poll_rows
    ]


def get_poll_options(poll_id: int, db_path: str | Path | None = None) -> list[str]:
    rows = fetch_all(
        """
        SELECT option_text
        FROM poll_options
        WHERE poll_id = ?
        ORDER BY id
        """,
        (poll_id,),
        db_path=db_path,
    )
    return [str(row["option_text"]) for row in rows]


def submit_vote(
    poll_id: int,
    voter_id: str,
    option: str,
    db_path: str | Path | None = None,
) -> bool:
    normalized_voter_id = voter_id.strip()
    normalized_option = option.strip()
    if not normalized_voter_id or not normalized_option:
        return False

    option_row = fetch_one(
        """
        SELECT id
        FROM poll_options
        WHERE poll_id = ? AND option_text = ?
        """,
        (poll_id, normalized_option),
        db_path=db_path,
    )
    if option_row is None:
        return False

    try:
        with get_connection(db_path) as connection:
            connection.execute(
                """
                INSERT INTO votes (poll_id, voter_id, option_id)
                VALUES (?, ?, ?)
                """,
                (poll_id, normalized_voter_id, int(option_row["id"])),
            )
        return True
    except Exception:
        return False


def has_voted(poll_id: int, voter_id: str, db_path: str | Path | None = None) -> bool:
    row = fetch_one(
        "SELECT id FROM votes WHERE poll_id = ? AND voter_id = ?",
        (poll_id, voter_id.strip()),
        db_path=db_path,
    )
    return row is not None


def get_selected_option(poll_id: int, voter_id: str, db_path: str | Path | None = None) -> str | None:
    row = fetch_one(
        """
        SELECT poll_options.option_text
        FROM votes
        JOIN poll_options ON poll_options.id = votes.option_id
        WHERE votes.poll_id = ? AND votes.voter_id = ?
        """,
        (poll_id, voter_id.strip()),
        db_path=db_path,
    )
    return str(row["option_text"]) if row is not None else None


def get_vote_summary(poll_id: int, db_path: str | Path | None = None) -> dict[str, int]:
    options = get_poll_options(poll_id, db_path)
    summary = {option: 0 for option in options}

    rows = fetch_all(
        """
        SELECT poll_options.option_text, COUNT(votes.id) AS vote_count
        FROM poll_options
        LEFT JOIN votes ON votes.option_id = poll_options.id
        WHERE poll_options.poll_id = ?
        GROUP BY poll_options.id, poll_options.option_text
        ORDER BY poll_options.id
        """,
        (poll_id,),
        db_path=db_path,
    )
    for row in rows:
        summary[str(row["option_text"])] = int(row["vote_count"])
    return summary


def get_total_active_votes(db_path: str | Path | None = None) -> int:
    """Return total vote count across all active polls in a single query."""
    row = fetch_one(
        "SELECT COUNT(v.id) AS total FROM votes v "
        "JOIN polls p ON p.id = v.poll_id WHERE p.is_active = 1",
        db_path=db_path,
    )
    return int(row["total"]) if row else 0


def _ensure_poll_options(
    poll_id: int,
    options: list[str],
    db_path: str | Path | None = None,
) -> None:
    existing_options = set(get_poll_options(poll_id, db_path))
    with get_connection(db_path) as connection:
        for option in options:
            normalized_option = option.strip()
            if normalized_option and normalized_option not in existing_options:
                connection.execute(
                    "INSERT INTO poll_options (poll_id, option_text) VALUES (?, ?)",
                    (poll_id, normalized_option),
                )
