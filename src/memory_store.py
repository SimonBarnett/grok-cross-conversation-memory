"""Persistent memory store for Grok conversations.

Stores per-user memories (summaries, key facts, preferences) so that
context carries over between separate conversations.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_DB = Path.home() / ".grok" / "memory.db"


@dataclass
class Memory:
    """A single stored memory entry."""

    id: Optional[int]
    user_id: str
    content: str
    kind: str  # "summary", "fact", "preference"
    source_conversation: Optional[str]
    created_at: str
    updated_at: str
    importance: float = 0.5


class MemoryStore:
    """SQLite-backed store for cross-conversation memories."""

    def __init__(self, db_path: Path = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source_conversation TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)"
            )

    def add(
        self,
        user_id: str,
        content: str,
        kind: str = "fact",
        source_conversation: Optional[str] = None,
        importance: float = 0.5,
    ) -> Memory:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO memories
                    (user_id, content, kind, source_conversation, created_at, updated_at, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, content, kind, source_conversation, now, now, importance),
            )
            mem_id = cur.lastrowid
        return Memory(
            id=mem_id,
            user_id=user_id,
            content=content,
            kind=kind,
            source_conversation=source_conversation,
            created_at=now,
            updated_at=now,
            importance=importance,
        )

    def get(self, memory_id: int) -> Optional[Memory]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
        return self._row_to_memory(row) if row else None

    def list_for_user(
        self,
        user_id: str,
        kind: Optional[str] = None,
        limit: int = 50,
    ) -> list[Memory]:
        query = "SELECT * FROM memories WHERE user_id = ?"
        params: list = [user_id]
        if kind:
            query += " AND kind = ?"
            params.append(kind)
        query += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def search(self, user_id: str, query: str, limit: int = 10) -> list[Memory]:
        """Simple substring search over memory content."""
        pattern = f"%{query.lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM memories
                WHERE user_id = ? AND lower(content) LIKE ?
                ORDER BY importance DESC
                LIMIT ?
                """,
                (user_id, pattern, limit),
            ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def update(
        self,
        memory_id: int,
        content: Optional[str] = None,
        importance: Optional[float] = None,
    ) -> Optional[Memory]:
        mem = self.get(memory_id)
        if not mem:
            return None
        new_content = content if content is not None else mem.content
        new_importance = importance if importance is not None else mem.importance
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE memories
                SET content = ?, importance = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_content, new_importance, now, memory_id),
            )
        return self.get(memory_id)

    def delete(self, memory_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cur.rowcount > 0

    def delete_all_for_user(self, user_id: str) -> int:
        """Delete every memory for a user. Supports the privacy requirement."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            return cur.rowcount

    def context_for_conversation(
        self, user_id: str, max_tokens: int = 2000
    ) -> str:
        """Build a context block to inject at the start of a new conversation.

        Rough token estimate: ~4 chars per token.
        """
        memories = self.list_for_user(user_id, limit=100)
        if not memories:
            return ""
        lines = ["## Persistent memory (from previous conversations)"]
        budget = max_tokens * 4
        used = len(lines[0])
        for m in memories:
            entry = f"- [{m.kind}] {m.content}"
            if used + len(entry) > budget:
                break
            lines.append(entry)
            used += len(entry)
        return "\n".join(lines)

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            user_id=row["user_id"],
            content=row["content"],
            kind=row["kind"],
            source_conversation=row["source_conversation"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            importance=row["importance"],
        )

    def export_json(self, user_id: str) -> str:
        """Export all memories for a user as JSON (portability / backup)."""
        memories = self.list_for_user(user_id, limit=10_000)
        return json.dumps([asdict(m) for m in memories], indent=2)
