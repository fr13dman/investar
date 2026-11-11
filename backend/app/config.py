from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'investar.db'}"
    finnhub_api_key: str = ""
    patentsview_api_key: str = ""
    # SEC fair-access policy requires a descriptive User-Agent with contact details.
    sec_user_agent: str = "Investar research app admin@example.com"
    # Wikipedia/Wikidata also reject anonymous agents; defaults to Investar/0.1 (<sec_user_agent>).
    http_user_agent: str = ""

    sentiment_model: str = "auto"  # auto | finbert | vader
    enable_scheduler: bool = True
    intraday_interval_minutes: int = 15

    news_ttl_minutes: int = 60
    filings_ttl_days: int = 7
    patents_ttl_days: int = 7

    cors_origins: list[str] = ["http://localhost:3010", "http://127.0.0.1:3010"]

    @field_validator("database_url")
    @classmethod
    def _resolve_sqlite_path(cls, v: str) -> str:
        prefix = "sqlite:///"
        if v.startswith(prefix) and not v.startswith(prefix + "/") and ":memory:" not in v:
            return prefix + str(BACKEND_DIR / v.removeprefix(prefix))
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
