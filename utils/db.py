"""Per-user persistence for owned-character and used-pair state, backed by SQLite
(data/app.db) instead of the old single-shared JSON files. Each row is keyed by
`user_id` (the logged-in username from utils/auth.py) so concurrent users deployed
against the same app instance don't overwrite each other's data. Still a local file,
consistent with the "no cloud infra" constraint - just one that handles concurrent
read/write correctly, which flat JSON files do not.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("data/app.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS owned_characters (
    user_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    PRIMARY KEY (user_id, character_name)
);
CREATE TABLE IF NOT EXISTS used_pairs (
    user_id TEXT NOT NULL,
    pair_key TEXT NOT NULL,
    PRIMARY KEY (user_id, pair_key)
);
"""


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def load_owned_characters(user_id: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT character_name FROM owned_characters WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row[0] for row in rows}


def save_owned_characters(user_id: str, owned: set[str]) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM owned_characters WHERE user_id = ?", (user_id,))
        conn.executemany(
            "INSERT INTO owned_characters (user_id, character_name) VALUES (?, ?)",
            [(user_id, name) for name in owned],
        )


def load_used_pairs(user_id: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT pair_key FROM used_pairs WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row[0] for row in rows}


def save_used_pairs(user_id: str, used: set[str]) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM used_pairs WHERE user_id = ?", (user_id,))
        conn.executemany(
            "INSERT INTO used_pairs (user_id, pair_key) VALUES (?, ?)",
            [(user_id, key) for key in used],
        )


def used_pair_key(combo_id: str, target: str, weather: str) -> str:
    return f"{combo_id}|{target}|{weather}"
