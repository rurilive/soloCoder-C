"""Pydantic Schemas 测试

测试 app/schemas/ 目录下的所有 Pydantic 模型。
"""

import pytest
from uuid import uuid4
from datetime import datetime


class TestUserSchemas:
    """测试用户相关 Schema"""

    def test_user_base_valid(self):
        """测试用户基础模型验证"""
        from app.schemas.user import UserBase

        user = UserBase(
            username="testuser",
            phone="13800138000",
            email="test@example.com",
            nickname="Test User",
            gender="male",
        )

        assert user.username == "testuser"
        assert user.phone == "13800138000"
        assert user.email == "test@example.com"
        assert user.nickname == "Test User"
        assert user.gender == "male"

    def test_user_base_min_length(self):
        """测试用户名字段最小长度"""
        from app.schemas.user import UserBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserBase(username="ab")

        valid = UserBase(username="abc")
        assert valid.username == "abc"

    def test_user_create(self):
        """测试用户创建模型"""
        from app.schemas.user import UserCreate

        user = UserCreate(
            username="testuser",
            password="password123",
            phone="13800138000",
        )

        assert user.username == "testuser"
        assert user.password == "password123"

    def test_user_create_password_validation(self):
        """测试密码验证"""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(username="testuser", password="123")

        valid = UserCreate(username="testuser", password="123456")
        assert valid.password == "123456"

    def test_user_login(self):
        """测试用户登录模型"""
        from app.schemas.user import UserLogin

        login = UserLogin(
            username="testuser",
            password="password123",
        )

        assert login.username == "testuser"
        assert login.password == "password123"

    def test_user_update(self):
        """测试用户更新模型"""
        from app.schemas.user import UserUpdate

        update = UserUpdate(
            phone="13900139000",
            nickname="New Nickname",
        )

        assert update.phone == "13900139000"
        assert update.nickname == "New Nickname"


class TestHouseSchemas:
    """测试房源相关 Schema"""

    def test_house_base_minimal(self):
        """测试房源基础模型最小数据"""
        from app.schemas.house import HouseBase

        house = HouseBase(
            title="精装两居室 近地铁",
            address="北京市朝阳区望京SOHO",
            price=5000.0,
        )

        assert house.title == "精装两居室 近地铁"
        assert house.address == "北京市朝阳区望京SOHO"
        assert house.price == 5000.0

    def test_house_base_full(self):
        """测试房源基础模型完整数据"""
        from app.schemas.house import HouseBase
        from app.models import Orientation, Decoration, HouseType

        house = HouseBase(
            title="精装两居室 近地铁",
            community="望京花园",
            address="北京市朝阳区望京SOHO",
            city="北京",
            district="朝阳区",
            price=5000.0,
            deposit_type="押一付三",
            house_type=HouseType.ENTIRE,
            property_type="apartment",
            room_type="2室1厅",
            bedrooms=2,
            livingrooms=1,
            bathrooms=1,
            area=85.5,
            floor=12,
            total_floors=28,
            floor_str="12/28",
            orientation=Orientation.SOUTH,
            orientation_str="south",
            decoration=Decoration.FINE,
            decoration_str="fine",
            description="精装修，拎包入住，近地铁15号线",
            contact_name="张先生",
            contact_phone="13800138000",
        )

        assert house.title == "精装两居室 近地铁"
        assert house.community == "望京花园"
        assert house.price == 5000.0
        assert house.bedrooms == 2
        assert house.livingrooms == 1
        assert house.bathrooms == 1
        assert house.area == 85.5
        assert house.property_type == "apartment"
        assert house.orientation == Orientation.SOUTH
        assert house.decoration == Decoration.FINE

    def test_house_base_price_validation(self):
        """测试价格验证"""
        from app.schemas.house import HouseBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HouseBase(
                title="测试房源",
                address="测试地址",
                price=-100.0,
            )

        with pytest.raises(ValidationError):
            HouseBase(
                title="测试房源",
                address="测试地址",
                price=0.0,
            )

        valid = HouseBase(
            title="测试房源",
            address="测试地址",
            price=1.0,
        )
        assert valid.price == 1.0

    def test_house_create(self):
        """测试房源创建模型"""
        from app.schemas.house import HouseCreate

        house = HouseCreate(
            title="测试房源",
            address="测试地址",
            price=3000.0,
        )

        assert house.title == "测试房源"
        assert house.price == 3000.0

    def test_house_update(self):
        """测试房源更新模型"""
        from app.schemas.house import HouseUpdate

        update = HouseUpdate(
            title="更新后的标题",
            price=3500.0,
            description="更新后的描述",
        )

        assert update.title == "更新后的标题"
        assert update.price == 3500.0

    def test_house_search_params(self):
        """测试房源搜索参数"""
        from app.schemas.house import HouseSearchParams
        from app.models import HouseType, Decoration, Orientation, HouseStatus

        params = HouseSearchParams(
            keyword="地铁",
            city="北京",
            district="朝阳区",
            min_price=2000.0,
            max_price=8000.0,
            house_type=HouseType.ENTIRE,
            min_area=50.0,
            max_area=120.0,
            decoration=Decoration.FINE,
            orientation=Orientation.SOUTH,
            status=HouseStatus.PUBLISHED,
            sort_by="price",
            sort_order="asc",
        )

        assert params.keyword == "地铁"
        assert params.city == "北京"
        assert params.min_price == 2000.0
        assert params.max_price == 8000.0
        assert params.sort_by == "price"
        assert params.sort_order == "asc"


class TestCommonSchemas:
    """测试通用 Schema"""

    def test_message_response(self):
        """测试消息响应"""
        from app.schemas.common import MessageResponse

        response = MessageResponse(
            message="操作成功",
            success=True,
        )

        assert response.message == "操作成功"
        assert response.success is True

    def test_message_response_default(self):
        """测试消息响应默认值"""
        from app.schemas.common import MessageResponse

        response = MessageResponse(message="测试消息")

        assert response.message == "测试消息"
        assert response.success is True

    def test_id_response(self):
        """测试 ID 响应"""
        from app.schemas.common import IDResponse
        from uuid import uuid4

        test_id = uuid4()
        response = IDResponse(
            id=test_id,
            message="创建成功",
        )

        assert response.id == test_id
        assert response.message == "创建成功"

    def test_paginated_params(self):
        """测试分页参数"""
        from app.schemas.common import PaginatedParams

        params = PaginatedParams(
            page=3,
            page_size=20,
        )

        assert params.page == 3
        assert params.page_size == 20
        assert params.offset == 40  # (3-1) * 20
        assert params.limit == 20

    def test_paginated_params_validation(self):
        """测试分页参数验证"""
        from app.schemas.common import PaginatedParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PaginatedParams(page=0)

        with pytest.raises(ValidationError):
            PaginatedParams(page_size=0)

        with pytest.raises(ValidationError):
            PaginatedParams(page_size=101)


class TestSchemaModelDump:
    """测试 Schema 模型转字典"""

    def test_house_base_model_dump(self):
        """测试房源模型转字典"""
        from app.schemas.house import HouseBase

        house = HouseBase(
            title="测试房源",
            address="测试地址",
            price=3000.0,
        )

        data = house.model_dump()

        assert data["title"] == "测试房源"
        assert data["address"] == "测试地址"
        assert data["price"] == 3000.0

    def test_user_base_model_dump(self):
        """测试用户模型转字典"""
        from app.schemas.user import UserBase

        user = UserBase(
            username="testuser",
            nickname="Test User",
        )

        data = user.model_dump()

        assert data["username"] == "testuser"
        assert data["nickname"] == "Test User"
