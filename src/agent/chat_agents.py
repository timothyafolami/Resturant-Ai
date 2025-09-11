import json
from typing import List, Dict, Any, Optional, Annotated

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel

from src.logging_config import setup_logger
from src.llm import llm
from src.tools import ALL_TOOLS, DATABASE_TOOLS, AGENT_MEMORY_TOOLS
from src.memory import get_checkpointer, ensure_thread_id
from src.prompts import INTERNAL_AGENT_CONFIG, EXTERNAL_AGENT_CONFIG


logger = setup_logger()


# ========================
# Agent State
# ========================
class ChatState(BaseModel):
    """State for chat applications"""
    messages: Annotated[List[Any], add_messages]
    user_type: str = "internal"  # "internal" or "external"


# ========================
# Agent Nodes
# ========================
def internal_agent_node(state: ChatState):
    """Internal restaurant staff agent"""
    system_message = SystemMessage(content=INTERNAL_AGENT_CONFIG["system_prompt"])
    
    # Create LLM with tools for internal staff
    internal_llm = llm.bind_tools(ALL_TOOLS)
    
    # Add system message if not present
    messages = state.messages
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_message] + messages
    
    response = internal_llm.invoke(messages)
    return {"messages": [response]}


def external_agent_node(state: ChatState):
    """External customer agent"""
    system_message = SystemMessage(content=EXTERNAL_AGENT_CONFIG["system_prompt"])
    
    # Create LLM with limited tools for customers
    external_tools = [tool for tool in ALL_TOOLS if tool.name in EXTERNAL_AGENT_CONFIG["tools_available"]]
    external_llm = llm.bind_tools(external_tools)
    
    # Add system message if not present
    messages = state.messages
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_message] + messages
    
    response = external_llm.invoke(messages)
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
    
    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")
    
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
    
    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")
    
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
    
    # Add edges
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges("router", tools_condition)
    workflow.add_edge("tools", "router")
    
    # Compile with memory
    checkpointer = get_checkpointer()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


# ========================
# Chat Interface Functions
# ========================
def run_internal_chat(message: str, thread_id: Optional[str] = None, **kwargs):
    """Run internal staff chat"""
    app = create_internal_chat_app()
    thread_id = ensure_thread_id(thread_id)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    state = ChatState(
        messages=[HumanMessage(content=message)],
        user_type="internal"
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
    thread_id = ensure_thread_id(thread_id)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    state = ChatState(
        messages=[HumanMessage(content=message)],
        user_type="external"
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
    thread_id = ensure_thread_id(thread_id)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    state = ChatState(
        messages=[HumanMessage(content=message)],
        user_type=user_type
    )
    
    try:
        result = app.invoke(state, config)
        return result["messages"][-1].content
    except Exception as e:
        logger.error(f"Error in unified chat: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}"

