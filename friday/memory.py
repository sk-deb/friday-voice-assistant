"""Durable local memory: remembered facts plus a conversation log.

Everything is stored in a single SQLite file under the data directory. No
network, no vector database, no external service.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fact       TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role       TEXT NOT NULL,
    text       TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_turns_created_at ON turns (created_at);
"""


class Memory:
    """Tiny SQLite wrapper. Safe to share across threads."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)
        self._db.commit()

    # ---------------------------------------------------------------- facts
    def remember(self, fact: str) -> bool:
        """Store a fact. Returns False when it was already known."""
        fact = fact.strip()
        if not fact:
            return False
        try:
            self._db.execute(
                "INSERT INTO facts (fact, created_at) VALUES (?, ?)",
                (fact, time.time()),
            )
            self._db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def forget(self, needle: str) -> int:
        """Delete every fact containing ``needle``. Returns the row count."""
        needle = needle.strip()
        if not needle:
            return 0
        cur = self._db.execute("DELETE FROM facts WHERE fact LIKE ?", (f"%{needle}%",))
        self._db.commit()
        return cur.rowcount

    def facts(self, limit: int = 100) -> list[str]:
        rows = self._db.execute(
            "SELECT fact FROM facts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [row["fact"] for row in rows]

    def as_prompt_block(self, limit: int = 50) -> str:
        """Render known facts for injection into the system prompt."""
        facts = self.facts(limit)
        return "\n".join(f"- {fact}" for fact in reversed(facts))

    # ---------------------------------------------------------------- turns
    def log_turn(self, role: str, text: str) -> None:
        self._db.execute(
            "INSERT INTO turns (role, text, created_at) VALUES (?, ?, ?)",
            (role, text, time.time()),
        )
        self._db.commit()

    def recent_turns(self, limit: int = 20) -> list[dict[str, object]]:
        rows = self._db.execute(
            "SELECT role, text, created_at FROM turns "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    # ---------------------------------------------------------------- misc
    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> Memory:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
