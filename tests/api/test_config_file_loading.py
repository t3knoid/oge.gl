from __future__ import annotations

from pathlib import Path
import tomllib

from pydantic import ValidationError
import pytest

from app.core.config import CONFIG_FILE_ENV_VAR, DEFAULT_CONFIG_FILE_PATH, Settings


def test_default_config_file_contains_required_keys() -> None:
    assert DEFAULT_CONFIG_FILE_PATH.exists()

    payload = tomllib.loads(DEFAULT_CONFIG_FILE_PATH.read_text())
    required_keys = {
        "app_name",
        "app_version",
        "api_v1_prefix",
        "database_url",
        "oge_base_url",
        "scraper_request_timeout",
        "ingest_worker_poll_interval_seconds",
        "ingest_worker_max_jobs_per_run",
        "cors_allow_origins",
        "log_level",
    }

    assert required_keys.issubset(set(payload.keys()))


def test_settings_loads_values_from_config_file(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "settings.toml"
    config_file.write_text(
        "\n".join(
            [
                'log_level = "WARNING"',
                "ingest_worker_max_jobs_per_run = 7",
                'cors_allow_origins = ["http://example.test:5173"]',
            ]
        )
    )

    monkeypatch.setenv(CONFIG_FILE_ENV_VAR, str(config_file))
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("INGEST_WORKER_MAX_JOBS_PER_RUN", raising=False)

    settings = Settings()

    assert settings.log_level == "WARNING"
    assert settings.ingest_worker_max_jobs_per_run == 7
    assert settings.cors_allow_origins == ["http://example.test:5173"]


def test_environment_values_override_config_file_values(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "settings.toml"
    config_file.write_text('log_level = "WARNING"\n')

    monkeypatch.setenv(CONFIG_FILE_ENV_VAR, str(config_file))
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    settings = Settings()

    assert settings.log_level == "ERROR"


def test_settings_validation_fails_for_invalid_file_values(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "settings.toml"
    config_file.write_text('runtime_environment = "invalid"\n')

    monkeypatch.setenv(CONFIG_FILE_ENV_VAR, str(config_file))

    with pytest.raises(ValidationError):
        Settings()


def test_missing_config_file_path_falls_back_to_defaults(monkeypatch, tmp_path: Path) -> None:
    missing_file = tmp_path / "does-not-exist.toml"

    monkeypatch.setenv(CONFIG_FILE_ENV_VAR, str(missing_file))
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.log_level == "INFO"


def test_api_and_worker_use_shared_settings_singleton() -> None:
    from app import main as main_module
    from app.workers import runner as runner_module

    assert main_module.settings is runner_module.settings
