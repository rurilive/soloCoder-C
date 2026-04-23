"""房源路由"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, or_, and_
from uuid import UUID
import json

from app.config.database import get_async_session
from app.models import (
    User, House, HouseImage, HouseStatus, HouseType,
    Favorite, Like, TargetType, FAQ,
    Orientation, Decoration,
)
from app.schemas.house import (
    HouseCreate, HouseUpdate, HouseResponse,
    HouseListResponse, HouseImageResponse,
    HouseSearchParams,
)
from app.schemas.common import PaginatedParams, IDResponse, MessageResponse
from app.routers.auth import get_current_active_user, get_current_landlord
from app.utils.response import success_response, error_response, paginated_response
from app.utils.file_handler import save_image, save_video, get_file_url
from app.utils.pagination import PaginationParams

router = APIRouter(prefix="/api/houses", tags=["房源"])


def parse_orientation(orientation_str: Optional[str]) -> Optional[Orientation]:
    """解析朝向字符串为枚举"""
    if not orientation_str:
        return None
    
    orientation_map = {
        "south": Orientation.SOUTH,
        "north": Orientation.NORTH,
        "east": Orientation.EAST,
        "west": Orientation.WEST,
        "southeast": Orientation.SOUTHEAST,
        "southwest": Orientation.SOUTHWEST,
        "northeast": Orientation.NORTHEAST,
        "northwest": Orientation.NORTHWEST,
    }
    
    lower_str = orientation_str.lower()
    if lower_str in orientation_map:
        return orientation_map[lower_str]
    
    try:
        return Orientation(orientation_str)
    except ValueError:
        return None


def parse_decoration(decoration_str: Optional[str]) -> Optional[Decoration]:
    """解析装修字符串为枚举"""
    if not decoration_str:
        return None
    
    decoration_map = {
        "bare": Decoration.BARE,
        "rough": Decoration.BARE,
        "simple": Decoration.SIMPLE,
        "standard": Decoration.SIMPLE,
        "fine": Decoration.FINE,
        "luxury": Decoration.LUXURY,
    }
    
    lower_str = decoration_str.lower()
    if lower_str in decoration_map:
        return decoration_map[lower_str]
    
    try:
        return Decoration(decoration_str)
    except ValueError:
        return None


def parse_floor(floor_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """解析楼层字符串 (如 "12/28") 为 (当前楼层, 总楼层)"""
    if not floor_str:
        return None, None
    
    if "/" in floor_str:
        parts = floor_str.split("/")
        try:
            current = int(parts[0].strip()) if parts[0].strip() else None
            total = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else None
            return current, total
        except ValueError:
            return None, None
    
    try:
        current = int(floor_str.strip())
        return current, None
    except ValueError:
        return None, None


def facilities_list_to_dict(facilities_list: Optional[List[str]]) -> dict:
    """将设施列表转换为字典"""
    if not facilities_list:
        return {}
    
    result = {}
    for item in facilities_list:
        if item:
            result[item] = True
    return result


@router.post("", response_model=IDResponse)
async def create_house(
    title: str = Form(...),
    community: Optional[str] = Form(None),
    address: str = Form(...),
    price: float = Form(...),
    house_type: HouseType = Form(default=HouseType.ENTIRE),
    deposit_type: str = Form(default="押一付三"),
    room_type: Optional[str] = Form(None),
    area: Optional[float] = Form(None),
    floor: Optional[int] = Form(None),
    total_floors: Optional[int] = Form(None),
    orientation: Optional[str] = Form(None),
    decoration: Optional[str] = Form(None),
    province: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    facilities: Optional[str] = Form("{}"),
    surrounding: Optional[str] = Form("{}"),
    description: Optional[str] = Form(None),
    rent_start_date: Optional[str] = Form(None),
    min_rent_months: int = Form(1),
    images: List[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_landlord),
    session: AsyncSession = Depends(get_async_session),
):
    """发布房源 (Form 格式)"""
    from datetime import date
    from app.models import Orientation, Decoration

    try:
        facilities_dict = json.loads(facilities) if facilities else {}
        surrounding_dict = json.loads(surrounding) if surrounding else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="设施或周边配置格式错误",
        )

    rent_start = None
    if rent_start_date:
        try:
            from datetime import datetime
            rent_start = datetime.strptime(rent_start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="日期格式错误，应为 YYYY-MM-DD",
            )

    orientation_enum = parse_orientation(orientation)
    decoration_enum = parse_decoration(decoration)

    community_value = community or title[:100] if not community else address[:50] if len(address) > 50 else address

    new_house = House(
        user_id=current_user.id,
        title=title,
        community=community_value,
        address=address,
        price=price,
        house_type=house_type,
        deposit_type=deposit_type,
        room_type=room_type,
        area=area,
        floor=floor,
        total_floors=total_floors,
        orientation=orientation_enum,
        decoration=decoration_enum,
        province=province,
        city=city,
        district=district,
        facilities=facilities_dict,
        surrounding=surrounding_dict,
        description=description,
        rent_start_date=rent_start,
        min_rent_months=min_rent_months,
        status=HouseStatus.PUBLISHED,
    )

    session.add(new_house)
    await session.flush()

    main_image_url = None
    if images:
        for i, image_file in enumerate(images):
            try:
                filename = await save_image(image_file)
                image_url = get_file_url(filename, file_type="image")

                if i == 0:
                    main_image_url = image_url
                    is_main = True
                else:
                    is_main = False

                house_image = HouseImage(
                    house_id=new_house.id,
                    image_url=image_url,
                    sort_order=i,
                    is_main=is_main,
                )
                session.add(house_image)
            except Exception:
                pass

        if main_image_url:
            new_house.main_image = main_image_url

    if video:
        try:
            filename = await save_video(video)
            video_url = get_file_url(filename, file_type="video")
            new_house.video_url = video_url
        except Exception:
            pass

    await session.commit()
    await session.refresh(new_house)

    return IDResponse(id=new_house.id, message="房源发布成功")


@router.post("/create", response_model=IDResponse)
async def create_house_json(
    house_data: HouseCreate,
    current_user: User = Depends(get_current_landlord),
    session: AsyncSession = Depends(get_async_session),
):
    """发布房源 (JSON 格式 - 用于前端表单)"""
    from app.models import Orientation, Decoration

    orientation_enum = None
    if house_data.orientation:
        orientation_enum = house_data.orientation
    elif house_data.orientation_str:
        orientation_enum = parse_orientation(house_data.orientation_str)

    decoration_enum = None
    if house_data.decoration:
        decoration_enum = house_data.decoration
    elif house_data.decoration_str:
        decoration_enum = parse_decoration(house_data.decoration_str)

    floor_num = house_data.floor
    total_floors_num = house_data.total_floors
    if house_data.floor_str and not floor_num:
        floor_num, total_floors_num = parse_floor(house_data.floor_str)

    facilities_dict = house_data.facilities or {}
    if house_data.facilities_list:
        facilities_dict = facilities_list_to_dict(house_data.facilities_list)

    community_value = house_data.community
    if not community_value:
        if house_data.district:
            community_value = f"{house_data.district}房源"
        elif house_data.city:
            community_value = f"{house_data.city}房源"
        else:
            community_value = house_data.title[:50] if len(house_data.title) > 50 else house_data.title

    room_type_value = house_data.room_type
    if not room_type_value and house_data.bedrooms is not None:
        parts = []
        if house_data.bedrooms >= 0:
            parts.append(f"{house_data.bedrooms}室")
        if house_data.livingrooms and house_data.livingrooms > 0:
            parts.append(f"{house_data.livingrooms}厅")
        if house_data.bathrooms and house_data.bathrooms > 0:
            parts.append(f"{house_data.bathrooms}卫")
        if parts:
            room_type_value = "".join(parts)

    new_house = House(
        user_id=current_user.id,
        title=house_data.title,
        community=community_value,
        address=house_data.address,
        price=house_data.price,
        house_type=house_data.house_type,
        deposit_type=house_data.deposit_type,
        room_type=room_type_value,
        bedrooms=house_data.bedrooms,
        livingrooms=house_data.livingrooms,
        bathrooms=house_data.bathrooms,
        area=house_data.area,
        floor=floor_num,
        total_floors=total_floors_num,
        orientation=orientation_enum,
        decoration=decoration_enum,
        province=house_data.province,
        city=house_data.city,
        district=house_data.district,
        facilities=facilities_dict,
        surrounding=house_data.surrounding,
        description=house_data.description,
        rent_start_date=house_data.rent_start_date,
        min_rent_months=house_data.min_rent_months,
        status=HouseStatus.PUBLISHED,
    )

    session.add(new_house)
    await session.commit()
    await session.refresh(new_house)

    return IDResponse(id=new_house.id, message="房源发布成功")


@router.get("")
async def get_houses(
    search_params: HouseSearchParams = Depends(),
    pagination: PaginatedParams = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    """获取房源列表（支持搜索和筛选）"""
    from sqlalchemy import select, func, or_, and_

    # 构建查询条件
    query = select(House)
    count_query = select(func.count(House.id))

    # 状态筛选
    if search_params.status:
        query = query.where(House.status == search_params.status)
        count_query = count_query.where(House.status == search_params.status)

    # 关键词搜索
    if search_params.keyword:
        keyword = f"%{search_params.keyword}%"
        query = query.where(
            or_(
                House.title.ilike(keyword),
                House.community.ilike(keyword),
                House.address.ilike(keyword),
            )
        )
        count_query = count_query.where(
            or_(
                House.title.ilike(keyword),
                House.community.ilike(keyword),
                House.address.ilike(keyword),
            )
        )

    # 城市筛选
    if search_params.city:
        query = query.where(House.city == search_params.city)
        count_query = count_query.where(House.city == search_params.city)

    # 区域筛选
    if search_params.district:
        query = query.where(House.district == search_params.district)
        count_query = count_query.where(House.district == search_params.district)

    # 价格区间筛选
    if search_params.min_price is not None:
        query = query.where(House.price >= search_params.min_price)
        count_query = count_query.where(House.price >= search_params.min_price)

    if search_params.max_price is not None:
        query = query.where(House.price <= search_params.max_price)
        count_query = count_query.where(House.price <= search_params.max_price)

    # 房屋类型筛选
    if search_params.house_type:
        query = query.where(House.house_type == search_params.house_type)
        count_query = count_query.where(House.house_type == search_params.house_type)

    # 户型筛选
    if search_params.room_type:
        query = query.where(House.room_type == search_params.room_type)
        count_query = count_query.where(House.room_type == search_params.room_type)

    # 面积区间筛选
    if search_params.min_area is not None:
        query = query.where(House.area >= search_params.min_area)
        count_query = count_query.where(House.area >= search_params.min_area)

    if search_params.max_area is not None:
        query = query.where(House.area <= search_params.max_area)
        count_query = count_query.where(House.area <= search_params.max_area)

    # 装修程度筛选
    if search_params.decoration:
        query = query.where(House.decoration == search_params.decoration)
        count_query = count_query.where(House.decoration == search_params.decoration)

    # 朝向筛选
    if search_params.orientation:
        query = query.where(House.orientation == search_params.orientation)
        count_query = count_query.where(House.orientation == search_params.orientation)

    # 排序
    sort_column = getattr(House, search_params.sort_by, House.created_at)
    if search_params.sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # 置顶优先
    query = query.order_by(House.is_top.desc(), House.is_recommended.desc())

    # 查询总数
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # 分页查询
    query = query.offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    houses = result.scalars().all()

    # 转换为响应格式
    house_list = []
    for house in houses:
        house_data = HouseResponse.model_validate(house)
        house_list.append(house_data.model_dump())

    return paginated_response(
        data=house_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{house_id}", response_model=HouseResponse)
async def get_house_detail(
    house_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """获取房源详情"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 增加浏览量
    house.view_count += 1
    await session.commit()
    await session.refresh(house)

    return HouseResponse.model_validate(house)


