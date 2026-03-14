"""Application configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "cashclaw-openclaw-adapter"
    app_version: str = "0.1.0"
    cashclaw_base_url: str = "http://127.0.0.1:8080"
    cashclaw_timeout_sec: float = Field(default=10.0, gt=0)
    cashclaw_connect_timeout_sec: float = Field(default=3.0, gt=0)
    cashclaw_safe_retry_count: int = Field(default=1, ge=0, le=5)
    memgraph_host: str = "odin"
    memgraph_port: int = Field(default=7687, ge=1, le=65535)
    memgraph_username: str = ""
    memgraph_password: str = ""
    memgraph_encrypted: bool = False
    log_level: str = "INFO"
    adapter_require_localhost: bool = True
    startup_validate_dependencies: bool = False

    @property
    def memgraph_url(self) -> str:
        """Return the Memgraph connection URL."""

        protocol = "bolt+s" if self.memgraph_encrypted else "bolt"
        return f"{protocol}://{self.memgraph_host}:{self.memgraph_port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
