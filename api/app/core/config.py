from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "oge.gl API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/oge"
    oge_base_url: str = "https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
    scraper_request_timeout: float = 30.0
    ingest_worker_poll_interval_seconds: float = 15.0
    ingest_worker_max_jobs_per_run: int = 10

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )


settings = Settings()
