from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, cast

from config.settings import get_database_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nba_fans_taiwan.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_PG_SCHEMA_PATH = Path(__file__).with_name("schema_pg.sql")


def _pg_dsn() -> str | None:
    url = get_database_url()
    return url if url and url.startswith(("postgresql://", "postgres://")) else None


class _PgConnection:
    """psycopg2 connection wrapper that matches the sqlite3 usage patterns in this codebase."""

    def __init__(self, dsn: str) -> None:
        import psycopg2  # type: ignore[import]
        import psycopg2.extras  # type: ignore[import]
        self._conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
        self._cur: Any = None
        self._cached_lastrowid: int | None = None
        self._lastrowid_fetched: bool = False

    def execute(self, sql: str, params: Any = ()) -> "_PgConnection":
        pg_sql = sql.replace("?", "%s")
        # Convert SQLite-only INSERT variants to Postgres equivalents
        is_or_variant = bool(re.match(r"^\s*INSERT\s+OR\s+(IGNORE|REPLACE)\b", pg_sql, re.IGNORECASE))
        if is_or_variant:
            pg_sql = re.sub(r"(?i)INSERT\s+OR\s+(IGNORE|REPLACE)\b", "INSERT", pg_sql, count=1)
        # Auto-append RETURNING * for INSERT so callers can use .lastrowid.
        # Use * instead of id because some tables (e.g. prediction_items) have no id column.
        if pg_sql.strip().upper().startswith("INSERT") and "RETURNING" not in pg_sql.upper():
            conflict = " ON CONFLICT DO NOTHING" if is_or_variant else ""
            pg_sql = pg_sql.rstrip() + conflict + " RETURNING *"
        self._cur = self._conn.cursor()
        self._cur.execute(pg_sql, list(params) if params else [])
        self._cached_lastrowid = None
        self._lastrowid_fetched = False
        return self

    def executescript(self, sql: str) -> None:
        cur = self._conn.cursor()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.upper().startswith("PRAGMA"):
                cur.execute(stmt)

    def fetchall(self) -> list[Any]:
        return list(self._cur.fetchall()) if self._cur is not None else []

    def fetchone(self) -> Any:
        return self._cur.fetchone() if self._cur is not None else None

    @property
    def lastrowid(self) -> int | None:
        if self._lastrowid_fetched:
            return self._cached_lastrowid
        self._lastrowid_fetched = True
        if self._cur is None:
            return None
        row = self._cur.fetchone()
        self._cached_lastrowid = int(row["id"]) if row and "id" in row else None
        return self._cached_lastrowid

    def __enter__(self) -> "_PgConnection":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()
        return False


def get_default_db_path() -> Path:
    database_url = get_database_url()
    if database_url and database_url.startswith("sqlite:///"):
        return Path(database_url.removeprefix("sqlite:///"))
    return DEFAULT_DB_PATH


def get_connection(db_path: str | Path | None = None) -> Any:
    dsn = _pg_dsn()
    if dsn:
        return _PgConnection(dsn)
    path = Path(db_path) if db_path is not None else get_default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    dsn = _pg_dsn()
    if dsn:
        schema = _PG_SCHEMA_PATH.read_text(encoding="utf-8")
        with _PgConnection(dsn) as conn:
            conn.executescript(schema)
    else:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with get_connection(db_path) as connection:
            connection.executescript(schema)
    _run_migrations(db_path)


