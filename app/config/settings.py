"""应用配置"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""

    app_name: str = Field(default="租房管理系统", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=True, alias="DEBUG")
    secret_key: str = Field(default="dev-secret-key-please-change", alias="SECRET_KEY")
    allowed_hosts_str: str = Field(default="localhost,127.0.0.1", alias="ALLOWED_HOSTS")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./rental.db", alias="DATABASE_URL"
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")

    jwt_secret_key: str = Field(
        default="dev-jwt-secret-key-please-change", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    upload_dir: str = Field(default="./app/static/uploads", alias="UPLOAD_DIR")
    max_file_size: int = Field(default=10 * 1024 * 1024, alias="MAX_FILE_SIZE")
    allowed_image_types_str: str = Field(
        default="image/jpeg,image/png,image/gif,image/webp",
        alias="ALLOWED_IMAGE_TYPES"
    )
    allowed_video_types_str: str = Field(
        default="video/mp4,video/webm,video/quicktime",
        alias="ALLOWED_VIDEO_TYPES"
    )

    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @property
    def allowed_hosts(self) -> List[str]:
        return [h.strip() for h in self.allowed_hosts_str.split(",") if h.strip()]

    @property
    def allowed_image_types(self) -> List[str]:
        return [t.strip() for t in self.allowed_image_types_str.split(",") if t.strip()]

    @property
    def allowed_video_types(self) -> List[str]:
        return [t.strip() for t in self.allowed_video_types_str.split(",") if t.strip()]

    @property
    def upload_image_dir(self) -> str:
        return os.path.join(self.upload_dir, "images")

    @property
    def upload_video_dir(self) -> str:
        return os.path.join(self.upload_dir, "videos")

    @property
    def upload_avatar_dir(self) -> str:
        return os.path.join(self.upload_dir, "avatars")


def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
