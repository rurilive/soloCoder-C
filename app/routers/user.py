"""用户路由"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID

from app.config.database import get_async_session
from app.models import User, UserRole, UserStatus, Favorite, FavoriteFolder, House
from app.schemas.user import UserUpdate, UserResponse
from app.schemas.common import MessageResponse, PaginatedParams
from app.routers.auth import get_current_active_user
from app.utils.security import get_password_hash
from app.utils.response import success_response, error_response, paginated_response
from app.utils.file_handler import save_image, get_file_url

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """获取用户个人资料"""
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """更新用户个人资料"""
    # 检查手机号是否已被其他用户使用
    if user_data.phone and user_data.phone != current_user.phone:
        result = await session.execute(
            select(User).where(User.phone == user_data.phone, User.id != current_user.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被使用",
            )

    # 检查邮箱是否已被其他用户使用
    if user_data.email and user_data.email != current_user.email:
        result = await session.execute(
            select(User).where(User.email == user_data.email, User.id != current_user.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用",
            )

    # 更新用户信息
    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    await session.commit()
    await session.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post("/avatar")
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """更新用户头像"""
    try:
        filename = await save_image(file)
        avatar_url = get_file_url(filename, file_type="avatar")

        current_user.avatar = avatar_url
        await session.commit()

        return success_response(
            data={"avatar_url": avatar_url},
            message="头像更新成功",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"头像上传失败: {str(e)}",
        )


@router.post("/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """修改密码"""
    from app.utils.security import verify_password

    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码长度至少6位",
        )

    current_user.password_hash = get_password_hash(new_password)
    await session.commit()

    return success_response(message="密码修改成功")


@router.post("/become-landlord")
async def become_landlord(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """申请成为房东"""
    if current_user.role in [UserRole.LANDLORD, UserRole.AGENT, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经是房东/业务员",
        )

    current_user.role = UserRole.LANDLORD
    await session.commit()

    return success_response(message="已成功升级为房东")


# 收藏相关功能
@router.get("/favorites")
async def get_favorites(
    pagination: Annotated[PaginatedParams, Depends()],
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """获取用户收藏列表"""
    # 查询收藏总数
    from sqlalchemy import func

    count_result = await session.execute(
        select(func.count(Favorite.id)).where(Favorite.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # 查询收藏列表
    result = await session.execute(
        select(Favorite, House)
        .join(House, Favorite.house_id == House.id)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.fetchall()

    favorites = []
    for favorite, house in rows:
        favorites.append(
            {
                "id": str(favorite.id),
                "house_id": str(house.id),
                "title": house.title,
                "community": house.community,
                "price": float(house.price),
                "main_image": house.main_image,
                "house_type": house.house_type.value if house.house_type else None,
                "room_type": house.room_type,
                "area": float(house.area) if house.area else None,
                "created_at": favorite.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=favorites,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/favorites/{house_id}")
async def add_favorite(
    house_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """添加收藏"""
    # 检查房源是否存在
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 检查是否已收藏
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.house_id == house_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已收藏该房源",
        )

    # 添加收藏
    favorite = Favorite(
        user_id=current_user.id,
        house_id=house_id,
    )

    session.add(favorite)

    # 更新房源收藏数
    house.favorite_count += 1

    await session.commit()

    return success_response(message="收藏成功")


@router.delete("/favorites/{house_id}")
async def remove_favorite(
    house_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """取消收藏"""
    # 检查收藏是否存在
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.house_id == house_id)
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未收藏该房源",
        )

    # 删除收藏
    await session.delete(favorite)

    # 更新房源收藏数
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()
    if house and house.favorite_count > 0:
        house.favorite_count -= 1

    await session.commit()

    return success_response(message="已取消收藏")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """根据ID获取用户公开信息"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 只返回公开信息
    return UserResponse.model_validate(user)
