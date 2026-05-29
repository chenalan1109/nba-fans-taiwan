"""球員殿堂投票服務：無正確答案、不結算先知幣，純粹情感表態。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from database.db import fetch_all, fetch_one, get_connection

# ── Poll definitions ───────────────────────────────────────────────────────────

HALL_POLLS: list[dict[str, Any]] = [
    {
        "key": "goat",
        "title": "歷史 GOAT",
        "subtitle": "史上你認為最偉大的籃球員是誰？",
        "type": "player",
    },
    {
        "key": "best_active",
        "title": "現役第一人",
        "subtitle": "現役球員中，你認為誰是當今最強？",
        "type": "player",
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
    },
    {
        "key": "underrated",
        "title": "最被低估的球員",
        "subtitle": "你認為歷史上或現役最被忽視、最不被記憶的球員是誰？",
        "type": "player",
    },
    {
        "key": "fav_team",
        "title": "最喜歡的球隊",
        "subtitle": "你心目中最愛的 NBA 球隊？",
        "type": "team",
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
    },
]

# ── CRUD ───────────────────────────────────────────────────────────────────────

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
