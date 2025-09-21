import re
import os

from typing import List, Any, Optional, Annotated

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
try:
    from langgraph.prebuilt.tool_node import ToolNode  # LangGraph >=0.4.8 module form
except ModuleNotFoundError:  # pragma: no cover - older LangGraph builds
    try:
        from langgraph.prebuilt import ToolNode  # type: ignore
    except (ModuleNotFoundError, ImportError):
        ToolNode = None  # type: ignore[assignment]
import asyncio
from pydantic import BaseModel

from src.utils.app_logging import setup_logger, get_context_logger
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
    intent: Optional[str] = None  # conversational | db_query
    plan: Optional[dict] = None   # {tool, args}
    tool_result: Optional[str] = None
    clarify_question: Optional[str] = None


# ========================
# Agent Nodes
# ========================
async def internal_agent_node(state: ChatState):
    """Internal restaurant staff agent"""
    ctx_logger = get_context_logger("internal")
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

    # Create response LLM without tool binding; tool execution is handled separately
    internal_llm = llm

    # Build message stack: system prompt + optional summary + current turn messages
    messages = state.messages
    built: List[Any] = [system_message]
    if memory_message is not None:
        built.append(memory_message)
    if summary_message is not None:
        built.append(summary_message)
    built.extend(messages)
    if state.tool_result:
        built.append(SystemMessage(content=f"Tool result:\n{state.tool_result}"))
    ctx_logger.debug(
        f"Responder prompt built. summary_present={bool(state.summary)} "
        f"memory_present={bool(state.memory)} tool_result_present={bool(state.tool_result)}"
    )
    # Control follow-up suggestions via env toggle
    if str(os.getenv("AI_SUGGESTIONS", "on")).lower() in {"0", "off", "no", "false"}:
        built.append(SystemMessage(content=(
            "Follow-up suggestions are disabled for this session. Provide a concise direct answer only;"
            " do not include sections like 'Next steps' or 'You might also like'."
        )))
    response = await internal_llm.ainvoke(built)
    ctx_logger.debug("Responder produced content length=%d", len(response.content) if hasattr(response, 'content') and isinstance(response.content, str) else -1)
    return {"messages": [response]}


