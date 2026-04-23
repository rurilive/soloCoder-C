"""模块导入测试

这个测试文件用于验证所有模块可以正确导入，
防止出现类似 NameError: name 'X' is not defined 的问题。
"""

import pytest


class TestImports:
    """测试所有模块导入是否正常"""

    def test_import_app_main(self):
        """测试主模块导入"""
        from app.main import app
        assert app is not None

    def test_import_settings(self):
        """测试配置模块导入"""
        from app.config.settings import Settings, get_settings
        assert Settings is not None
        assert get_settings is not None

    def test_import_database(self):
        """测试数据库模块导入"""
        from app.config.database import (
            Base,
            engine,
            async_session_maker,
            get_async_session,
            init_db,
            close_db,
        )
        assert Base is not None
        assert engine is not None
        assert async_session_maker is not None

    def test_import_models(self):
        """测试模型模块导入"""
        from app.models import (
            User, House, HouseImage, Comment, Question, Answer,
            Favorite, FavoriteFolder, Like, Message, Notification,
            ViewingAppointment, Report, FAQ,
            UserRole, UserStatus, HouseStatus, HouseType, Orientation,
            Decoration, ImageType, CommentStatus, QuestionStatus,
            MessageType, AppointmentStatus, ReportStatus, TargetType,
            NotificationType,
        )
        assert User is not None
        assert House is not None
        assert Orientation is not None
        assert Decoration is not None

    def test_import_house_router(self):
        """测试房源路由模块导入（关键测试）"""
        from app.routers import house
        assert house is not None
        assert house.parse_orientation is not None
        assert house.parse_decoration is not None
        assert house.parse_floor is not None
        assert house.facilities_list_to_dict is not None

    def test_import_house_schemas(self):
        """测试房源Schema导入"""
        from app.schemas.house import (
            HouseBase, HouseCreate, HouseUpdate, HouseResponse,
            HouseListResponse, HouseImageResponse, HouseSearchParams,
        )
        assert HouseBase is not None
        assert HouseCreate is not None
        assert HouseResponse is not None

    def test_import_auth_router(self):
        """测试认证路由导入"""
        from app.routers import auth
        assert auth is not None

    def test_import_http_utils(self):
        """测试HTTP工具函数（main.js中的模块，这里测试后端对应）"""
        from app.utils.response import (
            success_response,
            error_response,
            paginated_response,
        )
        assert success_response is not None
        assert error_response is not None

    def test_import_security_utils(self):
        """测试安全工具导入"""
        from app.utils.security import (
            get_password_hash,
            verify_password,
            create_access_token,
            create_refresh_token,
            decode_access_token,
        )
        assert get_password_hash is not None
        assert verify_password is not None

    def test_all_routers_importable(self):
        """测试所有路由模块可导入"""
        from app.routers import auth, house
        
        assert auth.router is not None
        assert house.router is not None

    def test_house_router_parse_functions(self):
        """测试房源路由中解析函数的类型注解"""
        from app.routers.house import (
            parse_orientation,
            parse_decoration,
            parse_floor,
            facilities_list_to_dict,
        )
        from app.models import Orientation, Decoration
        
        assert callable(parse_orientation)
        assert callable(parse_decoration)
        assert callable(parse_floor)
        assert callable(facilities_list_to_dict)

    def test_app_main_router_inclusion(self):
        """测试主应用中路由是否正确注册"""
        from app.main import app
        
        routes = [route.path for route in app.routes]
        
        assert any("/api/houses" in route for route in routes)
        assert any("/api/auth" in route for route in routes)
