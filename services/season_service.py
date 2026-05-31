from __future__ import annotations

import datetime
import os
from enum import Enum
from typing import Any


class SeasonPhase(str, Enum):
    REGULAR_SEASON = "regular_season"
    PLAY_IN = "play_in"
    PLAYOFFS = "playoffs"
    OFF_SEASON = "off_season"

    def label(self) -> str:
        return {
            "regular_season": "例行賽",
            "play_in": "附加賽",
            "playoffs": "季後賽",
            "off_season": "休賽季",
        }[self.value]


def get_current_season() -> str:
    today = datetime.date.today()
    year = today.year if today.month >= 10 else today.year - 1
    return f"{year}-{str(year + 1)[-2:]}"


def detect_season_phase() -> SeasonPhase:
    if _is_seed_mode():
        return SeasonPhase.PLAYOFFS
    return _detect_from_date()


def get_playoff_series() -> list[dict[str, Any]]:
    if _is_seed_mode():
        return _seed_playoff_series()
    try:
        return _fetch_playoff_series()
    except Exception:
        return _seed_playoff_series()


def get_standings() -> dict[str, list[dict[str, Any]]]:
    if _is_seed_mode():
        return _seed_standings()
    try:
        return _fetch_standings()
    except Exception:
        return _seed_standings()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_seed_mode() -> bool:
    return os.getenv("NBA_DATA_MODE", "auto").strip().lower() == "seed"


def _detect_from_api() -> SeasonPhase:
    from nba_api.stats.endpoints import leaguegamefinder

    season = get_current_season()
    today = datetime.date.today()
    cutoff_30 = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    cutoff_7 = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    def has_recent(season_type: str, cutoff: str) -> bool:
        finder = leaguegamefinder.LeagueGameFinder(
            season_nullable=season,
            season_type_nullable=season_type,
            timeout=12,
        )
        df = finder.get_data_frames()[0]
        return not df.empty and bool((df["GAME_DATE"] >= cutoff).any())

    if has_recent("Playoffs", cutoff_30):
        return SeasonPhase.PLAYOFFS
    if has_recent("PlayIn", cutoff_30):
        return SeasonPhase.PLAY_IN
    if has_recent("Regular Season", cutoff_7):
        return SeasonPhase.REGULAR_SEASON
    return SeasonPhase.OFF_SEASON


def _detect_from_date() -> SeasonPhase:
    today = datetime.date.today()
    m, d = today.month, today.day
    if m in (10, 11, 12, 1, 2, 3) or (m == 4 and d <= 13):
        return SeasonPhase.REGULAR_SEASON
    if m == 4 and 14 <= d <= 21:
        return SeasonPhase.PLAY_IN
    if (m == 4 and d >= 22) or m == 5 or (m == 6 and d <= 22):
        return SeasonPhase.PLAYOFFS
    return SeasonPhase.OFF_SEASON


_ROUND_LABELS: dict[int, str] = {1: "第一輪", 2: "分區準決賽", 3: "分區決賽", 4: "NBA Finals"}

_EAST_ABBRS: frozenset[str] = frozenset({
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND",
    "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS",
})


