from __future__ import annotations

from pathlib import Path
from typing import Optional


def get_checkpointer():
    """Return a LangGraph checkpointer (SQLite if available, else in-memory).

    - Uses data/agent_memory.sqlite when SQLite saver is available.
    - Falls back to in-process MemorySaver for ephemeral sessions.
    """
    # Try SQLite saver (persistent)
    try:
        # LangGraph moved modules across versions; try multiple import paths
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
        except Exception:
            from langgraph.checkpoint.sql import SqliteSaver  # type: ignore

        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "agent_memory.sqlite"
        return SqliteSaver(db_path)
    except Exception:
        # Fallback to in-memory saver
        try:
            from langgraph.checkpoint.memory import MemorySaver  # type: ignore

            return MemorySaver()
        except Exception:
            return None


def ensure_thread_id(thread_id: Optional[str]) -> str:
    return thread_id or "default"
