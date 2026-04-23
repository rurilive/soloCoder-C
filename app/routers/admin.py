"""管理后台路由"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from uuid import UUID
from datetime import datetime

from app.config.database import get_async_session
from app.models import (
    User, House, HouseStatus, UserRole, UserStatus,
    Comment, CommentStatus, Question, QuestionStatus,
    Report, ReportStatus, FAQ,
)
from app.schemas.common import PaginatedParams
from app.routers.auth import get_current_admin
from app.utils.response import success_response, paginated_response

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/users")
async def get_users(
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    keyword: Optional[str] = None,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """获取用户列表"""
    query = select(User)
    count_query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if status:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)

    if keyword:
        keyword_pattern = f"%{keyword}%"
        query = query.where(
            User.username.ilike(keyword_pattern)
            | User.phone.ilike(keyword_pattern)
            | User.email.ilike(keyword_pattern)
            | User.nickname.ilike(keyword_pattern)
        )
        count_query = count_query.where(
            User.username.ilike(keyword_pattern)
            | User.phone.ilike(keyword_pattern)
            | User.email.ilike(keyword_pattern)
            | User.nickname.ilike(keyword_pattern)
        )

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(User.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    users = result.scalars().all()

    user_list = []
    for user in users:
        user_list.append(
            {
                "id": str(user.id),
                "username": user.username,
                "nickname": user.nickname,
                "phone": user.phone,
                "email": user.email,
                "avatar": user.avatar,
                "role": user.role.value if user.role else None,
                "status": user.status.value if user.status else None,
                "is_verified": user.is_verified,
                "credit_score": user.credit_score,
                "created_at": user.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=user_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    status: UserStatus = Form(...),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """更新用户状态"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的状态",
        )

    user.status = status
    await session.commit()

    return success_response(message="用户状态已更新")


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role: UserRole = Form(...),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """更新用户角色"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的角色",
        )

    user.role = role
    await session.commit()

    return success_response(message="用户角色已更新")


@router.get("/houses")
async def get_houses_admin(
    status: Optional[HouseStatus] = None,
    city: Optional[str] = None,
    keyword: Optional[str] = None,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """获取房源列表（管理后台）"""
    from sqlalchemy.orm import selectinload

    query = select(House)
    count_query = select(func.count(House.id))

    if status:
        query = query.where(House.status == status)
        count_query = count_query.where(House.status == status)

    if city:
        query = query.where(House.city == city)
        count_query = count_query.where(House.city == city)

    if keyword:
        keyword_pattern = f"%{keyword}%"
        query = query.where(
            House.title.ilike(keyword_pattern)
            | House.community.ilike(keyword_pattern)
            | House.address.ilike(keyword_pattern)
        )
        count_query = count_query.where(
            House.title.ilike(keyword_pattern)
            | House.community.ilike(keyword_pattern)
            | House.address.ilike(keyword_pattern)
        )

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(House.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    houses = result.scalars().all()

    house_list = []
    for house in houses:
        result = await session.execute(select(User).where(User.id == house.user_id))
        owner = result.scalar_one_or_none()

        house_list.append(
            {
                "id": str(house.id),
                "title": house.title,
                "community": house.community,
                "address": house.address,
                "city": house.city,
                "district": house.district,
                "price": float(house.price),
                "house_type": house.house_type.value if house.house_type else None,
                "room_type": house.room_type,
                "main_image": house.main_image,
                "status": house.status.value if house.status else None,
                "view_count": house.view_count,
                "favorite_count": house.favorite_count,
                "is_top": house.is_top,
                "is_recommended": house.is_recommended,
                "owner": {
                    "id": str(owner.id) if owner else None,
                    "username": owner.username if owner else None,
                    "nickname": owner.nickname if owner else None,
                } if owner else None,
                "created_at": house.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=house_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.put("/houses/{house_id}/status")
async def update_house_status(
    house_id: UUID,
    status: HouseStatus = Form(...),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """更新房源状态"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    house.status = status
    await session.commit()

    return success_response(message="房源状态已更新")