@router.put("/{house_id}", response_model=HouseResponse)
async def update_house(
    house_id: UUID,
    house_data: HouseUpdate,
    current_user: Annotated[User, Depends(get_current_landlord)],
    session: AsyncSession = Depends(get_async_session),
):
    """更新房源信息"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 权限检查：只有发布者或管理员可以编辑
    if house.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权编辑该房源",
        )

    # 更新字段
    update_data = house_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(house, key, value)

    await session.commit()
    await session.refresh(house)

    return HouseResponse.model_validate(house)


@router.delete("/{house_id}")
async def delete_house(
    house_id: UUID,
    current_user: Annotated[User, Depends(get_current_landlord)],
    session: AsyncSession = Depends(get_async_session),
):
    """删除房源（软删除，实际是下架）"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 权限检查
    if house.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除该房源",
        )

    # 软删除：设置为下架状态
    house.status = HouseStatus.OFF_SHELF
    await session.commit()

    return success_response(message="房源已下架")


@router.post("/{house_id}/images")
async def upload_house_images(
    house_id: UUID,
    images: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_landlord),
    session: AsyncSession = Depends(get_async_session),
):
    """上传房源图片"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 权限检查
    if house.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权编辑该房源",
        )

    # 获取当前最大排序
    from sqlalchemy import func

    count_result = await session.execute(
        select(func.count(HouseImage.id)).where(HouseImage.house_id == house_id)
    )
    current_count = count_result.scalar() or 0

    uploaded_images = []
    for i, image_file in enumerate(images):
        try:
            filename = await save_image(image_file)
            image_url = get_file_url(filename, file_type="image")

            # 如果是第一张且没有主图，设为主图
            is_main = current_count == 0 and i == 0 and not house.main_image

            house_image = HouseImage(
                house_id=house_id,
                image_url=image_url,
                sort_order=current_count + i,
                is_main=is_main,
            )
            session.add(house_image)
            uploaded_images.append(image_url)

            # 设置主图
            if is_main:
                house.main_image = image_url
        except Exception as e:
            continue

    await session.commit()

    return success_response(
        data={"uploaded_images": uploaded_images},
        message=f"成功上传 {len(uploaded_images)} 张图片",
    )


@router.get("/{house_id}/images", response_model=List[HouseImageResponse])
async def get_house_images(
    house_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """获取房源图片列表"""
    result = await session.execute(
        select(HouseImage)
        .where(HouseImage.house_id == house_id)
        .order_by(HouseImage.sort_order)
    )
    images = result.scalars().all()

    return [HouseImageResponse.model_validate(img) for img in images]


@router.post("/{house_id}/like")
async def toggle_like(
    house_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """点赞/取消点赞房源"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 检查是否已点赞
    result = await session.execute(
        select(Like).where(
            Like.user_id == current_user.id,
            Like.target_id == house_id,
            Like.target_type == TargetType.HOUSE,
        )
    )
    existing_like = result.scalar_one_or_none()

    if existing_like:
        # 取消点赞
        await session.delete(existing_like)
        is_liked = False
    else:
        # 添加点赞
        new_like = Like(
            user_id=current_user.id,
            target_id=house_id,
            target_type=TargetType.HOUSE,
        )
        session.add(new_like)
        is_liked = True

    await session.commit()

    return success_response(
        data={"is_liked": is_liked},
        message="已取消点赞" if not is_liked else "点赞成功",
    )


