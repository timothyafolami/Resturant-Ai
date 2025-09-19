from typing import Optional
from langchain_core.tools import tool
from src.memory.store import MemoryStore
from src.utils.logging import setup_logger


logger = setup_logger()
store = MemoryStore()


@tool
def save_memory(thread_id: str, content: str, tags: Optional[str] = None, importance: int = 1) -> str:
    """Save a long-term memory for a given thread.

    - thread_id: conversation/thread identifier
    - content: memory text (preference, profile fact, decision, outcome)
    - tags: optional comma-separated tags
    - importance: 1-5 (default 1)
    """
    try:
        tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
        mem_id = store.add_memory(thread_id, content, tag_list, int(importance), source="tool")
        logger.info(f"🧠 Saved memory {mem_id} for thread {thread_id}")
        return f"✅ Saved memory ({mem_id})"
    except Exception as e:
        return f"❌ Error saving memory: {str(e)}"


@tool
def list_memories(thread_id: str, limit: int = 20) -> str:
    """List recent memories for a given thread.

    - thread_id: conversation/thread identifier
    - limit: number of items (default 20)
    """
    try:
        items = store.list_memories(thread_id, int(limit))
        if not items:
            return "No memories stored."
        lines = ["🗂️ Memories:"]
        for m in items:
            tags = ", ".join(m.get("tags", []))
            lines.append(f"- {m['id']}: {m['content']} [{tags}] ({m['updated_at'][:19]})")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error listing memories: {str(e)}"


@tool
def search_memory(thread_id: str, query: str, limit: int = 5) -> str:
    """Search memories for a given thread by keyword."""
    try:
        items = store.search(thread_id, query, int(limit))
        if not items:
            return "No matching memories."
        lines = [f"🔍 Memory search for '{query}':"]
        for m in items:
            lines.append(f"- {m['id']}: {m['content']} [{', '.join(m.get('tags', []))}]")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error searching memories: {str(e)}"


@tool
def delete_memory(thread_id: str, memory_id: str) -> str:
    """Delete a memory by id for a given thread."""
    try:
        ok = store.delete_memory(thread_id, memory_id)
        return "🗑️ Deleted." if ok else "Not found."
    except Exception as e:
        return f"❌ Error deleting memory: {str(e)}"


AGENT_MEMORY_TOOLS = [save_memory, list_memories, search_memory, delete_memory]
