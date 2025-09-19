import re

from typing import List, Any, Optional, Annotated

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from src.utils.logging import setup_logger
from src.utils.llm import llm
from src.tools import ALL_TOOLS, DATABASE_TOOLS, AGENT_MEMORY_TOOLS
from src.tools.memory_tools import store
from src.memory import get_checkpointer, ensure_thread_id
from src.ai_prompts.prompts import INTERNAL_AGENT_CONFIG, EXTERNAL_AGENT_CONFIG


logger = setup_logger()


# ========================
# Agent State
# ========================
class ChatState(BaseModel):
    """State for chat applications"""
    messages: Annotated[List[Any], add_messages]
    user_type: str = "internal"  # "internal" or "external"
    summary: Optional[str] = None  # running conversation summary
    memory: Optional[str] = None  # lightweight profile/context snapshot


# ========================
# Agent Nodes
# ========================
def internal_agent_node(state: ChatState):
    """Internal restaurant staff agent"""
    system_message = SystemMessage(content=INTERNAL_AGENT_CONFIG["system_prompt"])
    summary_message = (
        SystemMessage(content=f"Conversation summary (for context):\n{state.summary}")
        if state.summary
        else None
    )
    memory_message = (
        SystemMessage(content=state.memory)
        if state.memory
        else None
    )

    # Create LLM with tools for internal staff
    internal_llm = llm.bind_tools(ALL_TOOLS)

    # Build message stack: system prompt + optional summary + current turn messages
    messages = state.messages
    built: List[Any] = [system_message]
    if memory_message is not None:
        built.append(memory_message)
    if summary_message is not None:
        built.append(summary_message)
    built.extend(messages)

    response = internal_llm.invoke(built)
    return {"messages": [response]}


def external_agent_node(state: ChatState):
    """External customer agent"""
    system_message = SystemMessage(content=EXTERNAL_AGENT_CONFIG["system_prompt"])
    summary_message = (
        SystemMessage(content=f"Conversation summary (for context):\n{state.summary}")
        if state.summary
        else None
    )
    memory_message = (
        SystemMessage(content=state.memory)
        if state.memory
        else None
    )

    # Create LLM with limited tools for customers
    external_tools = [tool for tool in ALL_TOOLS if tool.name in EXTERNAL_AGENT_CONFIG["tools_available"]]
    external_llm = llm.bind_tools(external_tools)

    # Build message stack: system prompt + optional summary + current turn messages
    messages = state.messages
    built: List[Any] = [system_message]
    if memory_message is not None:
        built.append(memory_message)
    if summary_message is not None:
        built.append(summary_message)
    built.extend(messages)

    response = external_llm.invoke(built)
    return {"messages": [response]}


def router_node(state: ChatState):
    """Route to appropriate agent based on user type"""
    if state.user_type == "external":
        return external_agent_node(state)
    else:
        return internal_agent_node(state)


# ========================
# Create Chat Applications
# ========================
def create_internal_chat_app():
    """Create internal staff chat application"""
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("agent", internal_agent_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))

    def summarize_node(state: ChatState):
        """Update running summary from the latest user/assistant exchange."""
        try:
            prev = state.summary or ""
            # Extract latest human + AI messages for incremental update
            last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
            last_ai = next((m.content for m in reversed(state.messages) if isinstance(m, AIMessage)), "")
            prompt = [
                SystemMessage(content=(
                    "You are a conversation summarizer. Update the running summary with the latest exchange.\n"
                    "Keep it concise and factual. Include any decisions, preferences, or follow-ups."
                )),
                HumanMessage(content=(
                    f"Previous summary:\n{prev}\n\n"
                    f"Latest exchange:\nUser: {last_human}\nAssistant: {last_ai}\n\n"
                    f"Return the updated summary only."
                )),
            ]
            updated = llm.invoke(prompt)
            new_summary = updated.content.strip() if isinstance(updated, AIMessage) else str(updated)
            return {"summary": new_summary}
        except Exception:
            return {"summary": state.summary}
    
    # Add edges
    workflow.add_edge(START, "agent")

    # Route: if tools requested → tools; else → summarize
    def route_from_agent(state: ChatState):
        last = state.messages[-1] if state.messages else None
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "summarize"

    workflow.add_conditional_edges("agent", route_from_agent, {"tools": "tools", "summarize": "summarize"})
    workflow.add_edge("tools", "agent")

    # Summarize then end
    workflow.add_node("summarize", summarize_node)
    workflow.add_edge("summarize", END)
    
    # Compile with memory
    checkpointer = get_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


