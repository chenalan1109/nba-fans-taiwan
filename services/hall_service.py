"""球員殿堂投票服務：無正確答案、不結算先知幣，純粹情感表態。

Poll definitions 存於 hall_poll_definitions 表（由管理員維護）。
若 DB 中尚無自定義項目，自動以預設清單填充（idempotent）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database.db import execute_query, fetch_all, fetch_one, get_connection

# ── Default poll definitions (used as seed if DB table is empty) ──────────────

_DEFAULT_POLLS: list[dict[str, Any]] = [
    {
        "key": "goat",
        "title": "歷史 GOAT",
        "subtitle": "史上你認為最偉大的籃球員是誰？",
        "type": "player",
        "options": None,
        "order": 0,
    },
    {
        "key": "best_active",
        "title": "現役第一人",
        "subtitle": "現役球員中，你認為誰是當今最強？",
        "type": "player",
        "options": None,
        "order": 1,
    },
    {
        "key": "dream_duel",
        "title": "最想看的跨時代夢幻單挑",
        "subtitle": "最想親眼目睹哪一場跨世代對決？",
        "type": "custom",
        "options": [
            "Michael Jordan vs LeBron James",
            "Michael Jordan vs Kobe Bryant",
            "Kobe Bryant vs LeBron James",
            "Shaquille O'Neal vs Wilt Chamberlain",
            "Magic Johnson vs Stephen Curry",
            "Larry Bird vs Kevin Durant",
            "Oscar Robertson vs Russell Westbrook",
            "Hakeem Olajuwon vs Nikola Jokić",
        ],
        "order": 2,
    },
    {
        "key": "underrated",
        "title": "最被低估的球員",
        "subtitle": "你認為歷史上或現役最被忽視、最不被記憶的球員是誰？",
        "type": "player",
        "options": None,
        "order": 3,
    },
    {
        "key": "fav_team",
        "title": "最喜歡的球隊",
        "subtitle": "你心目中最愛的 NBA 球隊？",
        "type": "team",
        "options": None,
        "order": 4,
    },
    {
        "key": "signature_move",
        "title": "最想擁有的招牌動作",
        "subtitle": "如果你能擁有一個 NBA 球員的招牌動作，你想要哪個？",
        "type": "custom",
        "options": [
            "Kareem Abdul-Jabbar 的天勾（Skyhook）",
            "Stephen Curry 的超遠三分球",
            "Kobe Bryant 的後仰跳投",
            "Michael Jordan 的中距離 Fadeaway",
            "Tim Duncan 的底線打板",
            "Hakeem Olajuwon 的夢幻腳步",
            "Kyrie Irving 的運球過人",
            "Kevin Durant 的無解高位單打",
        ],
        "order": 5,
    },
]

# Keep HALL_POLLS as a module-level alias for backwards compatibility
HALL_POLLS: list[dict[str, Any]] = []


# ── DB-backed poll definition management ─────────────────────────────────────

def _seed_default_polls(db_path: str | Path | None = None) -> None:
    """Insert default polls into DB if the table is empty (idempotent)."""
    existing = fetch_all(
        "SELECT id FROM hall_poll_definitions LIMIT 1",
        db_path=db_path,
    )
    if existing:
        return
    for p in _DEFAULT_POLLS:
        options_json = json.dumps(p["options"], ensure_ascii=False) if p["options"] else None
        execute_query(
            "INSERT OR IGNORE INTO hall_poll_definitions "
            "(poll_key, title, subtitle, poll_type, options_json, display_order) VALUES (?,?,?,?,?,?)",
            (p["key"], p["title"], p["subtitle"], p["type"], options_json, p["order"]),
            db_path=db_path,
        )


def get_hall_polls(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return active poll definitions from DB, seeding defaults on first call."""
    _seed_default_polls(db_path)
    rows = fetch_all(
        "SELECT poll_key, title, subtitle, poll_type, options_json "
        "FROM hall_poll_definitions WHERE is_active = 1 "
        "ORDER BY display_order ASC, id ASC",
        db_path=db_path,
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        options = json.loads(str(row["options_json"])) if row["options_json"] else []
        result.append({
            "key": str(row["poll_key"]),
            "title": str(row["title"]),
            "subtitle": str(row["subtitle"]),
            "type": str(row["poll_type"]),
            "options": options if options else [],
        })
    # Keep module-level alias in sync
    global HALL_POLLS
    HALL_POLLS = result
    return result


def create_hall_poll(
    poll_key: str,
    title: str,
    subtitle: str,
    poll_type: str,
    options: list[str] | None = None,
    db_path: str | Path | None = None,
) -> tuple[bool, str]:
    """Admin: create a new Hall poll definition."""
    poll_key = poll_key.strip().lower().replace(" ", "_")
    title = title.strip()
    subtitle = subtitle.strip()
    if not poll_key or not title or not subtitle:
        return False, "poll_key、標題和副標題不能為空。"
    if poll_type not in ("player", "team", "custom"):
        return False, "類型必須是 player、team 或 custom。"
    if poll_type == "custom" and not options:
        return False, "custom 類型必須提供選項。"

    existing = fetch_one(
        "SELECT id FROM hall_poll_definitions WHERE poll_key = ?",
        (poll_key,),
        db_path=db_path,
    )
    if existing:
        return False, f"Poll key '{poll_key}' 已存在。"

    max_order_row = fetch_one(
        "SELECT MAX(display_order) AS max_order FROM hall_poll_definitions",
        db_path=db_path,
    )
    next_order = (int(max_order_row["max_order"]) + 1) if max_order_row and max_order_row["max_order"] is not None else 0

    options_json = json.dumps(options, ensure_ascii=False) if options else None
    try:
        execute_query(
            "INSERT INTO hall_poll_definitions (poll_key, title, subtitle, poll_type, options_json, display_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (poll_key, title, subtitle, poll_type, options_json, next_order),
            db_path=db_path,
        )
        return True, "投票主題已新增。"
    except Exception as exc:
        return False, f"新增失敗：{exc}"


def delete_hall_poll(poll_key: str, db_path: str | Path | None = None) -> tuple[bool, str]:
    """Admin: soft-delete a Hall poll (set is_active=0)."""
    row = fetch_one(
        "SELECT id FROM hall_poll_definitions WHERE poll_key = ?",
        (poll_key,),
        db_path=db_path,
    )
    if not row:
        return False, "找不到該投票主題。"
    try:
        execute_query(
            "UPDATE hall_poll_definitions SET is_active = 0 WHERE poll_key = ?",
            (poll_key,),
            db_path=db_path,
        )
        return True, "投票主題已停用。"
    except Exception as exc:
        return False, f"操作失敗：{exc}"


def restore_hall_poll(poll_key: str, db_path: str | Path | None = None) -> tuple[bool, str]:
    """Admin: restore a soft-deleted Hall poll."""
    try:
        execute_query(
            "UPDATE hall_poll_definitions SET is_active = 1 WHERE poll_key = ?",
            (poll_key,),
            db_path=db_path,
        )
        return True, "投票主題已恢復。"
    except Exception as exc:
        return False, f"操作失敗：{exc}"


def list_all_hall_polls(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Admin: return all poll definitions including inactive ones."""
    _seed_default_polls(db_path)
    rows = fetch_all(
        "SELECT poll_key, title, poll_type, is_active FROM hall_poll_definitions ORDER BY display_order ASC, id ASC",
        db_path=db_path,
    )
    return [dict(r) for r in rows]  # type: ignore[arg-type]


# ── Vote CRUD ─────────────────────────────────────────────────────────────────

def get_hall_vote(poll_key: str, voter_id: str, db_path: str | Path | None = None) -> str | None:
    """Return the voter's current choice for this poll, or None if not voted."""
    row = fetch_one(
        "SELECT choice FROM hall_votes WHERE poll_key = ? AND voter_id = ?",
        (poll_key, voter_id.strip()),
        db_path=db_path,
    )
    return str(row["choice"]) if row else None


def upsert_hall_vote(
    poll_key: str,
    voter_id: str,
    choice: str,
    db_path: str | Path | None = None,
) -> bool:
    """Insert or update the voter's choice. Returns True on success."""
    voter_id = voter_id.strip()
    choice = choice.strip()
    if not voter_id or not choice:
        return False
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                "DELETE FROM hall_votes WHERE poll_key = ? AND voter_id = ?",
                (poll_key, voter_id),
            )
            conn.execute(
                "INSERT INTO hall_votes (poll_key, voter_id, choice) VALUES (?, ?, ?)",
                (poll_key, voter_id, choice),
            )
        return True
    except Exception:
        return False


def get_hall_distribution(
    poll_key: str,
    top_n: int = 4,
    db_path: str | Path | None = None,
) -> tuple[list[str], list[int]]:
    """Return labels + values for top_n choices; remainder bucketed as '其他'."""
    rows = fetch_all(
        "SELECT choice, COUNT(*) AS cnt FROM hall_votes WHERE poll_key = ? GROUP BY choice ORDER BY cnt DESC",
        (poll_key,),
        db_path=db_path,
    )
    if not rows:
        return [], []

    labels: list[str] = []
    values: list[int] = []
    others = 0

    for i, row in enumerate(rows):
        if i < top_n:
            labels.append(str(row["choice"]))
            values.append(int(row["cnt"]))
        else:
            others += int(row["cnt"])

    if others > 0:
        labels.append("其他")
        values.append(others)

    return labels, values


def get_hall_ranking(poll_key: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return all choices ranked by vote count, with rank and percentage."""
    rows = fetch_all(
        "SELECT choice, COUNT(*) AS cnt FROM hall_votes WHERE poll_key = ? GROUP BY choice ORDER BY cnt DESC",
        (poll_key,),
        db_path=db_path,
    )
    if not rows:
        return []
    total = sum(int(r["cnt"]) for r in rows)
    return [
        {
            "排名": i + 1,
            "選項": str(r["choice"]),
            "票數": int(r["cnt"]),
            "佔比": f"{int(r['cnt']) / total * 100:.1f}%",
        }
        for i, r in enumerate(rows)
    ]
