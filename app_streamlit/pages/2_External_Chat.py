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

from src.agent.chat_agents import run_external_chat

load_dotenv()

st.set_page_config(page_title="Customer Chat", page_icon="🍽️", layout="wide")

# Sidebar
with st.sidebar:
    st.header("Try asking")
    examples = [
        "What's on the menu today?",
        "Do you have vegetarian options?",
        "Tell me about your pasta dishes",
        "Show desserts under $15",
        "What are your chef's recommendations?",
        "Any gluten‑free mains?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state._external_prefill = ex
            st.rerun()

    st.divider()
    st.subheader("Settings")
    temp = st.slider("Model temperature", 0.0, 1.0, value=float(os.getenv("AI_TEMPERATURE", 0.3)), step=0.05, key="external_temp")
    show_suggestions = st.checkbox("Show follow‑up suggestions", value=str(os.getenv("AI_SUGGESTIONS", "on")).lower() not in {"0","off","no","false"}, key="external_suggestions")
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
        st.session_state.external_messages = []
        st.session_state.external_thread_id = f"customer_session:streamlit:{uuid.uuid4().hex}"
        st.rerun()

    st.caption("Session")
    st.code(st.session_state.get("external_thread_id", ""), language="text")

# Title
apply_theme("Dark")
st.markdown("## 🍽️ Customer Chat")
st.caption("Friendly dining assistant to explore today’s menu and options.")

# Session state
if "external_thread_id" not in st.session_state:
    st.session_state.external_thread_id = f"customer_session:streamlit:{uuid.uuid4().hex}"
if "external_messages" not in st.session_state:
    st.session_state.external_messages = []

# Render chat history
for msg in st.session_state.external_messages:
    with st.chat_message("user" if msg[0] == "user" else "assistant"):
        st.markdown(msg[1])

# Input
prefill = st.session_state.pop("_external_prefill", None)
prompt = st.chat_input("Ask about today’s menu, prices, or recommendations...", key="external_chat_input")
if prefill and not prompt:
    prompt = prefill

if prompt:
    st.session_state.external_messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Let me check the menu…"):
            try:
                reply = run_external_chat(prompt, st.session_state.external_thread_id)
            except Exception as e:
                reply = f"❌ Sorry, something went wrong: {e}"
        st.markdown(reply)
    st.session_state.external_messages.append(("assistant", reply))
