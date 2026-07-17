import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource


DEFAULT_CONFIG_FILE_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"
CONFIG_FILE_ENV_VAR = "APP_CONFIG_FILE"


class Settings(BaseSettings):
    app_name: str = "oge.gl API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/oge"
    oge_base_url: str = "https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
    scraper_request_timeout: float = 30.0
    ingest_worker_poll_interval_seconds: float = 15.0
    ingest_worker_max_jobs_per_run: int = 10
    runtime_environment: Literal["local", "non_local"] = "local"
    log_level: str = "INFO"
    log_format: Literal["auto", "json", "text"] = "auto"
    log_enable_row_debug: bool = False
    log_file_path: str = "/var/log/oge.gl/backend.log"
    manual_ingest_default_mode: Literal["incremental"] = "incremental"
    manual_ingest_default_limit: int = Field(default=1, ge=1)
    manual_ingest_max_limit: int = Field(default=25, ge=1)
    cors_allow_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgresql_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        if value.startswith("postgres://"):
            return f"postgresql+psycopg://{value[len('postgres://') :]}"

        if value.startswith("postgresql://"):
            return f"postgresql+psycopg://{value[len('postgresql://') :]}"

        return value

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        def empty_settings_source():
            return {}

        configured_path = os.getenv(CONFIG_FILE_ENV_VAR)
        config_file_path = Path(configured_path).expanduser() if configured_path else DEFAULT_CONFIG_FILE_PATH

        if not config_file_path.exists():
            config_file_source = empty_settings_source
        else:
            config_file_source = TomlConfigSettingsSource(settings_cls, toml_file=config_file_path)

        # Precedence: init kwargs > environment variables > config file > dotenv > file secrets
        return init_settings, env_settings, config_file_source, dotenv_settings, file_secret_settings

    @model_validator(mode="after")
    def validate_manual_ingest_defaults(self) -> "Settings":
        if self.manual_ingest_default_limit > self.manual_ingest_max_limit:
            raise ValueError("manual_ingest_default_limit must be less than or equal to manual_ingest_max_limit")
        return self


settings = Settings()
