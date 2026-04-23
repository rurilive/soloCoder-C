"""房源相关Pydantic模型"""

from datetime import datetime, date
from typing import Optional, Dict, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.models import (
    HouseStatus,
    HouseType,
    Orientation,
    Decoration,
    ImageType,
)


class HouseBase(BaseModel):
    """房源基础模型"""

    title: str = Field(..., min_length=5, max_length=200, description="房源标题")
    community: str = Field(..., min_length=2, max_length=100, description="小区名称")
    address: str = Field(..., min_length=5, max_length=300, description="详细地址")
    province: Optional[str] = Field(None, max_length=50, description="省")
    city: Optional[str] = Field(None, max_length=50, description="市")
    district: Optional[str] = Field(None, max_length=50, description="区")
    price: float = Field(..., gt=0, description="月租价格")
    deposit_type: str = Field(default="押一付三", max_length=50, description="押金方式")
    house_type: HouseType = Field(default=HouseType.ENTIRE, description="房屋类型")
    room_type: Optional[str] = Field(None, max_length=50, description="户型")
    area: Optional[float] = Field(None, gt=0, description="面积(平方米)")
    floor: Optional[int] = Field(None, ge=0, description="所在楼层")
    total_floors: Optional[int] = Field(None, ge=0, description="总楼层")
    orientation: Optional[Orientation] = Field(None, description="朝向")
    decoration: Optional[Decoration] = Field(None, description="装修程度")
    facilities: Dict = Field(default_factory=dict, description="设施配置")
    surrounding: Dict = Field(default_factory=dict, description="周边配套")
    description: Optional[str] = Field(None, description="详细描述")
    main_image: Optional[str] = Field(None, description="主图URL")
    video_url: Optional[str] = Field(None, description="视频URL")
    rent_start_date: Optional[date] = Field(None, description="可入住日期")
    min_rent_months: int = Field(default=1, ge=1, description="最短租期(月)")


class HouseCreate(HouseBase):
    """房源创建模型"""

    pass


class HouseUpdate(BaseModel):
    """房源更新模型"""

    title: Optional[str] = Field(None, min_length=5, max_length=200)
    community: Optional[str] = Field(None, min_length=2, max_length=100)
    address: Optional[str] = Field(None, min_length=5, max_length=300)
    province: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, gt=0)
    deposit_type: Optional[str] = Field(None, max_length=50)
    house_type: Optional[HouseType] = Field(None)
    room_type: Optional[str] = Field(None, max_length=50)
    area: Optional[float] = Field(None, gt=0)
    floor: Optional[int] = Field(None, ge=0)
    total_floors: Optional[int] = Field(None, ge=0)
    orientation: Optional[Orientation] = Field(None)
    decoration: Optional[Decoration] = Field(None)
    facilities: Optional[Dict] = Field(None)
    surrounding: Optional[Dict] = Field(None)
    description: Optional[str] = Field(None)
    main_image: Optional[str] = Field(None)
    video_url: Optional[str] = Field(None)
    status: Optional[HouseStatus] = Field(None)
    is_top: Optional[bool] = Field(None)
    is_recommended: Optional[bool] = Field(None)
    rent_start_date: Optional[date] = Field(None)
    min_rent_months: Optional[int] = Field(None, ge=1)


class HouseResponse(HouseBase):
    """房源响应模型"""

    id: UUID
    user_id: UUID
    status: HouseStatus
    view_count: int
    favorite_count: int
    is_top: bool
    is_recommended: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class HouseListResponse(HouseResponse):
    """房源列表响应模型（包含缩略信息）"""

    owner_name: Optional[str] = Field(None, description="发布者名称")
    owner_avatar: Optional[str] = Field(None, description="发布者头像")


class HouseImageResponse(BaseModel):
    """房源图片响应模型"""

    id: UUID
    house_id: UUID
    image_url: str
    image_type: ImageType
    sort_order: int
    is_main: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class HouseSearchParams(BaseModel):
    """房源搜索参数"""

    keyword: Optional[str] = Field(None, description="关键词搜索")
    city: Optional[str] = Field(None, description="城市")
    district: Optional[str] = Field(None, description="区域")
    min_price: Optional[float] = Field(None, ge=0, description="最低价格")
    max_price: Optional[float] = Field(None, ge=0, description="最高价格")
    house_type: Optional[HouseType] = Field(None, description="房屋类型")
    room_type: Optional[str] = Field(None, description="户型")
    min_area: Optional[float] = Field(None, ge=0, description="最小面积")
    max_area: Optional[float] = Field(None, ge=0, description="最大面积")
    decoration: Optional[Decoration] = Field(None, description="装修程度")
    orientation: Optional[Orientation] = Field(None, description="朝向")
    facilities: Optional[List[str]] = Field(None, description="设施筛选")
    status: Optional[HouseStatus] = Field(default=HouseStatus.PUBLISHED, description="房源状态")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方式(asc/desc)")
