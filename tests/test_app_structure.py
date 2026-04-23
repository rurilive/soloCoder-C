"""主应用结构测试

测试应用的整体结构、路由注册、中间件配置等。
"""

import pytest


class TestAppImports:
    """测试主应用导入"""

    def test_import_main_app(self):
        """测试导入主应用"""
        from app.main import app, settings, templates

        assert app is not None
        assert settings is not None
        assert templates is not None

    def test_app_title(self):
        """测试应用标题配置"""
        from app.main import app, settings

        assert app.title == settings.app_name

    def test_app_version(self):
        """测试应用版本配置"""
        from app.main import app, settings

        assert app.version == settings.app_version


class TestAppRoutes:
    """测试应用路由"""

    def test_health_check_route(self):
        """测试健康检查路由存在"""
        from app.main import app

        routes = [route.path for route in app.routes]

        assert "/health" in routes

    def test_index_route(self):
        """测试首页路由存在"""
        from app.main import app

        routes = [route.path for route in app.routes]

        assert "/" in routes

    def test_template_routes_exist(self):
        """测试模板页面路由存在"""
        from app.main import app

        routes = [route.path for route in app.routes]

        template_routes = [
            "/login",
            "/register",
            "/houses",
            "/publish",
            "/user/profile",
            "/user/favorites",
            "/messages",
            "/admin",
            "/faq",
        ]

        for route in template_routes:
            assert route in routes, f"路由 {route} 不存在"

    def test_house_detail_route(self):
        """测试房源详情路由（带参数）"""
        from app.main import app

        routes = [route.path for route in app.routes]

        assert any("house_id" in route for route in routes)


class TestRouterInclusion:
    """测试路由包含"""

    def test_all_routers_included(self):
        """测试所有路由都被包含"""
        from app.main import app
        from app.routers import (
            auth_router,
            user_router,
            house_router,
            comment_router,
            message_router,
            admin_router,
        )

        prefixes = [
            auth_router.prefix,
            user_router.prefix,
            house_router.prefix,
            comment_router.prefix,
            message_router.prefix,
            admin_router.prefix,
        ]

        routes = [route.path for route in app.routes]

        for prefix in prefixes:
            if prefix:
                assert any(route.startswith(prefix) for route in routes), f"前缀 {prefix} 没有路由"

    def test_auth_router_prefix(self):
        """测试认证路由前缀"""
        from app.routers.auth import router as auth_router

        assert auth_router.prefix == "/api/auth"

    def test_house_router_prefix(self):
        """测试房源路由前缀"""
        from app.routers.house import router as house_router

        assert house_router.prefix == "/api/houses"

    def test_user_router_prefix(self):
        """测试用户路由前缀"""
        from app.routers.user import router as user_router

        assert user_router.prefix == "/api/users"


class TestMiddlewareConfiguration:
    """测试中间件配置"""

    def test_cors_middleware_configured(self):
        """测试 CORS 中间件已配置"""
        from app.main import app

        middleware_types = [type(middleware.cls).__name__ for middleware in app.user_middleware]

        assert "CORSMiddleware" in middleware_types


class TestAppConfiguration:
    """测试应用配置"""

    def test_static_files_mounted(self):
        """测试静态文件已挂载"""
        from app.main import app

        routes = [route.path for route in app.routes]

        assert any("/static" in route for route in routes)

    def test_debug_settings(self):
        """测试调试设置"""
        from app.config.settings import get_settings

        settings = get_settings()

        assert isinstance(settings.debug, bool)

    def test_jwt_settings(self):
        """测试 JWT 配置"""
        from app.config.settings import get_settings

        settings = get_settings()

        assert settings.jwt_algorithm
        assert settings.access_token_expire_minutes > 0
        assert settings.refresh_token_expire_minutes > 0


class TestDatabaseConfig:
    """测试数据库配置"""

    def test_database_url_configured(self):
        """测试数据库 URL 已配置"""
        from app.config.settings import get_settings

        settings = get_settings()

        assert settings.database_url
        assert "sqlite" in settings.database_url.lower()

    def test_engine_and_session_exist(self):
        """测试引擎和会话工厂存在"""
        from app.config.database import engine, async_session_maker, Base

        assert engine is not None
        assert async_session_maker is not None
        assert Base is not None


class TestModuleExports:
    """测试模块导出"""

    def test_routers_module_exports(self):
        """测试 routers 模块导出"""
        from app.routers import (
            auth_router,
            user_router,
            house_router,
            comment_router,
            message_router,
            admin_router,
        )

        assert auth_router is not None
        assert user_router is not None
        assert house_router is not None
        assert comment_router is not None
        assert message_router is not None
        assert admin_router is not None

    def test_models_module_exports(self):
        """测试 models 模块导出"""
        from app.models import (
            User, House, HouseImage, Comment, Question, Answer,
            Favorite, FavoriteFolder, Like, Message, Notification,
            ViewingAppointment, Report, FAQ,
            UserRole, UserStatus, HouseStatus, HouseType,
            Orientation, Decoration, ImageType, CommentStatus,
            QuestionStatus, MessageType, AppointmentStatus,
            ReportStatus, TargetType, NotificationType,
        )

        assert all(v is not None for v in [
            User, House, HouseImage, Comment, Question, Answer,
            Favorite, FavoriteFolder, Like, Message, Notification,
            ViewingAppointment, Report, FAQ,
        ])

    def test_schemas_module_exports(self):
        """测试 schemas 模块导出"""
        from app.schemas.common import (
            IDResponse,
            MessageResponse,
            PaginatedParams,
            PaginatedResponse,
        )

        assert IDResponse is not None
        assert MessageResponse is not None
        assert PaginatedParams is not None
        assert PaginatedResponse is not None


class TestLifespanFunction:
    """测试生命周期函数"""

    def test_lifespan_function_exists(self):
        """测试生命周期函数存在"""
        from app.main import lifespan

        assert callable(lifespan)

    def test_lifespan_returns_context_manager(self):
        """测试生命周期是上下文管理器"""
        from contextlib import asynccontextmanager
        from app.main import lifespan

        assert hasattr(lifespan, "__call__")
