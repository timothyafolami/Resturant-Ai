from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from src.configs.config import get_settings


_settings = get_settings()

llm = ChatOpenAI(
    api_key=_settings.openai_api_key,
    model="gpt-4.1-mini",
    temperature=0.0,
    max_retries=2,
)


# llm = ChatGroq(
#     api_key=_settings.groq_api_key,
#     model=_settings.model_name,
#     temperature=0.0,
#     max_retries=2,
# )

__all__ = ["llm"]
