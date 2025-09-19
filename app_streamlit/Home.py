#!/usr/bin/env python3
import os
import sys
import uuid
import streamlit as st
from _theme import apply_theme
from dotenv import load_dotenv

# Ensure src is importable
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

load_dotenv()

st.set_page_config(
    page_title="Restaurant CRM Chat",
    page_icon="🍽️",
    layout="wide",
)

with st.sidebar:
    st.header("Settings")
    temp = st.slider("Model temperature", 0.0, 1.0, value=float(os.getenv("AI_TEMPERATURE", 0.2)), step=0.05, key="home_temp")
    show_suggestions = st.checkbox("Show follow‑up suggestions", value=str(os.getenv("AI_SUGGESTIONS", "on")).lower() not in {"0","off","no","false"}, key="home_suggestions")
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

apply_theme("Dark")

st.markdown(
    """
    <style>
    .hero {
        padding: 1.25rem 1.5rem; border-radius: 12px;
        background: linear-gradient(135deg, #0ea5e9 0%, #22c55e 100%);
        color: white;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
    }
    .hero h1 { margin: 0 0 0.25rem 0; }
    .note { color: #0f172a; opacity: 0.8; }
    .card { padding: 1rem; border-radius: 10px; border: 1px solid #e2e8f0; background: #ffffffaa; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>Restaurant CRM Chat</h1>
      <div>Your internal ops assistant and guest menu concierge</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
col1, col2 = st.columns(2)
with col1:
    st.markdown(
        """
        ### 🏪 Internal Staff Chat
        Streamline operations with quick access to employees, inventory, recipes, and daily menu tools.
        - Employee lookups, performance stats, schedules
        - Inventory levels and low‑stock alerts
        - Recipe cards, ingredients, timing and notes
        - Daily menu status, availability and pricing
        """
    )
    st.page_link("pages/1_Internal_Chat.py", label="Open Internal Chat", icon="🧑‍🍳")

with col2:
    st.markdown(
        """
        ### 🍽️ Customer Chat
        Friendly menu guidance for guests, with dietary filters and recommendations.
        - Today’s menu with pricing and prep time
        - Recommendations by preference and diet
        - Availability and specials
        """
    )
    st.page_link("pages/2_External_Chat.py", label="Open Customer Chat", icon="🧑‍💼")

st.write("")
with st.expander("Tips"):
    st.markdown(
        """
        - Use the sidebar on each page for sample prompts and quick actions.
        - Click "New conversation" to start a fresh thread with a unique session ID.
        - All internal logs are written to files under `logs/`; the app view stays clean.
        """
    )
