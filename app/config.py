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

    guide_request_interval: float = Field(
        default=1.0,
        description="Delay between guide page fetches to reduce bot detection risk",
    )

    hltb_request_interval: float = Field(
        default=1.2,
        description="Delay between HowLongToBeat requests to avoid captchas",
    )

    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for analyzing achievements"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Model to use for identifying main-story achievements",
    )
    openai_request_interval: float = Field(
        default=2.0,
        description="Delay between OpenAI requests to respect rate limits",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
