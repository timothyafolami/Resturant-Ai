import streamlit as st


def apply_theme(theme: str = "Auto") -> None:
    """Inject lightweight CSS for light/dark accent theming.

    Theme options: Auto, Light, Dark.
    """
    dark = theme == "Dark"
    light = theme == "Light"
    # If Auto, leave as Streamlit default but still style chat bubbles.
    bg = "#0b1220" if dark else "#ffffff"
    fg = "#e2e8f0" if dark else "#0f172a"
    bubble_user = "#155e75" if dark else "#e0f2fe"
    bubble_ai = "#1e293b" if dark else "#f1f5f9"
    border = "#334155" if dark else "#e2e8f0"
    accent = "#22c55e" if dark else "#0ea5e9"

    st.markdown(
        f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{
            background: {bg} !important;
            color: {fg} !important;
        }}
        .stChatMessage.user {{
            background: {bubble_user};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 10px 12px;
        }}
        .stChatMessage.assistant {{
            background: {bubble_ai};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 10px 12px;
        }}
        .stButton > button[kind="primary"] {{
            background: {accent};
            color: white;
            border: none;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

