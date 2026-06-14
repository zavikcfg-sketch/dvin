from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str = ""
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/vpn_bot.db"
    admin_secret_key: str = "change-me"
    admin_username: str = "admin"
    admin_password: str = "change-me"
    trial_days: int = 3
    default_traffic_gb: int = 50
    max_devices: int = 3

    # TVIL integration (webhook + object ID, без iCal)
    public_base_url: str = ""
    tvil_webhook_secret: str = ""

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids.strip():
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