@router.put("/houses/{house_id}/recommend")
async def update_house_recommend(
    house_id: UUID,
    is_recommended: bool = Form(...),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """设置/取消推荐房源"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    house.is_recommended = is_recommended
    await session.commit()

    return success_response(
        message="已推荐" if is_recommended else "已取消推荐"
    )


@router.put("/houses/{house_id}/top")
async def update_house_top(
    house_id: UUID,
    is_top: bool = Form(...),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """设置/取消置顶房源"""
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    house.is_top = is_top
    await session.commit()

    return success_response(
        message="已置顶" if is_top else "已取消置顶"
    )


@router.get("/comments")
async def get_comments_admin(
    status: Optional[CommentStatus] = None,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """获取评论列表（管理后台）"""
    query = select(Comment)
    count_query = select(func.count(Comment.id))

    if status:
        query = query.where(Comment.status == status)
        count_query = count_query.where(Comment.status == status)

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(Comment.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    comments = result.scalars().all()

    comment_list = []
    for comment in comments:
        result = await session.execute(select(User).where(User.id == comment.user_id))
        user = result.scalar_one_or_none()

        result = await session.execute(select(House).where(House.id == comment.house_id))
        house = result.scalar_one_or_none()

        comment_list.append(
            {
                "id": str(comment.id),
                "content": comment.content,
                "rating": comment.rating,
                "like_count": comment.like_count,
                "status": comment.status.value if comment.status else None,
                "user": {
                    "id": str(user.id) if user else None,
                    "username": user.username if user else None,
                } if user else None,
                "house": {
                    "id": str(house.id) if house else None,
                    "title": house.title if house else None,
                } if house else None,
                "created_at": comment.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=comment_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.put("/comments/{comment_id}/status")
async def update_comment_status(
    comment_id: UUID,
    status: CommentStatus = Form(...),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """更新评论状态"""
    result = await session.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    comment.status = status
    await session.commit()

    return success_response(message="评论状态已更新")


@router.get("/reports")
async def get_reports(
    status: Optional[ReportStatus] = None,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """获取举报列表"""
    query = select(Report)
    count_query = select(func.count(Report.id))

    if status:
        query = query.where(Report.status == status)
        count_query = count_query.where(Report.status == status)

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(Report.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    reports = result.scalars().all()

    report_list = []
    for report in reports:
        result = await session.execute(select(User).where(User.id == report.reporter_id))
        reporter = result.scalar_one_or_none()

        report_list.append(
            {
                "id": str(report.id),
                "reason": report.reason,
                "description": report.description,
                "target_type": report.target_type.value if report.target_type else None,
                "target_id": str(report.target_id),
                "status": report.status.value if report.status else None,
                "reporter": {
                    "id": str(reporter.id) if reporter else None,
                    "username": reporter.username if reporter else None,
                } if reporter else None,
                "created_at": report.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=report_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.put("/reports/{report_id}/handle")
async def handle_report(
    report_id: UUID,
    status: ReportStatus = Form(...),
    handle_note: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """处理举报"""
    result = await session.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报不存在",
        )

    report.status = status
    report.handler_id = current_user.id
    report.handle_note = handle_note
    report.handled_at = datetime.utcnow()

    await session.commit()

    return success_response(message="举报已处理")


@router.get("/statistics")
async def get_statistics(
    current_user: Annotated[User, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """获取统计数据"""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    user_count_result = await session.execute(select(func.count(User.id)))
    total_users = user_count_result.scalar() or 0

    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    today_user_result = await session.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    today_new_users = today_user_result.scalar() or 0

    house_count_result = await session.execute(
        select(func.count(House.id)).where(House.status == HouseStatus.PUBLISHED)
    )
    total_houses = house_count_result.scalar() or 0

    leased_house_result = await session.execute(
        select(func.count(House.id)).where(House.status == HouseStatus.LEASED)
    )
    leased_houses = leased_house_result.scalar() or 0

    today_house_result = await session.execute(
        select(func.count(House.id)).where(House.created_at >= today_start)
    )
    today_new_houses = today_house_result.scalar() or 0

    role_stats_result = await session.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    role_stats = role_stats_result.fetchall()
    role_distribution = {}
    for role, count in role_stats:
        role_distribution[role.value if role else "unknown"] = count

    city_stats_result = await session.execute(
        select(House.city, func.count(House.id))
        .where(House.status == HouseStatus.PUBLISHED, House.city.isnot(None))
        .group_by(House.city)
        .order_by(func.count(House.id).desc())
        .limit(10)
    )
    city_stats = city_stats_result.fetchall()
    city_distribution = []
    for city, count in city_stats:
        city_distribution.append({"city": city, "count": count})

    return success_response(
        data={
            "users": {
                "total": total_users,
                "today_new": today_new_users,
                "role_distribution": role_distribution,
            },
            "houses": {
                "total_published": total_houses,
                "total_leased": leased_houses,
                "today_new": today_new_houses,
                "city_distribution": city_distribution,
            },
        }
    )


@router.get("/faqs")
async def get_faqs_admin(
    is_active: Optional[bool] = None,
    keyword: Optional[str] = None,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """获取常见问题列表（管理后台）"""
    query = select(FAQ)
    count_query = select(func.count(FAQ.id))

    if is_active is not None:
        query = query.where(FAQ.is_active == is_active)
        count_query = count_query.where(FAQ.is_active == is_active)

    if keyword:
        keyword_pattern = f"%{keyword}%"
        query = query.where(
            FAQ.question.ilike(keyword_pattern)
            | FAQ.answer.ilike(keyword_pattern)
        )
        count_query = count_query.where(
            FAQ.question.ilike(keyword_pattern)
            | FAQ.answer.ilike(keyword_pattern)
        )

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(FAQ.sort_order.asc(), FAQ.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    faqs = result.scalars().all()

    faq_list = []
    for faq in faqs:
        faq_list.append(
            {
                "id": str(faq.id),
                "question": faq.question,
                "answer": faq.answer,
                "sort_order": faq.sort_order,
                "is_active": faq.is_active,
                "view_count": faq.view_count,
                "created_at": faq.created_at.isoformat(),
                "updated_at": faq.updated_at.isoformat(),
            }
        )

    return paginated_response(
        data=faq_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/faqs")
async def create_faq(
    question: str = Form(...),
    answer: str = Form(...),
    sort_order: int = Form(default=0),
    is_active: bool = Form(default=True),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """创建常见问题"""
    new_faq = FAQ(
        question=question,
        answer=answer,
        sort_order=sort_order,
        is_active=is_active,
    )

    session.add(new_faq)
    await session.commit()
    await session.refresh(new_faq)

    return success_response(
        data={
            "id": str(new_faq.id),
            "question": new_faq.question,
            "answer": new_faq.answer,
            "sort_order": new_faq.sort_order,
            "is_active": new_faq.is_active,
        },
        message="常见问题创建成功",
    )


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: UUID,
    question: Optional[str] = Form(default=None),
    answer: Optional[str] = Form(default=None),
    sort_order: Optional[int] = Form(default=None),
    is_active: Optional[bool] = Form(default=None),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """更新常见问题"""
    result = await session.execute(select(FAQ).where(FAQ.id == faq_id))
    faq = result.scalar_one_or_none()

    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="常见问题不存在",
        )

    if question is not None:
        faq.question = question
    if answer is not None:
        faq.answer = answer
    if sort_order is not None:
        faq.sort_order = sort_order
    if is_active is not None:
        faq.is_active = is_active

    await session.commit()
    await session.refresh(faq)

    return success_response(
        data={
            "id": str(faq.id),
            "question": faq.question,
            "answer": faq.answer,
            "sort_order": faq.sort_order,
            "is_active": faq.is_active,
        },
        message="常见问题更新成功",
    )


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: UUID,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session),
):
    """删除常见问题"""
    result = await session.execute(select(FAQ).where(FAQ.id == faq_id))
    faq = result.scalar_one_or_none()

    if not faq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="常见问题不存在",
        )

    await session.delete(faq)
    await session.commit()

    return success_response(message="常见问题删除成功")
