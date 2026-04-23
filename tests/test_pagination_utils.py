"""分页工具测试

测试 app/utils/pagination.py 和 app/schemas/common.py 中的分页工具。
"""

import pytest


class TestPaginationParams:
    """测试 PaginationParams 分页参数类"""

    def test_default_values(self):
        """测试默认值"""
        from app.utils.pagination import PaginationParams

        params = PaginationParams()

        assert params.page == 1
        assert params.page_size == 10

    def test_offset_calculation(self):
        """测试 offset 计算"""
        from app.utils.pagination import PaginationParams

        params = PaginationParams(page=1, page_size=10)
        assert params.offset == 0  # (1-1) * 10 = 0

        params = PaginationParams(page=2, page_size=10)
        assert params.offset == 10  # (2-1) * 10 = 10

        params = PaginationParams(page=5, page_size=20)
        assert params.offset == 80  # (5-1) * 20 = 80

    def test_limit_property(self):
        """测试 limit 属性"""
        from app.utils.pagination import PaginationParams

        params = PaginationParams(page_size=15)
        assert params.limit == 15

        params = PaginationParams(page_size=50)
        assert params.limit == 50

    def test_validation_min_page(self):
        """测试 page 最小值验证"""
        from app.utils.pagination import PaginationParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PaginationParams(page=0)

        with pytest.raises(ValidationError):
            PaginationParams(page=-1)

    def test_validation_page_size_range(self):
        """测试 page_size 范围验证"""
        from app.utils.pagination import PaginationParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PaginationParams(page_size=0)

        with pytest.raises(ValidationError):
            PaginationParams(page_size=101)

        valid = PaginationParams(page_size=50)
        assert valid.page_size == 50

        valid = PaginationParams(page_size=1)
        assert valid.page_size == 1

        valid = PaginationParams(page_size=100)
        assert valid.page_size == 100


class TestPaginatedParamsCommon:
    """测试 app/schemas/common.py 中的 PaginatedParams"""

    def test_default_values(self):
        """测试默认值"""
        from app.schemas.common import PaginatedParams

        params = PaginatedParams()

        assert params.page == 1
        assert params.page_size == 10

    def test_offset_calculation(self):
        """测试 offset 计算"""
        from app.schemas.common import PaginatedParams

        params = PaginatedParams(page=3, page_size=20)
        assert params.offset == 40  # (3-1) * 20 = 40

    def test_limit_property(self):
        """测试 limit 属性"""
        from app.schemas.common import PaginatedParams

        params = PaginatedParams(page_size=25)
        assert params.limit == 25

    def test_validation(self):
        """测试验证"""
        from app.schemas.common import PaginatedParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PaginatedParams(page=0)

        with pytest.raises(ValidationError):
            PaginatedParams(page_size=0)

        with pytest.raises(ValidationError):
            PaginatedParams(page_size=101)


class TestPaginatedResponseCommon:
    """测试 app/schemas/common.py 中的 PaginatedResponse"""

    def test_default_values(self):
        """测试默认值"""
        from app.schemas.common import PaginatedResponse

        response = PaginatedResponse[int]()

        assert response.data == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 0

    def test_with_data(self):
        """测试带数据"""
        from app.schemas.common import PaginatedResponse

        response = PaginatedResponse[dict](
            data=[{"id": 1}, {"id": 2}, {"id": 3}],
            total=150,
            page=2,
            page_size=10,
            total_pages=15
        )

        assert len(response.data) == 3
        assert response.total == 150
        assert response.page == 2
        assert response.page_size == 10
        assert response.total_pages == 15

    def test_model_dump(self):
        """测试模型转字典"""
        from app.schemas.common import PaginatedResponse

        response = PaginatedResponse[str](
            data=["item1", "item2"],
            total=100,
            page=1,
            page_size=20,
            total_pages=5
        )

        result = response.model_dump()

        assert result["data"] == ["item1", "item2"]
        assert result["total"] == 100
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total_pages"] == 5


class TestIDResponse:
    """测试 IDResponse"""

    def test_id_response(self):
        """测试 ID 响应"""
        from app.schemas.common import IDResponse
        from uuid import uuid4

        test_id = uuid4()
        response = IDResponse(id=test_id, message="创建成功")

        assert response.id == test_id
        assert response.message == "创建成功"

    def test_id_response_default_message(self):
        """测试默认消息"""
        from app.schemas.common import IDResponse
        from uuid import uuid4

        test_id = uuid4()
        response = IDResponse(id=test_id)

        assert response.id == test_id
        assert response.message == "success"


class TestMessageResponse:
    """测试 MessageResponse"""

    def test_message_response(self):
        """测试消息响应"""
        from app.schemas.common import MessageResponse

        response = MessageResponse(message="操作成功", success=True)

        assert response.message == "操作成功"
        assert response.success is True

    def test_message_response_default(self):
        """测试默认值"""
        from app.schemas.common import MessageResponse

        response = MessageResponse(message="操作失败", success=False)

        assert response.message == "操作失败"
        assert response.success is False
