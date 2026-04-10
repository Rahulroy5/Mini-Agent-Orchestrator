from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "mini-agent-orchestrator"
    app_version: str = "1.0.0"

    model: str = "qwen3.5:2b"
    ollama_url: str = "http://localhost:11434"

    ollama_timeout_seconds: float = 20.0
    ollama_retries: int = 2
    ollama_retry_backoff_seconds: float = 0.5
    ollama_startup_check: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
