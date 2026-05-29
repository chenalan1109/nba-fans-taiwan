"""Prophet coin prediction system — data layer.

Covers user management, prediction item lifecycle (open → locked → settled),
upsert of user predictions, coin settlement, and leaderboard queries.
The Streamlit page (prophet.py) calls these functions; no st.* imports here.
"""
from __future__ import annotations

import datetime
import math
from typing import Any

from database.db import execute_query, fetch_all, fetch_one
from services.season_service import get_current_season

# ── Constants ─────────────────────────────────────────────────────────────────

_LONGTERM_AWARDS: list[tuple[str, str]] = [
    ("mvp",       "年度 MVP"),
    ("champion",  "總冠軍"),
    ("dpoy",      "最佳防守球員"),
    ("roy",       "最佳新秀"),
    ("sixth_man", "最佳第六人"),
    ("mip",       "最佳進步獎"),
    ("fmvp",      "總決賽 MVP"),
]

_BASE_LONGTERM = 1000
_BASE_INSTANT  = 200
_LAMBDA        = 4.0

_ROUND_ZH: dict[int, str] = {
    1: "第一輪", 2: "分區準決賽", 3: "分區決賽", 4: "Finals",
}

# ── Initialization ────────────────────────────────────────────────────────────

def init_prophet(season: str | None = None) -> None:
    """Create long-term prediction items for the season on first call (idempotent)."""
    s = season or get_current_season()
    now = _now()
    for suffix, label in _LONGTERM_AWARDS:
        item_key = f"{s}_{suffix}"
        if not fetch_one("SELECT 1 FROM prediction_items WHERE item_key=?", (item_key,)):
            execute_query(
                "INSERT OR IGNORE INTO prediction_items "
                "(item_key, item_label, category, status, opened_at) VALUES (?,?,?,?,?)",
                (item_key, f"{s} {label}", "longterm", "open", now),
            )


# ── User management ───────────────────────────────────────────────────────────

def get_or_create_user(nickname: str) -> dict[str, Any]:
    row = fetch_one("SELECT * FROM prophet_users WHERE nickname=?", (nickname,))
    if not row:
        execute_query("INSERT OR IGNORE INTO prophet_users (nickname) VALUES (?)", (nickname,))
        row = fetch_one("SELECT * FROM prophet_users WHERE nickname=?", (nickname,))
    return dict(row)  # type: ignore[arg-type]


def get_leaderboard(limit: int = 20) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT nickname, coins FROM prophet_users "
        "ORDER BY coins DESC, created_at ASC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in rows]


# ── Prediction items ──────────────────────────────────────────────────────────

def get_item(item_key: str) -> dict[str, Any] | None:
    row = fetch_one(
        "SELECT pi.*, se.correct_answer, se.settled_at "
        "FROM prediction_items pi "
        "LEFT JOIN settlement_events se ON pi.item_key=se.item_key "
        "WHERE pi.item_key=?",
        (item_key,),
    )
    return dict(row) if row else None


def get_all_items(season: str | None = None) -> list[dict[str, Any]]:
    s = season or get_current_season()
    rows = fetch_all(
        "SELECT pi.*, se.correct_answer, se.settled_at "
        "FROM prediction_items pi "
        "LEFT JOIN settlement_events se ON pi.item_key=se.item_key "
        "WHERE pi.item_key LIKE ? ORDER BY pi.category DESC, pi.opened_at",
        (f"{s}%",),
    )
    return [dict(r) for r in rows]


# ── Instant prediction sync (called each page load during playoffs) ───────────