def _fetch_playoff_series() -> list[dict[str, Any]]:
    from nba_api.stats.endpoints import leaguegamefinder
    from nba_api.stats.static import teams as nba_teams

    season = get_current_season()
    all_teams = nba_teams.get_teams()
    id_to_info: dict[int, dict] = {int(t["id"]): t for t in all_teams}
    abbr_to_id: dict[str, int] = {str(t["abbreviation"]): int(t["id"]) for t in all_teams}

    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Playoffs",
        timeout=15,
    )
    df = finder.get_data_frames()[0]
    if df.empty:
        return []

    series_data: dict[frozenset, dict[str, Any]] = {}

    for _, row in df.iterrows():
        matchup = str(row.get("MATCHUP", ""))
        wl = str(row.get("WL", ""))
        team_id = int(row.get("TEAM_ID", 0))
        # NBA playoff game_id: 004YY00RSSG — position 7 (0-indexed) is round number
        game_id = str(row.get("GAME_ID") or "")
        round_from_id = int(game_id[7]) if len(game_id) >= 8 and game_id[7].isdigit() else 0

        if " vs. " in matchup:
            opp_abbr = matchup.split(" vs. ")[-1].strip()
        elif " @ " in matchup:
            opp_abbr = matchup.split(" @ ")[-1].strip()
        else:
            continue

        opp_id = abbr_to_id.get(opp_abbr)
        if not opp_id or not team_id:
            continue

        key: frozenset = frozenset([team_id, opp_id])
        if key not in series_data:
            ids = sorted(key)
            info_a = id_to_info.get(ids[0], {})
            info_b = id_to_info.get(ids[1], {})
            abbr_a = str(info_a.get("abbreviation", ""))
            abbr_b = str(info_b.get("abbreviation", ""))
            conf_a = "East" if abbr_a in _EAST_ABBRS else "West"
            conf_b = "East" if abbr_b in _EAST_ABBRS else "West"
            series_data[key] = {
                "team_a": str(info_a.get("full_name", ids[0])),
                "team_b": str(info_b.get("full_name", ids[1])),
                "team_a_id": ids[0],
                "team_b_id": ids[1],
                "team_a_abbr": abbr_a,
                "team_b_abbr": abbr_b,
                "conference": conf_a if conf_a == conf_b else "Finals",
                "wins_a": 0,
                "wins_b": 0,
                "round_num": round_from_id,
            }
        elif round_from_id > 0:
            series_data[key]["round_num"] = round_from_id

        s = series_data[key]
        if wl == "W":
            if team_id == s["team_a_id"]:
                s["wins_a"] += 1
            else:
                s["wins_b"] += 1

    all_series: list[dict[str, Any]] = []
    for s in series_data.values():
        wins_a, wins_b = s["wins_a"], s["wins_b"]
        finished = max(wins_a, wins_b) >= 4
        winner: str | None = None
        if wins_a >= 4:
            winner = s["team_a"]
        elif wins_b >= 4:
            winner = s["team_b"]
        rnd = s.get("round_num", 0)
        all_series.append({
            "team_a": s["team_a"],
            "team_b": s["team_b"],
            "team_a_abbr": s.get("team_a_abbr", ""),
            "team_b_abbr": s.get("team_b_abbr", ""),
            "wins_a": wins_a,
            "wins_b": wins_b,
            "conference": s["conference"],
            "status": "finished" if finished else "ongoing",
            "winner": winner,
            "round_num": rnd,
            "round": _ROUND_LABELS.get(rnd, f"第{rnd}輪") if rnd else "季後賽",
        })

    # Synthesize a Finals entry when both conf finals are done but no game has been played yet
    if not any(s["round_num"] == 4 for s in all_series):
        round3_done = [s for s in all_series if s["round_num"] == 3 and s["status"] == "finished"]
        east_final = next((s for s in round3_done if s["conference"] == "East"), None)
        west_final = next((s for s in round3_done if s["conference"] == "West"), None)
        if east_final and east_final.get("winner") and west_final and west_final.get("winner"):
            name_to_abbr = {
                str(info.get("full_name", "")): str(info.get("abbreviation", ""))
                for info in id_to_info.values()
            }
            ew, ww = east_final["winner"], west_final["winner"]
            all_series.append({
                "team_a": ww, "team_b": ew,
                "team_a_abbr": name_to_abbr.get(ww, ""),
                "team_b_abbr": name_to_abbr.get(ew, ""),
                "wins_a": 0, "wins_b": 0,
                "conference": "Finals",
                "status": "ongoing", "winner": None,
                "round_num": 4, "round": "NBA Finals",
            })

    return sorted(all_series, key=lambda x: x["round_num"])


def _fetch_standings() -> dict[str, list[dict[str, Any]]]:
    from nba_api.stats.endpoints import leaguestandings

    season = get_current_season()
    ep = leaguestandings.LeagueStandings(season=season, timeout=15)
    df = ep.standings.get_data_frame()

    result: dict[str, list[dict[str, Any]]] = {"East": [], "West": []}

    for _, row in df.iterrows():
        r = row.to_dict()
        conf = str(r.get("Conference") or "")
        if conf not in ("East", "West"):
            continue
        city = str(r.get("TeamCity") or "")
        name = str(r.get("TeamName") or "")
        wins = int(r.get("WINS") or 0)
        losses = int(r.get("LOSSES") or 0)
        pct = float(r.get("WinPCT") or 0.0)
        rank = int(r.get("PlayoffRank") or r.get("ConferenceRank") or 0)
        result[conf].append({"rank": rank, "team": f"{city} {name}".strip(), "wins": wins, "losses": losses, "pct": pct})

    for conf in result:
        result[conf].sort(key=lambda x: x["rank"])
    return result


