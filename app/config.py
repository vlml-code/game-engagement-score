from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    database_url: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        description="SQLAlchemy database URL (async)",
    )

    steam_api_key: str | None = Field(
        default=None,
        description="Steam Web API key used for achievements and guide queries",
    )
    steam_request_interval: float = Field(
        default=0.35,
        description="Delay in seconds between Steam API requests to avoid rate limits",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