def sync_instant_items(series_list: list[dict[str, Any]], season: str | None = None) -> None:
    """Open prediction items for rounds whose previous round is fully finished.
    Lock items for series where the first game has been played.
    """
    s = season or get_current_season()

    by_round: dict[int, list[dict[str, Any]]] = {}
    for series in series_list:
        rnd = int(series.get("round_num") or 0)
        if rnd > 0:
            by_round.setdefault(rnd, []).append(series)

    for rnd in sorted(by_round.keys()):
        prev = by_round.get(rnd - 1, [])
        prev_done = rnd == 1 or (bool(prev) and all(sr["status"] == "finished" for sr in prev))
        if not prev_done:
            continue

        for series in by_round[rnd]:
            item_key = _series_key(series, s)
            if not item_key:
                continue

            label      = _series_label(series, rnd)
            games      = int(series.get("wins_a", 0)) + int(series.get("wins_b", 0))
            started    = games > 0
            existing   = fetch_one(
                "SELECT status FROM prediction_items WHERE item_key=?", (item_key,)
            )

            if not existing:
                status    = "locked" if started else "open"
                locked_at = _now() if started else None
                execute_query(
                    "INSERT OR IGNORE INTO prediction_items "
                    "(item_key, item_label, category, status, opened_at, locked_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (item_key, label, "instant", status, _now(), locked_at),
                )
            elif existing["status"] == "open" and started:
                execute_query(
                    "UPDATE prediction_items SET status='locked', locked_at=? WHERE item_key=?",
                    (_now(), item_key),
                )


def settle_finished_series(series_list: list[dict[str, Any]], season: str | None = None) -> None:
    """Auto-settle prediction items for series that now have a winner."""
    s = season or get_current_season()
    now = _now()
    for series in series_list:
        if series.get("status") != "finished" or not series.get("winner"):
            continue
        item_key = _series_key(series, s)
        if not item_key:
            continue
        item = get_item(item_key)
        if item and item.get("status") != "settled":
            _do_settle(item_key, str(series["winner"]), now, _BASE_INSTANT)


# ── User predictions ──────────────────────────────────────────────────────────

def get_user_prediction(nickname: str, item_key: str) -> dict[str, Any] | None:
    row = fetch_one(
        "SELECT * FROM user_predictions WHERE nickname=? AND item_key=?",
        (nickname, item_key),
    )
    return dict(row) if row else None


def upsert_prediction(nickname: str, item_key: str, prediction: str) -> tuple[bool, str]:
    """Insert or update a prediction. Returns (success, reason)."""
    item = get_item(item_key)
    if not item:
        return False, "找不到預測項目"
    if item["status"] == "settled":
        return False, "此項目已結算"
    if not prediction.strip():
        return False, "預測內容不可為空"

    get_or_create_user(nickname)
    execute_query(
        "INSERT INTO user_predictions (nickname, item_key, prediction, last_changed_at) "
        "VALUES (?,?,?,?) "
        "ON CONFLICT(nickname, item_key) DO UPDATE SET "
        "prediction=excluded.prediction, last_changed_at=excluded.last_changed_at",
        (nickname, item_key, prediction.strip(), _now()),
    )
    return True, "預測成功"


def get_user_all_predictions(nickname: str, season: str | None = None) -> list[dict[str, Any]]:
    s = season or get_current_season()
    rows = fetch_all(
        "SELECT up.*, pi.item_label, pi.status AS item_status, pi.category, "
        "pi.opened_at AS item_opened_at, se.correct_answer, se.settled_at "
        "FROM user_predictions up "
        "JOIN prediction_items pi ON up.item_key=pi.item_key "
        "LEFT JOIN settlement_events se ON up.item_key=se.item_key "
        "WHERE up.nickname=? AND up.item_key LIKE ? "
        "ORDER BY pi.category DESC, pi.opened_at",
        (nickname, f"{s}%"),
    )
    return [dict(r) for r in rows]


# ── Settlement ────────────────────────────────────────────────────────────────

def settle_longterm_item(item_key: str, correct_answer: str) -> tuple[int, str]:
    """Admin-triggered settlement. Returns (users_settled, error_msg)."""
    item = get_item(item_key)
    if not item:
        return 0, "找不到項目"
    if item.get("status") == "settled":
        return 0, "已結算"
    n = _do_settle(item_key, correct_answer.strip(), _now(), _BASE_LONGTERM)
    return n, ""