async def external_agent_node(state: ChatState):
    """External customer agent"""
    ctx_logger = get_context_logger("external")
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

    # Create response LLM without tool binding; tool execution is handled separately
    external_llm = llm

    # Build message stack: system prompt + optional summary + current turn messages
    messages = state.messages
    built: List[Any] = [system_message]
    if memory_message is not None:
        built.append(memory_message)
    if summary_message is not None:
        built.append(summary_message)
    built.extend(messages)
    if state.tool_result:
        built.append(SystemMessage(content=f"Tool result:\n{state.tool_result}"))
    ctx_logger.debug(
        f"Responder prompt built. summary_present={bool(state.summary)} "
        f"memory_present={bool(state.memory)} tool_result_present={bool(state.tool_result)}"
    )
    if str(os.getenv("AI_SUGGESTIONS", "on")).lower() in {"0", "off", "no", "false"}:
        built.append(SystemMessage(content=(
            "Follow-up suggestions are disabled for this session. Provide a concise direct answer only;"
            " do not include sections like 'Next steps' or 'You might also like'."
        )))
    response = await external_llm.ainvoke(built)
    ctx_logger.debug("Responder produced content length=%d", len(response.content) if hasattr(response, 'content') and isinstance(response.content, str) else -1)
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
    
    # Add nodes: intent -> (planner -> exec)? -> agent -> summarize
    internal_tools = [tool for tool in ALL_TOOLS if tool.name in INTERNAL_AGENT_CONFIG["tools_available"]]

    async def intent_node(state: ChatState):
        last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
        from src.agent.query_planner import aclassify_intent
        it = await aclassify_intent(last_human, user_type="internal")
        get_context_logger("internal").info(f"Intent classified: {it}")
        return {"intent": it}

    async def planner_node(state: ChatState):
        last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
        from src.agent.query_planner import aplan_query
        pl = await aplan_query(last_human, user_type="internal")
        # Heuristic: if planner picked recipe details but omitted identifiers,
        # try to extract a dish name from the latest user message.
        try:
            if pl and getattr(pl, "tool", None) == "get_recipe_details":
                args = getattr(pl, "args", {}) or {}
                has_id = args.get("recipe_id") and str(args.get("recipe_id")).strip()
                has_name = args.get("dish_name") and str(args.get("dish_name")).strip()
                if not (has_id or has_name):
                    import re
                    m = re.search(r"(?:for|about)\s+([A-Za-z0-9][^\n\r]+)$", last_human, flags=re.IGNORECASE)
                    if m:
                        guess = m.group(1).strip().strip(".?!'\" ")
                        if guess:
                            args["dish_name"] = guess
                            pl.args = args
        except Exception:
            pass
        get_context_logger("internal").info(
            f"Plan: {{'tool': {getattr(pl, 'tool', None)}, 'args': {getattr(pl, 'args', None)}}}"
        )
        return {"plan": {"tool": pl.tool, "args": pl.args}} if pl else {"plan": None}

    def _clarify_for_plan(plan: Optional[dict]) -> Optional[str]:
        if not plan:
            return None
        tool = plan.get("tool") if isinstance(plan, dict) else None
        args = plan.get("args") if isinstance(plan, dict) else None
        if not tool:
            return None
        args = args or {}
        # Required args by tool
        if tool == "get_menu_item_details":
            if not (args.get("dish_name") and str(args.get("dish_name")).strip()):
                return "Which dish would you like details for? You can optionally specify a date (YYYY-MM-DD)."
        if tool == "get_recipe_details":
            # Accept either recipe_id or dish_name; don't force recipe_id
            has_id = args.get("recipe_id") and str(args.get("recipe_id")).strip()
            has_name = args.get("dish_name") and str(args.get("dish_name")).strip()
            if not (has_id or has_name):
                return "Which recipe would you like details for? You can specify the dish name."
        if tool == "query_daily_menu":
            # If no filters at all, ask to narrow to reduce result size
            if not any(args.get(k) for k in ["menu_date", "location", "category_filter", "price_range", "dietary_restrictions"]):
                return "Do you have a date or location in mind for the daily menu (e.g., today at Downtown, or desserts)?"
        return None

    def clarify_node(state: ChatState):
        q = _clarify_for_plan(state.plan)
        if not q:
            return {}
        get_context_logger("internal").info(f"Clarify question: {q}")
        return {"messages": [AIMessage(content=q)], "clarify_question": q}

    async def exec_node(state: ChatState):
        if not state.plan:
            return {"tool_result": None}
        tool_name = state.plan.get("tool")
        args = state.plan.get("args") or {}
        tool = next((t for t in internal_tools if t.name == tool_name), None)
        if not tool:
            return {"tool_result": f"Planner selected unknown tool: {tool_name}"}
        try:
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(args)
            else:
                # fallback to sync invocation
                result = tool.invoke(args)
        except Exception as e:
            result = f"Tool execution error: {str(e)}"
        get_context_logger("internal").info(f"Tool exec: {tool_name} args={args}")
        # Avoid gigantic log lines; cap at 4000 chars
        get_context_logger("internal").debug(f"Tool result (truncated): {str(result)[:4000]}")
        return {"tool_result": result}

    workflow.add_node("detect_intent", intent_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("exec", exec_node)
    workflow.add_node("agent", internal_agent_node)

    async def summarize_node(state: ChatState):
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
            updated = await llm.ainvoke(prompt)
            new_summary = updated.content.strip() if isinstance(updated, AIMessage) else str(updated)
            return {"summary": new_summary}
        except Exception:
            return {"summary": state.summary}
    
    # Add edges
    workflow.add_edge(START, "detect_intent")

    def route_from_intent(state: ChatState):
        return "planner" if state.intent == "db_query" else "agent"

    workflow.add_conditional_edges("detect_intent", route_from_intent, {"planner": "planner", "agent": "agent"})
    def route_from_planner(state: ChatState):
        return "clarify" if _clarify_for_plan(state.plan) else "exec"

    workflow.add_conditional_edges("planner", route_from_planner, {"clarify": "clarify", "exec": "exec"})
    workflow.add_edge("clarify", "summarize")
    workflow.add_edge("exec", "agent")
    # ensure agent still flows to summarize
    workflow.add_edge("agent", "summarize")

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

    # Add nodes: intent -> (planner -> exec)? -> agent -> summarize
    async def intent_node(state: ChatState):
        last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
        from src.agent.query_planner import aclassify_intent
        it = await aclassify_intent(last_human, user_type="external")
        get_context_logger("external").info(f"Intent classified: {it}")
        return {"intent": it}

    async def planner_node(state: ChatState):
        last_human = next((m.content for m in reversed(state.messages) if isinstance(m, HumanMessage)), "")
        from src.agent.query_planner import aplan_query
        pl = await aplan_query(last_human, user_type="external")
        get_context_logger("external").info(
            f"Plan: {{'tool': {getattr(pl, 'tool', None)}, 'args': {getattr(pl, 'args', None)}}}"
        )
        return {"plan": {"tool": pl.tool, "args": pl.args}} if pl else {"plan": None}

    def _clarify_for_plan(plan: Optional[dict]) -> Optional[str]:
        if not plan:
            return None
        tool = plan.get("tool") if isinstance(plan, dict) else None
        args = plan.get("args") if isinstance(plan, dict) else None
        if not tool:
            return None
        args = args or {}
        if tool == "get_menu_item_details":
            if not (args.get("dish_name") and str(args.get("dish_name")).strip()):
                return "Which dish would you like details for? You can optionally specify a date (YYYY-MM-DD)."
        if tool == "query_daily_menu":
            if not any(args.get(k) for k in ["menu_date", "location", "category_filter", "price_range", "dietary_restrictions"]):
                return "Do you have a specific location, category, or price range for today's menu?"
        return None

    def clarify_node(state: ChatState):
        q = _clarify_for_plan(state.plan)
        if not q:
            return {}
        get_context_logger("external").info(f"Clarify question: {q}")
        return {"messages": [AIMessage(content=q)], "clarify_question": q}

    async def exec_node(state: ChatState):
        if not state.plan:
            return {"tool_result": None}
        tool_name = state.plan.get("tool")
        args = state.plan.get("args") or {}
        tool = next((t for t in external_tools if t.name == tool_name), None)
        if not tool:
            return {"tool_result": f"Planner selected unknown tool: {tool_name}"}
        try:
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(args)
            else:
                result = tool.invoke(args)
        except Exception as e:
            result = f"Tool execution error: {str(e)}"
        get_context_logger("external").info(f"Tool exec: {tool_name} args={args}")
        get_context_logger("external").debug(f"Tool result (truncated): {str(result)[:4000]}")
        return {"tool_result": result}

    workflow.add_node("detect_intent", intent_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("exec", exec_node)
    workflow.add_node("agent", external_agent_node)
    
    async def summarize_node(state: ChatState):
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
            updated = await llm.ainvoke(prompt)
            new_summary = updated.content.strip() if isinstance(updated, AIMessage) else str(updated)
            return {"summary": new_summary}
        except Exception:
            return {"summary": state.summary}
    
    # Add edges
    workflow.add_edge(START, "detect_intent")

    def route_from_intent(state: ChatState):
        return "planner" if state.intent == "db_query" else "agent"

    workflow.add_conditional_edges("detect_intent", route_from_intent, {"planner": "planner", "agent": "agent"})
    def route_from_planner(state: ChatState):
        return "clarify" if _clarify_for_plan(state.plan) else "exec"

    workflow.add_conditional_edges("planner", route_from_planner, {"clarify": "clarify", "exec": "exec"})
    workflow.add_edge("clarify", "summarize")
    workflow.add_edge("exec", "agent")
    workflow.add_edge("agent", "summarize")

    workflow.add_node("summarize", summarize_node)
    workflow.add_edge("summarize", END)
    
    # Compile with memory
    checkpointer = get_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


def create_unified_chat_app():
    """Create unified chat application that routes based on user type"""
    if ToolNode is None:
        raise ImportError(
            "ToolNode is unavailable in this LangGraph build. "
            "Install `langgraph-prebuilt>=0.6.4` or pin `langgraph` to a version "
            "that includes `prebuilt.tool_node`, or avoid using the unified chat app."
        )

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
            # Use internal defaults for summarization
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


def _build_memory_system_message(thread_id: str, query_text: Optional[str] = None) -> Optional[str]:
    try:
        items = store.list_memories(thread_id, limit=50)
    except Exception:
        items = []

    name = _get_known_name(thread_id)

    # Collect compact profile facts
    prefs, dislikes, dietary, allergy, notes = [], [], [], [], []
    for it in items:
        tags = it.get("tags", []) or []
        content = (it.get("content") or "").strip()
        if not content:
            continue
        if "preference" in tags:
            prefs.append(content.split(":", 1)[-1])
        elif "dislike" in tags:
            dislikes.append(content.split(":", 1)[-1])
        elif "dietary" in tags:
            dietary.append(content.split(":", 1)[-1])
        elif "allergy" in tags:
            allergy.append(content.split(":", 1)[-1])
        elif "note" in tags:
            notes.append(content.split(":", 1)[-1])

    relevant = []
    if query_text:
        try:
            relevant = [m.get("content", "") for m in store.search(thread_id, query_text, limit=3)]
        except Exception:
            relevant = []

    lines: List[str] = []
    if name:
        lines.append(f"- Name: {name}")
    if dietary:
        lines.append(f"- Dietary: {', '.join(sorted(set(dietary)))}")
    if allergy:
        lines.append(f"- Allergies: {', '.join(sorted(set(allergy)))}")
    if prefs:
        lines.append(f"- Likes: {', '.join(sorted(set(prefs)))}")
    if dislikes:
        lines.append(f"- Dislikes: {', '.join(sorted(set(dislikes)))}")
    if notes:
        lines.append(f"- Notes: {', '.join(notes[:3])}")
    if relevant:
        lines.append("- Relevant memory: " + " | ".join(relevant))

    if not lines:
        return None

    header = "Known user profile:"
    tail = (
        "\n\nUse profile facts only when helpful to answer or personalize. "
        "Avoid repeating them gratuitously."
    )
    return header + "\n" + "\n".join(lines) + tail


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


def _maybe_save_assistant_insights(thread_id: str, text: str) -> list[str]:
    """Capture preferences or facts stated by the assistant about the user.

    This complements _maybe_save_preference (which analyzes user text). It looks
    for phrases like "you prefer ...", "you're vegan", or "allergic to ..." in
    the assistant response and persists them as durable memories.
    """
    patterns = [
        (r"you\s+(?:really\s+)?(?:like|love|prefer)\s+([A-Za-z][\w\s\-]+)\b", "preference"),
        (r"you\s+(?:do\s+not|don't|dont)\s+like\s+([A-Za-z][\w\s\-]+)\b", "dislike"),
        (r"you\s+are\s+(vegan|vegetarian|gluten[-\s]?free)\b", "dietary"),
        (r"allergic\s+to\s+([A-Za-z][\w\s\-]+)\b", "allergy"),
    ]
    t = text.strip()
    saved: list[str] = []
    for pat, key in patterns:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip().replace(" ", "_")
            try:
                store.add_memory(
                    thread_id=thread_id,
                    content=f"{key}:{val}",
                    tags=["user_profile", key],
                    importance=3,
                    source="assistant",
                )
                saved.append(f"{key}:{val}")
            except Exception:
                pass
    return saved


def _postprocess_turn_memory(thread_id: str, user_text: str, assistant_text: str) -> None:
    """Persist any useful memory derived from the user or assistant turn."""
    try:
        saved_user = _maybe_save_preference(thread_id, user_text)
        saved_assistant = _maybe_save_assistant_insights(thread_id, assistant_text)
        # Log saved memories to appropriate context file
        context = "internal" if (thread_id and str(thread_id).startswith("internal_staff_session")) else "external"
        ctx_logger = get_context_logger(context)
        if saved_user:
            ctx_logger.info(f"[thread={thread_id}] Memory saved (user): {saved_user}")
        if saved_assistant:
            for s in saved_assistant:
                ctx_logger.info(f"[thread={thread_id}] Memory saved (assistant): {s}")
    except Exception:
        pass


# ========================
# Chat Interface Functions
# ========================
async def run_internal_chat_async(message: str, thread_id: Optional[str] = None, **kwargs):
    """Run internal staff chat"""
    app = create_internal_chat_app()
    thread_id = ensure_thread_id(thread_id or "internal_staff_session")

    # Allow enough steps for detect -> planner -> exec -> agent -> summarize -> END
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}

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

    ctx_logger = get_context_logger("internal")
    ctx_logger.info(f"[thread={thread_id}] User: {message}")
    memory_note = _build_memory_system_message(thread_id, message)
    if memory_note:
        ctx_logger.debug(f"[thread={thread_id}] Memory inject: {memory_note}")

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
        result = await app.ainvoke(state, config)
        final_text = result["messages"][-1].content
        ctx_logger.info(
            f"[thread={thread_id}] Assistant: {(final_text[:4000] if isinstance(final_text, str) else str(final_text))}"
        )
        _postprocess_turn_memory(thread_id, message, final_text)
        return final_text
    except Exception as e:
        logger.error(f"Error in internal chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"


def run_internal_chat(message: str, thread_id: Optional[str] = None, **kwargs):
    return asyncio.run(run_internal_chat_async(message, thread_id, **kwargs))


def run_external_chat(message: str, thread_id: Optional[str] = None, **kwargs):
    """Run external customer chat"""
async def run_external_chat_async(message: str, thread_id: Optional[str] = None, **kwargs):
    app = create_external_chat_app()
    thread_id = ensure_thread_id(thread_id or "customer_session")

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}

    ctx_logger = get_context_logger("external")
    ctx_logger.info(f"[thread={thread_id}] User: {message}")
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
    memory_note = _build_memory_system_message(thread_id, message)
    if memory_note:
        ctx_logger.debug(f"[thread={thread_id}] Memory inject: {memory_note}")

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
        result = await app.ainvoke(state, config)
        final_text = result["messages"][-1].content
        ctx_logger.info(
            f"[thread={thread_id}] Assistant: {(final_text[:4000] if isinstance(final_text, str) else str(final_text))}"
        )
        _postprocess_turn_memory(thread_id, message, final_text)
        return final_text
    except Exception as e:
        logger.error(f"Error in external chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"


def run_external_chat(message: str, thread_id: Optional[str] = None, **kwargs):
    return asyncio.run(run_external_chat_async(message, thread_id, **kwargs))


async def run_unified_chat_async(message: str, user_type: str = "internal", thread_id: Optional[str] = None, **kwargs):
    """Run unified chat with user type routing"""
    app = create_unified_chat_app()
    resolved_thread = thread_id or ("internal_staff_session" if user_type == "internal" else "customer_session")
    resolved_thread = ensure_thread_id(resolved_thread)

    config = {"configurable": {"thread_id": resolved_thread}, "recursion_limit": 20}

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
    memory_note = _build_memory_system_message(resolved_thread, message)

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
        result = await app.ainvoke(state, config)
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Error in unified chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"


def run_unified_chat(message: str, user_type: str = "internal", thread_id: Optional[str] = None, **kwargs):
    return asyncio.run(run_unified_chat_async(message, user_type, thread_id, **kwargs))
