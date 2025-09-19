import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    openai_api_key: str
    model_name: str = "llama3-70b-8192"
    database_url: str = "postgresql://user:password@localhost:5432/restaurant_crm"


def get_settings() -> Settings:
    key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL_NAME") or "llama3-70b-8192"
    db_url = os.getenv("DATABASE_URL") or "postgresql://user:password@localhost:5432/restaurant_crm"

    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Create a .env file with GROQ_API_KEY=... or export the variable."
        )

    return Settings(groq_api_key=key, openai_api_key=openai_key, model_name=model, database_url=db_url)
