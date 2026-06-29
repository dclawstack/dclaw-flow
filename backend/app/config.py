"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://flow:flow@localhost:5432/dclaw_flow"
    app_env: str = "development"
    log_level: str = "info"
    webhook_secret: str = "change-me-in-production"
    admin_token: str = "change-me-in-production"
    execution_retention_days: int = 90
    # Slack / generic webhook for failure alerts (empty = alerting disabled).
    alert_webhook_url: str = ""
    cors_origins: str = "http://localhost:3000"

    # --- Rate limiting (slowapi, in-memory; FOSS, single-instance) ---
    rate_limit_enabled: bool = True
    webhook_rate_limit: str = "60/minute"
    copilot_rate_limit: str = "20/minute"

    # --- AI Flow Copilot (P0.1) ---
    # Provider order for natural-language workflow generation. "auto" tries the
    # local Ollama model first, then the OpenRouter cloud model, then falls back
    # to a deterministic generator so the copilot always works offline / in CI.
    copilot_provider: str = "auto"  # auto | ollama | openrouter | heuristic
    copilot_timeout_seconds: float = 8.0
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openrouter_api_key: str = ""
    openrouter_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "moonshotai/kimi-k2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
