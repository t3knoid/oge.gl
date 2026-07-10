from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "oge.gl API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/oge"

    model_config = SettingsConfigDict(
        env_prefix="OGE_",
        extra="ignore",
    )


settings = Settings()
