import sqlite3
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


class MemoryStore:
    def __init__(self, db_path: Path | str = Path("data/memories.sqlite")) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    importance INTEGER DEFAULT 1,
                    source TEXT DEFAULT 'agent',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_mem_thread ON memories(thread_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_mem_updated ON memories(updated_at)")

    def add_memory(
        self,
        thread_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance: int = 1,
        source: str = "agent",
    ) -> str:
        mem_id = uuid.uuid4().hex
        now = datetime.now().isoformat()
        with self._conn() as con:
            con.execute(
                "INSERT INTO memories(id, thread_id, content, tags, importance, source, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    mem_id,
                    thread_id,
                    content,
                    json.dumps(tags or []),
                    importance,
                    source,
                    now,
                    now,
                ),
            )
        return mem_id

    def list_memories(self, thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT id, content, tags, importance, source, created_at, updated_at FROM memories WHERE thread_id=? ORDER BY updated_at DESC LIMIT ?",
                (thread_id, limit),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "content": r[1],
                    "tags": json.loads(r[2] or "[]"),
                    "importance": r[3],
                    "source": r[4],
                    "created_at": r[5],
                    "updated_at": r[6],
                }
            )
        return out

    def delete_memory(self, thread_id: str, mem_id: str) -> bool:
        with self._conn() as con:
            cur = con.execute(
                "DELETE FROM memories WHERE id=? AND thread_id=?",
                (mem_id, thread_id),
            )
            return cur.rowcount > 0

    def search(self, thread_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # naive LIKE-based search; upgrade to FTS if needed
        pattern = f"%{query.lower()}%"
        with self._conn() as con:
            rows = con.execute(
                "SELECT id, content, tags, importance, source, created_at, updated_at FROM memories WHERE thread_id=? AND LOWER(content) LIKE ? ORDER BY updated_at DESC LIMIT ?",
                (thread_id, pattern, limit),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "content": r[1],
                    "tags": json.loads(r[2] or "[]"),
                    "importance": r[3],
                    "source": r[4],
                    "created_at": r[5],
                    "updated_at": r[6],
                }
            )
        return out

