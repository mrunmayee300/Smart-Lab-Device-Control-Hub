from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SMART_LAB_", extra="ignore")

    app_name: str = "Smart Lab Device Control Hub"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051
    database_url: str = "sqlite+aiosqlite:///./smart_lab.db"
    log_level: str = "INFO"
    telemetry_retention_days: int = 30
    device_poll_interval_seconds: float = 0.5
    max_command_rate_per_minute: int = 120
    worker_heartbeat_seconds: float = 2.0
    cpu_worker_count: int = Field(default=2, ge=1)
    enable_worker_runtime: bool = True
    ipc_socket_host: str = "127.0.0.1"
    ipc_socket_port: int = 9100
    state_dir: Path = Path("./runtime")


@lru_cache
def get_settings() -> Settings:
    return Settings()
