"""通用Pydantic模型"""

from typing import Generic, TypeVar, Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    """消息响应模型"""

    message: str = Field(..., description="消息内容")
    success: bool = Field(default=True, description="是否成功")


class IDResponse(BaseModel):
    """ID响应模型"""

    id: UUID = Field(..., description="资源ID")
    message: str = Field(default="success", description="消息")


class PaginatedParams(BaseModel):
    """分页参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    data: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=10, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")