def create_external_chat_app():
    """Create external customer chat application"""
    # Limited tools for customers
    external_tools = [tool for tool in ALL_TOOLS if tool.name in EXTERNAL_AGENT_CONFIG["tools_available"]]

    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("agent", external_agent_node)
    workflow.add_node("tools", ToolNode(external_tools))
    
    def summarize_node(state: ChatState):
        try:
            prev = state.summary or ""
            last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
            last_ai = next((m.content for m in reversed(state.messages) if isinstance(m, AIMessage)), "")
            prompt = [
                SystemMessage(content=(
                    "You are a conversation summarizer. Update the running summary with the latest exchange.\n"
                    "Be concise, include preferences or constraints relevant to dining."
                )),
                HumanMessage(content=(
                    f"Previous summary:\n{prev}\n\n"
                    f"Latest exchange:\nUser: {last_human}\nAssistant: {last_ai}\n\n"
                    f"Return the updated summary only."
                )),
            ]
            updated = llm.invoke(prompt)
            new_summary = updated.content.strip() if isinstance(updated, AIMessage) else str(updated)
            return {"summary": new_summary}
        except Exception:
            return {"summary": state.summary}
    
    # Add edges
    workflow.add_edge(START, "agent")

    def route_from_agent(state: ChatState):
        last = state.messages[-1] if state.messages else None
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "summarize"

    workflow.add_conditional_edges("agent", route_from_agent, {"tools": "tools", "summarize": "summarize"})
    workflow.add_edge("tools", "agent")

    workflow.add_node("summarize", summarize_node)
    workflow.add_edge("summarize", END)
    
    # Compile with memory
    checkpointer = get_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


def create_unified_chat_app():
    """Create unified chat application that routes based on user type"""
    # All tools available for routing
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    
    def summarize_node(state: ChatState):
        try:
            prev = state.summary or ""
            last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
            last_ai = next((m.content for m in reversed(state.messages) if isinstance(m, AIMessage)), "")
            prompt = [
                SystemMessage(content=(
                    "You are a conversation summarizer. Update the running summary with the latest exchange."
                )),
                HumanMessage(content=(
                    f"Previous summary:\n{prev}\n\n"
                    f"Latest exchange:\nUser: {last_human}\nAssistant: {last_ai}\n\n"
                    f"Return the updated summary only."
                )),
            ]
            updated = llm.invoke(prompt)
            new_summary = updated.content.strip() if isinstance(updated, AIMessage) else str(updated)
            return {"summary": new_summary}
        except Exception:
            return {"summary": state.summary}
    
    def finalize_node(state: ChatState):
        for msg in reversed(state.messages):
            if isinstance(msg, ToolMessage):
                return {"messages": [AIMessage(content=msg.content)]}
        return {"messages": [AIMessage(content="Done.")]}
    workflow.add_node("finalize", finalize_node)
    
    # Add edges
    workflow.add_edge(START, "router")

    def route_from_router(state: ChatState):
        last = state.messages[-1] if state.messages else None
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "summarize"

    workflow.add_conditional_edges("router", route_from_router, {"tools": "tools", "summarize": "summarize"})
    workflow.add_edge("tools", "router")

    workflow.add_node("summarize", summarize_node)
    workflow.add_edge("summarize", END)
    
    # Compile with memory
    checkpointer = get_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