def _run_migrations(db_path: str | Path | None = None) -> None:
    """Add new columns to existing tables without dropping data."""
    dsn = _pg_dsn()
    migrations = [
        "ALTER TABLE polls ADD COLUMN correct_answer TEXT",
        "ALTER TABLE polls ADD COLUMN completed_at TEXT",
        (
            "CREATE TABLE IF NOT EXISTS custom_matchups ("
            "id TEXT PRIMARY KEY, title TEXT NOT NULL, "
            "team_a_name TEXT NOT NULL, team_b_name TEXT NOT NULL, "
            "team_a_players TEXT NOT NULL, team_b_players TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        ),
        "ALTER TABLE custom_matchups ADD COLUMN creator_id TEXT",
        (
            "CREATE TABLE IF NOT EXISTS game_comments ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "game_id TEXT NOT NULL, voter_id TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS comment_likes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "comment_id INTEGER NOT NULL, voter_id TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE (comment_id, voter_id), "
            "FOREIGN KEY (comment_id) REFERENCES game_comments(id))"
        ),
        (
            "CREATE TABLE IF NOT EXISTS user_accounts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT UNIQUE NOT NULL, "
            "password_hash TEXT NOT NULL, "
            "nickname TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS user_player_pool ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT NOT NULL, "
            "player_id INTEGER NOT NULL, "
            "player_name TEXT NOT NULL, "
            "purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE (username, player_id))"
        ),
        (
            "CREATE TABLE IF NOT EXISTS hall_poll_definitions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "poll_key TEXT UNIQUE NOT NULL, "
            "title TEXT NOT NULL, "
            "subtitle TEXT NOT NULL, "
            "poll_type TEXT NOT NULL CHECK (poll_type IN ('player', 'team', 'custom')), "
            "options_json TEXT, "
            "is_active INTEGER NOT NULL DEFAULT 1, "
            "display_order INTEGER NOT NULL DEFAULT 0, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS daily_checkins ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username TEXT NOT NULL, "
            "checkin_date TEXT NOT NULL, "
            "coins_earned INTEGER NOT NULL DEFAULT 150, "
            "UNIQUE (username, checkin_date))"
        ),
    ]
    pg_migrations = [
        "ALTER TABLE polls ADD COLUMN IF NOT EXISTS correct_answer TEXT",
        "ALTER TABLE polls ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ",
        (
            "CREATE TABLE IF NOT EXISTS custom_matchups ("
            "id TEXT PRIMARY KEY, title TEXT NOT NULL, "
            "team_a_name TEXT NOT NULL, team_b_name TEXT NOT NULL, "
            "team_a_players TEXT NOT NULL, team_b_players TEXT NOT NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        ),
        "ALTER TABLE custom_matchups ADD COLUMN IF NOT EXISTS creator_id TEXT",
        (
            "CREATE TABLE IF NOT EXISTS game_comments ("
            "id BIGSERIAL PRIMARY KEY, "
            "game_id TEXT NOT NULL, voter_id TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        ),
        (
            "CREATE TABLE IF NOT EXISTS comment_likes ("
            "id BIGSERIAL PRIMARY KEY, "
            "comment_id BIGINT NOT NULL REFERENCES game_comments(id) ON DELETE CASCADE, "
            "voter_id TEXT NOT NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
            "UNIQUE (comment_id, voter_id))"
        ),
        (
            "CREATE TABLE IF NOT EXISTS user_accounts ("
            "id BIGSERIAL PRIMARY KEY, "
            "username TEXT UNIQUE NOT NULL, "
            "password_hash TEXT NOT NULL, "
            "nickname TEXT NOT NULL, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        ),
        (
            "CREATE TABLE IF NOT EXISTS user_player_pool ("
            "id BIGSERIAL PRIMARY KEY, "
            "username TEXT NOT NULL, "
            "player_id INTEGER NOT NULL, "
            "player_name TEXT NOT NULL, "
            "purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
            "UNIQUE (username, player_id))"
        ),
        (
            "CREATE TABLE IF NOT EXISTS hall_poll_definitions ("
            "id BIGSERIAL PRIMARY KEY, "
            "poll_key TEXT UNIQUE NOT NULL, "
            "title TEXT NOT NULL, "
            "subtitle TEXT NOT NULL, "
            "poll_type TEXT NOT NULL CHECK (poll_type IN ('player', 'team', 'custom')), "
            "options_json TEXT, "
            "is_active INTEGER NOT NULL DEFAULT 1, "
            "display_order INTEGER NOT NULL DEFAULT 0, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        ),
        (
            "CREATE TABLE IF NOT EXISTS daily_checkins ("
            "id BIGSERIAL PRIMARY KEY, "
            "username TEXT NOT NULL, "
            "checkin_date TEXT NOT NULL, "
            "coins_earned INTEGER NOT NULL DEFAULT 150, "
            "UNIQUE (username, checkin_date))"
        ),
    ]
    stmts = pg_migrations if dsn else migrations
    for sql in stmts:
        try:
            with get_connection(db_path) as conn:
                conn.execute(sql)
        except Exception:
            pass  # Column already exists or table already created


def execute_query(
    sql: str,
    params: tuple[Any, ...] = (),
    db_path: str | Path | None = None,
) -> None:
    with get_connection(db_path) as connection:
        connection.execute(sql, params)


def fetch_all(
    sql: str,
    params: tuple[Any, ...] = (),
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    with get_connection(db_path) as connection:
        cursor = connection.execute(sql, params)
        return cursor.fetchall()  # type: ignore[return-value]


def fetch_one(
    sql: str,
    params: tuple[Any, ...] = (),
    db_path: str | Path | None = None,
) -> sqlite3.Row | None:
    with get_connection(db_path) as connection:
        cursor = connection.execute(sql, params)
        return cast(sqlite3.Row | None, cursor.fetchone())
