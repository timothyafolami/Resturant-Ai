from langchain_groq import ChatGroq
from .config import get_settings


_settings = get_settings()

llm = ChatGroq(
    api_key=_settings.groq_api_key,
    model=_settings.model_name,
    temperature=0.0,
    max_retries=2,
)

__all__ = ["llm"]

