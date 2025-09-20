#!/usr/bin/env python3
import os
import sys
import uuid
from dotenv import load_dotenv
import streamlit as st
from _theme import apply_theme

# Ensure src is importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.agent.chat_agents import run_internal_chat

load_dotenv()

st.set_page_config(page_title="Internal Staff Chat", page_icon="🏪", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Quick Start")
    st.caption("Sample prompts")
    examples = [
        "Show me all employees in the kitchen department",
        "What recipes use chicken breast?",
        "Check low stock alerts",
        "What's on today's menu at Downtown?",
        "Get performance stats for all employees",
        "Show me the recipe details for Spaghetti Carbonara",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state._internal_prefill = ex
            st.rerun()

    st.divider()
    st.subheader("Settings")
    temp = st.slider("Model temperature", 0.0, 1.0, value=float(os.getenv("AI_TEMPERATURE", 0.1)), step=0.05, key="internal_temp")
    show_suggestions = st.checkbox("Show follow‑up suggestions", value=str(os.getenv("AI_SUGGESTIONS", "on")).lower() not in {"0","off","no","false"}, key="internal_suggestions")
    # Apply settings via environment for backend consumption
    os.environ["AI_TEMPERATURE"] = str(temp)
    os.environ["AI_SUGGESTIONS"] = "1" if show_suggestions else "0"
    # Show effective provider/model for quick debugging
    model_env = (os.getenv("MODEL_NAME") or "llama3-70b-8192").strip()
    provider = "OpenAI" if model_env.lower().startswith("gpt-") and os.getenv("OPENAI_API_KEY") else "Groq"
    alias = {
        "llama3-groq-70b-8192-tool-use-preview": "llama3-70b-8192",
        "llama3-groq-8b-8192-tool-use-preview": "llama3-8b-8192",
    }
    effective_model = alias.get(model_env.lower(), model_env)
    if provider == "Groq" and effective_model.lower().startswith("gpt-"):
        effective_model = "llama3-70b-8192"
    st.caption(f"Provider: {provider} | Model: {effective_model}")
    if st.button("New conversation", type="primary", use_container_width=True):
        st.session_state.internal_messages = []
        st.session_state.internal_thread_id = f"internal_staff_session:streamlit:{uuid.uuid4().hex}"
        st.rerun()

    st.caption("Session")
    st.code(st.session_state.get("internal_thread_id", ""), language="text")

# Title
apply_theme("Dark")
st.markdown("## 🏪 Internal Staff Chat")
st.caption("Operations assistant for employees, recipes, inventory, and daily menu.")

# Session state
if "internal_thread_id" not in st.session_state:
    st.session_state.internal_thread_id = f"internal_staff_session:streamlit:{uuid.uuid4().hex}"
if "internal_messages" not in st.session_state:
    st.session_state.internal_messages = []

# Render chat history
for msg in st.session_state.internal_messages:
    with st.chat_message("user" if msg[0] == "user" else "assistant"):
        st.markdown(msg[1])

# Input
prefill = st.session_state.pop("_internal_prefill", None)
prompt = st.chat_input("Ask about employees, recipes, inventory, or menu...", key="internal_chat_input")
if prefill and not prompt:
    prompt = prefill

if prompt:
    st.session_state.internal_messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Working on it..."):
            try:
                reply = run_internal_chat(prompt, st.session_state.internal_thread_id)
            except Exception as e:
                reply = f"❌ Sorry, something went wrong: {e}"
        st.markdown(reply)
    st.session_state.internal_messages.append(("assistant", reply))