# ========================
# Lightweight Memory Helpers
# ========================
NAME_PATTERNS = [
    r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z\-'’]+)\b",
    r"\bi\s*am\s+([A-Za-z][A-Za-z\-'’]+)\b",
    r"\bi['’]?m\s+([A-Za-z][A-Za-z\-'’]+)\b",
    r"\bim\s+([A-Za-z][A-Za-z\-'’]+)\b",
    r"\bm\s+([A-Za-z][A-Za-z\-'’]+)\b",
    r"\b([A-Za-z][A-Za-z\-'’]+)\s+is\s+my\s+name\b",
    r"\bcall\s+me\s+([A-Za-z][A-Za-z\-'’]+)\b",
]

NAME_STOP_WORDS = {"what", "who", "where", "why", "how", "when"}


def _extract_user_name(text: str) -> Optional[str]:
    t = text.strip()
    for pat in NAME_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            return name[:1].upper() + name[1:]
    return None


def _get_known_name(thread_id: str) -> Optional[str]:
    try:
        items = store.list_memories(thread_id, limit=50)
        for it in items:
            tags = it.get("tags", []) or []
            if "name" in tags and "user_profile" in tags:
                content = it.get("content", "")
                if ":" in content:
                    key, _, val = content.partition(":")
                    if key.strip().lower().startswith("user_name"):
                        return val.strip()
                nm = _extract_user_name(content)
                if nm:
                    return nm
        return None
    except Exception:
        return None


def _maybe_save_user_name(thread_id: str, text: str) -> Optional[str]:
    name = _extract_user_name(text)
    if not name:
        return None
    if name.lower() in NAME_STOP_WORDS:
        return _get_known_name(thread_id)
    known = _get_known_name(thread_id)
    if known and known.lower() == name.lower():
        return known
    try:
        store.add_memory(
            thread_id=thread_id,
            content=f"user_name:{name}",
            tags=["user_profile", "name"],
            importance=3,
            source="agent",
        )
    except Exception:
        pass
    return name


def _build_memory_system_message(thread_id: str) -> Optional[str]:
    name = _get_known_name(thread_id)
    if name:
        return (
            "Known user profile:\n"
            f"- Name: {name}\n\n"
            "Use profile facts when the user asks about them or when confirming details. Avoid default greetings that repeat the user's name."
        )
    return None


# Capture simple durable preferences from natural phrases and store them
PREF_PATTERNS = [
    (r"\bremember\s+that\s+(.+)$", lambda m: ("note", m.group(1).strip())),
    (r"\bi\s+(?:really\s+)?like\s+([A-Za-z][\w\s\-]+)\b", lambda m: ("preference", m.group(1).strip())),
    (r"\bi\s+(?:do\s+not|don't|dont)\s+like\s+([A-Za-z][\w\s\-]+)\b", lambda m: ("dislike", m.group(1).strip())),
    (r"\bi['’]?m\s+(vegan|vegetarian|gluten[-\s]?free)\b", lambda m: ("dietary", m.group(1).replace(' ', '_'))),
    (r"\bi\s+am\s+(vegan|vegetarian|gluten[-\s]?free)\b", lambda m: ("dietary", m.group(1).replace(' ', '_'))),
    (r"\ballergic\s+to\s+([A-Za-z][\w\s\-]+)\b", lambda m: ("allergy", m.group(1).strip())),
]


def _maybe_save_preference(thread_id: str, text: str) -> Optional[str]:
    t = text.strip()
    for pat, fn in PREF_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            key, val = fn(m)
            content = f"{key}:{val}"
            try:
                store.add_memory(
                    thread_id=thread_id,
                    content=content,
                    tags=["user_profile", key],
                    importance=3,
                    source="agent",
                )
                return content
            except Exception:
                return None
    return None


