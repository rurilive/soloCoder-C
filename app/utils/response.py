"""响应封装工具"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """通用响应模型"""

    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[T] = Field(default=None, description="数据")
    timestamp: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat())


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    code: int = Field(default=200)
    message: str = Field(default="success")
    data: List[T] = Field(default_factory=list)
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=10, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")
    timestamp: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat())


def success_response(data: Any = None, message: str = "success", code: int = 200) -> dict:
    """成功响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
    }


def error_response(message: str = "error", code: int = 400, data: Any = None) -> dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
    }


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "success",
) -> dict:
    """分页响应"""
    import math

    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    return {
        "code": 200,
        "message": message,
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
    }
