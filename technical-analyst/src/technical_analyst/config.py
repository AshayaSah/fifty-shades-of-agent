from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config, loaded from environment variables / .env."""

    twelve_data_api_key: str | None = None
    neon_database_url: str | None = None
    cache_ttl_seconds: int = 300
    log_level: str = "INFO"
    mcp_allowed_hosts: str = ""
    mcp_api_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
