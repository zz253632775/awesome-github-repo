"""SQLite connection and migration helpers."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .models import CREATE_TABLES_SQL

LOGGER = logging.getLogger(__name__)


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path | str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as conn:
        conn.executescript(CREATE_TABLES_SQL)
    LOGGER.info("SQLite database initialized at %s", path)


def upsert_many(conn: sqlite3.Connection, sql: str, rows: Iterable[Mapping[str, object] | Sequence[object]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    conn.executemany(sql, rows)
    return len(rows)
