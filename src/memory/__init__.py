from __future__ import annotations

import importlib
import asyncio
import importlib
import sqlite3
from pathlib import Path
from typing import Optional, AsyncIterator


_CHECKPOINTER = None
_ASYNC_SQLITE_COMPAT = None


def _load_sqlite_saver():
    """Return the first SqliteSaver available for the installed LangGraph build."""

    for module_name in (
        "langgraph.checkpoint.sqlite",        # < 0.6 packaged sqlite saver
        "langgraph.checkpoint.sql",           # 0.6.3 – 0.6.6 fallback name
        "langgraph.checkpoint.sqlite.aio",    # optional async build
        "langgraph_checkpoint.sqlite",        # langgraph-checkpoint-sqlite>=2.0
        "langgraph_checkpoint_sqlite",        # legacy naming
    ):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        saver = getattr(module, "SqliteSaver", None)
        if saver:
            return saver
    return None


def _build_async_sqlite_compat(sqlite_cls, db_path: Path):
    """Create a SqliteSaver subclass that implements the async API using threads."""

    global _ASYNC_SQLITE_COMPAT
    if _ASYNC_SQLITE_COMPAT is None:

        class AsyncSqliteCompat(sqlite_cls):  # type: ignore[valid-type]
            async def aget(self, config):  # type: ignore[override]
                return await asyncio.to_thread(sqlite_cls.get, self, config)

            async def aget_tuple(self, config):  # type: ignore[override]
                return await asyncio.to_thread(sqlite_cls.get_tuple, self, config)

            async def alist(  # type: ignore[override]
                self,
                config=None,
                *,
                filter=None,
                before=None,
                limit=None,
            ) -> AsyncIterator:
                rows = await asyncio.to_thread(
                    lambda: list(
                        sqlite_cls.list(
                            self,
                            config,
                            filter=filter,
                            before=before,
                            limit=limit,
                        )
                    )
                )
                for row in rows:
                    yield row

            async def aput(self, config, checkpoint, metadata, new_versions):  # type: ignore[override]
                return await asyncio.to_thread(
                    sqlite_cls.put, self, config, checkpoint, metadata, new_versions
                )

            async def aput_writes(self, config, writes, task_id, task_path=""):  # type: ignore[override]
                await asyncio.to_thread(
                    sqlite_cls.put_writes, self, config, writes, task_id, task_path
                )

            async def adelete_thread(self, thread_id):  # type: ignore[override]
                await asyncio.to_thread(sqlite_cls.delete_thread, self, thread_id)

        _ASYNC_SQLITE_COMPAT = AsyncSqliteCompat

    conn = sqlite3.connect(db_path, check_same_thread=False)
    return _ASYNC_SQLITE_COMPAT(conn)


def get_checkpointer():
    """Return a process-wide LangGraph checkpointer.

    Prefers the SQLite saver for persistence but reuses a single MemorySaver
    instance when SQLite support is not installed. Reusing the saver is
    critical so that conversation history survives across Streamlit runs.
    """

    global _CHECKPOINTER
    if _CHECKPOINTER is not None:
        return _CHECKPOINTER

    sqlite_cls = _load_sqlite_saver()
    if sqlite_cls is not None:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "agent_memory.sqlite"
        _CHECKPOINTER = _build_async_sqlite_compat(sqlite_cls, db_path)
        return _CHECKPOINTER

    try:
        from langgraph.checkpoint.memory import MemorySaver  # type: ignore
    except Exception:
        return None

    _CHECKPOINTER = MemorySaver()
    return _CHECKPOINTER


def ensure_thread_id(thread_id: Optional[str]) -> str:
    return thread_id or "default"
