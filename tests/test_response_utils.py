"""响应工具函数测试

测试 app/utils/response.py 中的响应封装工具。
"""

import pytest
import datetime


class TestResponseUtils:
    """测试响应工具函数"""

    def test_success_response_default(self):
        """测试默认成功响应"""
        from app.utils.response import success_response

        result = success_response()

        assert result["code"] == 200
        assert result["message"] == "success"
        assert result["data"] is None
        assert "timestamp" in result

    def test_success_response_with_data(self):
        """测试带数据的成功响应"""
        from app.utils.response import success_response

        test_data = {"key": "value", "list": [1, 2, 3]}
        result = success_response(data=test_data, message="获取成功")

        assert result["code"] == 200
        assert result["message"] == "获取成功"
        assert result["data"] == test_data

    def test_success_response_with_custom_code(self):
        """测试自定义状态码"""
        from app.utils.response import success_response

        result = success_response(message="已创建", code=201)

        assert result["code"] == 201
        assert result["message"] == "已创建"

    def test_error_response_default(self):
        """测试默认错误响应"""
        from app.utils.response import error_response

        result = error_response()

        assert result["code"] == 400
        assert result["message"] == "error"
        assert result["data"] is None
        assert "timestamp" in result

    def test_error_response_with_message(self):
        """测试带消息的错误响应"""
        from app.utils.response import error_response

        result = error_response(message="参数验证失败", code=422)

        assert result["code"] == 422
        assert result["message"] == "参数验证失败"

    def test_error_response_with_data(self):
        """测试带数据的错误响应"""
        from app.utils.response import error_response

        error_details = {"field": "username", "error": "用户名已存在"}
        result = error_response(message="验证失败", data=error_details)

        assert result["message"] == "验证失败"
        assert result["data"] == error_details

    def test_paginated_response(self):
        """测试分页响应"""
        from app.utils.response import paginated_response

        test_data = [
            {"id": 1, "name": "item1"},
            {"id": 2, "name": "item2"},
            {"id": 3, "name": "item3"},
        ]

        result = paginated_response(
            data=test_data,
            total=25,
            page=2,
            page_size=10,
            message="获取成功"
        )

        assert result["code"] == 200
        assert result["message"] == "获取成功"
        assert result["data"] == test_data
        assert result["total"] == 25
        assert result["page"] == 2
        assert result["page_size"] == 10
        assert result["total_pages"] == 3  # 25 / 10 = 2.5 -> ceil = 3
        assert "timestamp" in result

    def test_paginated_response_edge_cases(self):
        """测试分页响应边界情况"""
        from app.utils.response import paginated_response

        # 空数据
        result = paginated_response(data=[], total=0, page=1, page_size=10)
        assert result["total_pages"] == 0

        # 刚好一页
        result = paginated_response(data=[1, 2], total=2, page=1, page_size=10)
        assert result["total_pages"] == 1

        # page_size 为 0 的情况（应该安全处理）
        result = paginated_response(data=[], total=10, page=1, page_size=0)
        assert result["total_pages"] == 0


class TestAPIResponseModel:
    """测试 APIResponse Pydantic 模型"""

    def test_api_response_default(self):
        """测试默认 APIResponse"""
        from app.utils.response import APIResponse

        response = APIResponse[int]()

        assert response.code == 200
        assert response.message == "success"
        assert response.data is None
        assert response.timestamp is not None

    def test_api_response_with_data(self):
        """测试带数据的 APIResponse"""
        from app.utils.response import APIResponse

        response = APIResponse[str](
            code=200,
            message="success",
            data="test data"
        )

        assert response.data == "test data"

    def test_api_response_model_dump(self):
        """测试 APIResponse 转字典"""
        from app.utils.response import APIResponse

        response = APIResponse[dict](
            code=201,
            message="Created",
            data={"id": 123}
        )

        result = response.model_dump()

        assert result["code"] == 201
        assert result["message"] == "Created"
        assert result["data"] == {"id": 123}


class TestPaginatedResponseModel:
    """测试 PaginatedResponse Pydantic 模型"""

    def test_paginated_response_default(self):
        """测试默认 PaginatedResponse"""
        from app.utils.response import PaginatedResponse

        response = PaginatedResponse[int]()

        assert response.code == 200
        assert response.message == "success"
        assert response.data == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 0

    def test_paginated_response_with_data(self):
        """测试带数据的 PaginatedResponse"""
        from app.utils.response import PaginatedResponse

        response = PaginatedResponse[dict](
            data=[{"id": 1}, {"id": 2}],
            total=100,
            page=2,
            page_size=10,
            total_pages=10
        )

        assert len(response.data) == 2
        assert response.total == 100
        assert response.page == 2
        assert response.page_size == 10
        assert response.total_pages == 10
