from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai_prompts.prompts import INTERNAL_AGENT_CONFIG, EXTERNAL_AGENT_CONFIG
from src.utils.llm import llm


@dataclass
class Plan:
    tool: str
    args: Dict[str, Any]


def _safe_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        # try to extract a JSON object
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


def _allowed_tools(user_type: str) -> List[str]:
    if user_type == "external":
        return list(EXTERNAL_AGENT_CONFIG["tools_available"])  # type: ignore[index]
    return list(INTERNAL_AGENT_CONFIG["tools_available"])  # type: ignore[index]


def classify_intent(message: str, user_type: str = "internal") -> str:
    """Return 'db_query' or 'conversational' using the LLM (no heuristics)."""
    sys_text = (
        "Classify the user message. If answering requires querying any restaurant database "
        "(employees, recipes, storage/inventory, daily menu), return db_query. "
        "If it can be answered conversationally without data lookup, return conversational.\n"
        "Return only one token: db_query or conversational."
    )
    msgs = [SystemMessage(content=sys_text), HumanMessage(content=message)]
    ai = llm.invoke(msgs)
    out = ai.content.strip().lower() if isinstance(ai, AIMessage) else str(ai).strip().lower()
    return "db_query" if out.startswith("db_query") or out == "db_query" else "conversational"


def plan_query(message: str, user_type: str = "internal") -> Optional[Plan]:
    """Derive a concrete tool + args plan using the LLM, restricted to allowed tools."""
    tools = _allowed_tools(user_type)
    schema_hint = (
        "Return strict JSON with keys: tool (one of: " + ", ".join(tools) + ") and args (object).\n"
        "Do NOT include any 'limit' argument; fetch full results unless the user explicitly requests a sample or page.\n"
        "Examples:\n"
        "{\"tool\": \"query_daily_menu\", \"args\": {\"menu_date\": \"2025-01-03\", \"category_filter\": \"dessert\", \"output_format\": \"json\"}}\n"
        "{\"tool\": \"query_employees\", \"args\": {\"department_filter\": \"kitchen\", \"output_format\": \"json\"}}\n"
        "If information is missing (e.g., date/location), keep args minimal and avoid restrictive filters."
    )
    sys_text = (
        "You are a restaurant CRM query planner. Map the user request to exactly one database tool and arguments.\n"
        + schema_hint
    )
    msgs = [SystemMessage(content=sys_text), HumanMessage(content=message)]
    ai = llm.invoke(msgs)
    data = _safe_json(ai.content if isinstance(ai, AIMessage) else str(ai))
    if not data:
        return None
    tool = data.get("tool")
    args = data.get("args") or {}
    if tool not in tools:
        return None
    if not isinstance(args, dict):
        return None
    # Default to JSON output for structured tool results
    args.setdefault("output_format", "json")
    return Plan(tool=tool, args=args)


# Async variants
async def aclassify_intent(message: str, user_type: str = "internal") -> str:
    """Async LLM-only intent classification."""
    sys_text = (
        "Classify the user message. If answering requires querying any restaurant database "
        "(employees, recipes, storage/inventory, daily menu), return db_query. "
        "If it can be answered conversationally without data lookup, return conversational.\n"
        "Return only one token: db_query or conversational."
    )
    msgs = [SystemMessage(content=sys_text), HumanMessage(content=message)]
    ai = await llm.ainvoke(msgs)
    out = ai.content.strip().lower() if isinstance(ai, AIMessage) else str(ai).strip().lower()
    return "db_query" if out.startswith("db_query") or out == "db_query" else "conversational"


async def aplan_query(message: str, user_type: str = "internal") -> Optional[Plan]:
    tools = _allowed_tools(user_type)
    schema_hint = (
        "Return strict JSON with keys: tool (one of: " + ", ".join(tools) + ") and args (object).\n"
        "Do NOT include any 'limit' argument; fetch full results unless the user explicitly requests a sample or page.\n"
        "If information is missing (e.g., date/location), keep args minimal and avoid restrictive filters."
    )
    sys_text = (
        "You are a restaurant CRM query planner. Map the user request to exactly one database tool and arguments.\n"
        + schema_hint
    )
    msgs = [SystemMessage(content=sys_text), HumanMessage(content=message)]
    ai = await llm.ainvoke(msgs)
    data = _safe_json(ai.content if isinstance(ai, AIMessage) else str(ai))
    if not data:
        return None
    tool = data.get("tool")
    args = data.get("args") or {}
    if tool not in tools:
        return None
    if not isinstance(args, dict):
        return None
    args.setdefault("output_format", "json")
    return Plan(tool=tool, args=args)
