from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MusicPlayer"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./music.db"
    jamendo_client_id: str = ""
    musicbrainz_user_agent: str = "MusicPlayer/1.0 (your@email.com)"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
