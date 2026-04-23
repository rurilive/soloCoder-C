"""配置模块测试

测试 app/config/settings.py 中的配置类和配置读取。
"""

import pytest
from unittest.mock import patch, MagicMock
import os


class TestSettingsDefaultValues:
    """测试配置默认值"""

    def test_settings_default_app_config(self):
        """测试应用配置默认值"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.app_name == "Rental Platform"
        assert settings.app_version == "1.0.0"
        assert settings.debug is True

    def test_settings_default_database(self):
        """测试数据库配置默认值"""
        from app.config.settings import Settings

        settings = Settings()

        assert "sqlite" in settings.database_url.lower()

    def test_settings_default_jwt(self):
        """测试 JWT 配置默认值"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_minutes == 43200  # 30天

    def test_settings_default_upload(self):
        """测试上传配置默认值"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.max_file_size == 100 * 1024 * 1024
        assert settings.allowed_image_types == ["jpg", "jpeg", "png", "gif", "webp"]
        assert settings.allowed_video_types == ["mp4", "avi", "mov", "mkv", "webm"]

    def test_settings_default_admin(self):
        """测试管理员配置默认值"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.admin_username == "admin"
        assert settings.admin_email == "admin@example.com"


class TestSettingsFromEnvironment:
    """测试从环境变量读取配置"""

    @patch.dict(os.environ, {"APP_NAME": "Custom App", "DEBUG": "false"})
    def test_env_app_config(self):
        """测试从环境变量读取应用配置"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.app_name == "Custom App"
        assert settings.debug is False

    @patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "60"})
    def test_env_jwt_expiry(self):
        """测试从环境变量读取 JWT 过期时间"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.access_token_expire_minutes == 60

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
    })
    def test_env_database_url(self):
        """测试从环境变量读取数据库 URL"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/db"


class TestGetSettings:
    """测试 get_settings 函数"""

    def test_get_settings_returns_singleton(self):
        """测试 get_settings 返回单例（缓存）"""
        from app.config.settings import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_returns_settings_instance(self):
        """测试 get_settings 返回 Settings 实例"""
        from app.config.settings import get_settings, Settings

        settings = get_settings()

        assert isinstance(settings, Settings)


class TestSettingsValidation:
    """测试配置验证"""

    def test_settings_type_validation(self):
        """测试配置类型验证"""
        from app.config.settings import Settings

        settings = Settings()

        assert isinstance(settings.debug, bool)
        assert isinstance(settings.access_token_expire_minutes, int)
        assert isinstance(settings.max_file_size, int)
        assert isinstance(settings.allowed_image_types, list)

    def test_settings_computed_fields(self):
        """测试计算字段"""
        from app.config.settings import Settings

        settings = Settings()

        assert "static" in str(settings.static_dir)
        assert "templates" in str(settings.templates_dir)
        assert "uploads" in str(settings.upload_dir)
        assert "images" in str(settings.upload_image_dir)
        assert "videos" in str(settings.upload_video_dir)
        assert "avatars" in str(settings.upload_avatar_dir)


class TestSettingsEdgeCases:
    """测试边界情况"""

    @patch.dict(os.environ, {"ALLOWED_HOSTS": '["http://localhost:8000", "http://example.com"]'})
    def test_parsing_allowed_hosts(self):
        """测试解析允许的主机列表"""
        from app.config.settings import Settings

        settings = Settings()

        assert len(settings.allowed_hosts) == 2
        assert "http://localhost:8000" in settings.allowed_hosts

    @patch.dict(os.environ, {
        "ADMIN_USERNAME": "superadmin",
        "ADMIN_PASSWORD": "supersecret",
        "ADMIN_EMAIL": "superadmin@example.com",
    })
    def test_custom_admin_credentials(self):
        """测试自定义管理员凭据"""
        from app.config.settings import Settings

        settings = Settings()

        assert settings.admin_username == "superadmin"
        assert settings.admin_password == "supersecret"
        assert settings.admin_email == "superadmin@example.com"