@router.get("/my")
async def get_my_houses(
    status: Optional[HouseStatus] = None,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """获取我发布的房源"""
    from sqlalchemy import func

    # 构建查询
    query = select(House).where(House.user_id == current_user.id)
    count_query = select(func.count(House.id)).where(House.user_id == current_user.id)

    if status:
        query = query.where(House.status == status)
        count_query = count_query.where(House.status == status)

    # 查询总数
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # 分页查询
    query = query.order_by(House.created_at.desc())
    query = query.offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    houses = result.scalars().all()

    house_list = []
    for house in houses:
        house_data = HouseResponse.model_validate(house)
        house_list.append(house_data.model_dump())

    return paginated_response(
        data=house_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/faqs")
async def get_faqs_public(
    session: AsyncSession = Depends(get_async_session),
):
    """获取常见问题列表（公共接口，无需登录）"""
    from sqlalchemy import select, func

    query = select(FAQ).where(FAQ.is_active == True).order_by(FAQ.sort_order.asc(), FAQ.created_at.desc())
    result = await session.execute(query)
    faqs = result.scalars().all()

    faq_list = []
    for faq in faqs:
        faq.view_count += 1
        faq_list.append(
            {
                "id": str(faq.id),
                "question": faq.question,
                "answer": faq.answer,
                "view_count": faq.view_count,
            }
        )

    await session.commit()

    return success_response(
        data=faq_list,
        message="获取成功",
    )
