from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "HR_Assistant"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM
    openai_api_key: str = ""
    cohere_api_key: str = ""
    cohere_rerank_model: str = "rerank-v4.0-pro"
    cohere_rerank_candidate_limit: int = Field(default=40, ge=1, le=1000)
    cohere_rerank_max_tokens_per_doc: int = Field(default=2048, ge=128, le=4096)
    google_api_key: str = ""
    google_api_keys: str = ""
    model_name: str = Field(
        default="gemini-3.1-flash-lite",
        validation_alias=AliasChoices("MODEL_NAME", "DEFAULT_MODEL"),
    )
    embedding_model_name: str = "gemini-embedding-2"
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    online_llm_tests: bool = True

    # Guardrails
    guardrails_enabled: bool = True
    guardrails_mode: Literal["off", "warn", "block"] = "block"
    guardrails_fail_closed: bool = True
    safeguard_provider: Literal["openai", "groq"] = "groq"
    groq_api_key: str = ""
    groq_api_keys: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_safeguard_model: str = "openai/gpt-oss-safeguard-20b"
    openai_safeguard_enabled: bool = True
    openai_moderation_model: str = "omni-moderation-latest"
    openai_safeguard_model: str = "gpt-5-mini"
    topic_classifier_enabled: bool = True
    topic_classifier_provider: Literal["gemma", "rules"] = "gemma"
    topic_classifier_model: str = "gemma-4-12b-it"
    topic_classifier_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    output_guardrail_enabled: bool = True
    tool_guardrail_enabled: bool = True
    guardrail_log_decisions: bool = True
    guardrail_log_raw_text: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    # Security / Auth
    jwt_secret_key: str = Field(
        default="dev-only-change-me",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)
    jwt_secret: str = "dev-only-change-me"

    # Chat rate limit
    chat_rate_limit_count: int = Field(default=10, ge=1, le=1000)
    chat_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env != "production":
            return self

        if self.jwt_secret_key in {"", "dev-only-change-me", "change-me"} or len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be set to a strong value in production.")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must be an explicit allowlist in production.")
        if not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY must be configured in production.")
        if not (self.google_api_key or self.google_api_keys):
            raise ValueError("At least one Gemini API key must be configured in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

