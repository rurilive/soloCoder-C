"""用户相关Pydantic模型"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, field_validator

from app.models import UserRole, UserStatus


class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    avatar: Optional[str] = Field(None, description="头像URL")


class UserCreate(UserBase):
    """用户创建模型"""

    password: str = Field(..., min_length=6, max_length=128, description="密码")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度至少6位")
        return v


class UserUpdate(BaseModel):
    """用户更新模型"""

    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = Field(None)
    nickname: Optional[str] = Field(None, max_length=50)
    gender: Optional[str] = Field(None, max_length=10)
    avatar: Optional[str] = Field(None)


class UserLogin(BaseModel):
    """用户登录模型"""

    username: str = Field(..., description="用户名/手机号/邮箱")
    password: str = Field(..., description="密码")


class UserResponse(UserBase):
    """用户响应模型"""

    id: UUID
    role: UserRole
    is_verified: bool
    credit_score: int
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class Token(BaseModel):
    """令牌模型"""

    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")
    user: UserResponse


class TokenPayload(BaseModel):
    """令牌载荷模型"""

    sub: str
    exp: datetime
    type: str
