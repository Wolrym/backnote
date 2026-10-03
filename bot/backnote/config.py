from functools import cached_property
from zoneinfo import ZoneInfo

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "bot/.env", "../.env"),
        extra="ignore",
    )

    bot_token: SecretStr
    admin_id: int
    database_url: str = "sqlite+aiosqlite:///data/backnote.db"
    timezone: str = "Europe/Kyiv"
    web_url: str | None = None

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-flash-latest"
    summary_language: str = "Ukrainian"

    @cached_property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.get_secret_value())