def _seed_standings() -> dict[str, list[dict[str, Any]]]:
    return {
        "East": [
            {"rank": 1, "team": "Cleveland Cavaliers", "wins": 64, "losses": 18, "pct": 0.780},
            {"rank": 2, "team": "New York Knicks", "wins": 55, "losses": 27, "pct": 0.671},
            {"rank": 3, "team": "Boston Celtics", "wins": 52, "losses": 30, "pct": 0.634},
            {"rank": 4, "team": "Milwaukee Bucks", "wins": 48, "losses": 34, "pct": 0.585},
            {"rank": 5, "team": "Indiana Pacers", "wins": 45, "losses": 37, "pct": 0.549},
        ],
        "West": [
            {"rank": 1, "team": "Oklahoma City Thunder", "wins": 68, "losses": 14, "pct": 0.829},
            {"rank": 2, "team": "Houston Rockets", "wins": 52, "losses": 30, "pct": 0.634},
            {"rank": 3, "team": "Los Angeles Lakers", "wins": 50, "losses": 32, "pct": 0.610},
            {"rank": 4, "team": "Golden State Warriors", "wins": 48, "losses": 34, "pct": 0.585},
            {"rank": 5, "team": "Dallas Mavericks", "wins": 44, "losses": 38, "pct": 0.537},
        ],
    }


_SEED_ABBR: dict[str, str] = {
    "Oklahoma City Thunder": "OKC", "San Antonio Spurs": "SAS",
    "Dallas Mavericks": "DAL",      "Houston Rockets": "HOU",
    "Los Angeles Lakers": "LAL",    "Golden State Warriors": "GSW",
    "Denver Nuggets": "DEN",        "Minnesota Timberwolves": "MIN",
    "Cleveland Cavaliers": "CLE",   "Miami Heat": "MIA",
    "New York Knicks": "NYK",       "Philadelphia 76ers": "PHI",
    "Boston Celtics": "BOS",        "Atlanta Hawks": "ATL",
    "Milwaukee Bucks": "MIL",       "Indiana Pacers": "IND",
}


def _seed_playoff_series() -> list[dict[str, Any]]:
    def _s(ta, tb, wa, wb, conf, winner, rnd):
        return {"team_a": ta, "team_b": tb,
                "team_a_abbr": _SEED_ABBR.get(ta, ""), "team_b_abbr": _SEED_ABBR.get(tb, ""),
                "wins_a": wa, "wins_b": wb, "conference": conf,
                "status": "finished" if winner else "ongoing", "winner": winner,
                "round_num": rnd, "round": _ROUND_LABELS.get(rnd, "")}
    return [
        _s("Oklahoma City Thunder", "San Antonio Spurs",     4, 0, "West",   "Oklahoma City Thunder", 1),
        _s("Dallas Mavericks",      "Houston Rockets",       4, 2, "West",   "Dallas Mavericks",      1),
        _s("Los Angeles Lakers",    "Golden State Warriors", 4, 3, "West",   "Los Angeles Lakers",    1),
        _s("Denver Nuggets",        "Minnesota Timberwolves",4, 2, "West",   "Denver Nuggets",        1),
        _s("Cleveland Cavaliers",   "Miami Heat",            4, 0, "East",   "Cleveland Cavaliers",   1),
        _s("New York Knicks",       "Philadelphia 76ers",    4, 1, "East",   "New York Knicks",       1),
        _s("Boston Celtics",        "Atlanta Hawks",         4, 0, "East",   "Boston Celtics",        1),
        _s("Milwaukee Bucks",       "Indiana Pacers",        4, 3, "East",   "Milwaukee Bucks",       1),
        _s("Oklahoma City Thunder", "Dallas Mavericks",      4, 1, "West",   "Oklahoma City Thunder", 2),
        _s("Denver Nuggets",        "Los Angeles Lakers",    4, 2, "West",   "Denver Nuggets",        2),
        _s("Cleveland Cavaliers",   "Milwaukee Bucks",       4, 2, "East",   "Cleveland Cavaliers",   2),
        _s("New York Knicks",       "Boston Celtics",        4, 3, "East",   "New York Knicks",       2),
        _s("Oklahoma City Thunder", "Denver Nuggets",        4, 1, "West",   "Oklahoma City Thunder", 3),
        _s("New York Knicks",       "Cleveland Cavaliers",   4, 2, "East",   "New York Knicks",       3),
        _s("Oklahoma City Thunder", "New York Knicks",       2, 1, "Finals", None,                    4),
    ]