# ========================
# Chat Interface Functions
# ========================
def run_internal_chat(message: str, thread_id: Optional[str] = None, **kwargs):
    """Run internal staff chat"""
    app = create_internal_chat_app()
    thread_id = ensure_thread_id(thread_id or "internal_staff_session")

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 5}

    # Retrieve the previously summarised context for this thread (if any)
    summary: Optional[str] = None
    history: List[Any] = []
    try:
        prior_state = app.get_state(config)
        if prior_state and getattr(prior_state, "values", None):
            summary = prior_state.values.get("summary")  # type: ignore[attr-defined]
            stored_messages = prior_state.values.get("messages")  # type: ignore[attr-defined]
            if stored_messages:
                history = list(stored_messages)[-20:]
    except Exception:
        summary = None

    # Capture any lightweight memories from the latest user message
    _maybe_save_user_name(thread_id, message)
    _maybe_save_preference(thread_id, message)

    memory_note = _build_memory_system_message(thread_id)

    windowed_messages: List[Any] = []
    if history:
        windowed_messages.extend(history)
    windowed_messages.append(HumanMessage(content=message))

    state = ChatState(
        messages=windowed_messages,
        user_type="internal",
        summary=summary,
        memory=memory_note,
    )

    try:
        result = app.invoke(state, config)
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Error in internal chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"


def run_external_chat(message: str, thread_id: Optional[str] = None, **kwargs):
    """Run external customer chat"""
    app = create_external_chat_app()
    thread_id = ensure_thread_id(thread_id or "customer_session")

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 5}

    summary: Optional[str] = None
    history: List[Any] = []
    try:
        prior_state = app.get_state(config)
        if prior_state and getattr(prior_state, "values", None):
            summary = prior_state.values.get("summary")  # type: ignore[attr-defined]
            stored_messages = prior_state.values.get("messages")  # type: ignore[attr-defined]
            if stored_messages:
                history = list(stored_messages)[-20:]
    except Exception:
        summary = None

    _maybe_save_user_name(thread_id, message)
    _maybe_save_preference(thread_id, message)
    memory_note = _build_memory_system_message(thread_id)

    windowed_messages: List[Any] = []
    if history:
        windowed_messages.extend(history)
    windowed_messages.append(HumanMessage(content=message))

    state = ChatState(
        messages=windowed_messages,
        user_type="external",
        summary=summary,
        memory=memory_note,
    )

    try:
        result = app.invoke(state, config)
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Error in external chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"


def run_unified_chat(message: str, user_type: str = "internal", thread_id: Optional[str] = None, **kwargs):
    """Run unified chat with user type routing"""
    app = create_unified_chat_app()
    resolved_thread = thread_id or ("internal_staff_session" if user_type == "internal" else "customer_session")
    resolved_thread = ensure_thread_id(resolved_thread)

    config = {"configurable": {"thread_id": resolved_thread}, "recursion_limit": 5}

    summary: Optional[str] = None
    history: List[Any] = []
    try:
        prior_state = app.get_state(config)
        if prior_state and getattr(prior_state, "values", None):
            summary = prior_state.values.get("summary")  # type: ignore[attr-defined]
            stored_messages = prior_state.values.get("messages")  # type: ignore[attr-defined]
            if stored_messages:
                history = list(stored_messages)[-20:]
    except Exception:
        summary = None

    _maybe_save_user_name(resolved_thread, message)
    _maybe_save_preference(resolved_thread, message)
    memory_note = _build_memory_system_message(resolved_thread)

    windowed_messages: List[Any] = []
    if history:
        windowed_messages.extend(history)
    windowed_messages.append(HumanMessage(content=message))

    state = ChatState(
        messages=windowed_messages,
        user_type=user_type,
        summary=summary,
        memory=memory_note,
    )

    try:
        result = app.invoke(state, config)
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Error in unified chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"