def revoke_longterm_item(item_key: str) -> tuple[int, str]:
    """Admin-triggered settlement revocation. Reverses coins and resets status to open.

    Returns (users_affected, error_msg).
    """
    item = get_item(item_key)
    if not item:
        return 0, "找不到項目"
    if item.get("status") != "settled":
        return 0, "此項目尚未結算，無需撤銷"

    preds = fetch_all(
        "SELECT id, nickname, coins_earned FROM user_predictions WHERE item_key=? AND settled=1",
        (item_key,),
    )
    count = 0
    for pred in preds:
        coins_to_return = int(pred["coins_earned"])
        if coins_to_return > 0:
            execute_query(
                "UPDATE prophet_users SET coins = MAX(0, coins - ?) WHERE nickname = ?",
                (coins_to_return, str(pred["nickname"])),
            )
        execute_query(
            "UPDATE user_predictions SET settled=0, coins_earned=0 WHERE id=?",
            (int(pred["id"]),),
        )
        count += 1

    execute_query("DELETE FROM settlement_events WHERE item_key=?", (item_key,))
    execute_query("UPDATE prediction_items SET status='open' WHERE item_key=?", (item_key,))
    return count, ""


def _do_settle(item_key: str, correct_answer: str, settled_at: str, base: int) -> int:
    execute_query(
        "INSERT OR REPLACE INTO settlement_events (item_key, correct_answer, settled_at) VALUES (?,?,?)",
        (item_key, correct_answer, settled_at),
    )
    execute_query(
        "UPDATE prediction_items SET status='settled', locked_at=COALESCE(locked_at,?) WHERE item_key=?",
        (settled_at, item_key),
    )

    item = fetch_one("SELECT opened_at FROM prediction_items WHERE item_key=?", (item_key,))
    opened_at = item["opened_at"] if item else settled_at

    preds = fetch_all(
        "SELECT * FROM user_predictions WHERE item_key=? AND settled=0", (item_key,)
    )
    count = 0
    for pred in preds:
        p = dict(pred)
        correct = p["prediction"].strip().lower() == correct_answer.strip().lower()
        coins = 0
        if correct:
            coins = _calc_coins(opened_at, p["last_changed_at"], settled_at, base)
            execute_query(
                "UPDATE prophet_users SET coins=coins+? WHERE nickname=?",
                (coins, p["nickname"]),
            )
        execute_query(
            "UPDATE user_predictions SET settled=1, coins_earned=? WHERE id=?",
            (coins, p["id"]),
        )
        count += 1
    return count


# ── Coin formula ──────────────────────────────────────────────────────────────

def _calc_coins(opened_at: str, last_changed_at: str, settled_at: str, base: int) -> int:
    t_open  = _parse_ts(opened_at)
    t_pred  = _parse_ts(last_changed_at)
    t_close = _parse_ts(settled_at)
    window  = (t_close - t_open).total_seconds()
    if window <= 0:
        return base
    t = max(0.0, min(1.0, (t_pred - t_open).total_seconds() / window))
    return max(1, round(base * math.exp(-_LAMBDA * t)))


# ── Player / team search (for long-term prediction UI) ───────────────────────

def search_players(keyword: str) -> list[str]:
    """Return player full names matching keyword (case-insensitive). Max 30 results."""
    if len(keyword) < 2:
        return []
    try:
        from nba_api.stats.static import players as nba_players
        kw = keyword.lower()
        return [
            p["full_name"]
            for p in nba_players.get_players()
            if kw in p["full_name"].lower()
        ][:30]
    except Exception:
        return []


def series_item_key(series: dict[str, Any], season: str | None = None) -> str | None:
    """Public helper so the UI can match series to prediction items."""
    return _series_key(series, season or get_current_season())


def get_nba_team_names() -> list[str]:
    """All 30 NBA team full names (for champion prediction)."""
    try:
        from nba_api.stats.static import teams as nba_teams
        return sorted(t["full_name"] for t in nba_teams.get_teams())
    except Exception:
        return []


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _series_key(series: dict[str, Any], season: str) -> str | None:
    a   = str(series.get("team_a_abbr") or "")
    b   = str(series.get("team_b_abbr") or "")
    rnd = int(series.get("round_num") or 0)
    if not a or not b or not rnd:
        return None
    return f"{season}_r{rnd}_{'_'.join(sorted([a, b]))}"


def _series_label(series: dict[str, Any], rnd: int) -> str:
    a   = series.get("team_a", "?")
    b   = series.get("team_b", "?")
    rnd_label = _ROUND_ZH.get(rnd, f"第{rnd}輪")
    return f"{rnd_label}：{a} vs {b}"
