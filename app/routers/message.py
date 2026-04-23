"""消息和通知路由"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, distinct
from uuid import UUID
from datetime import datetime

from app.config.database import get_async_session
from app.models import (
    User, House, Message, MessageType, Notification, NotificationType,
)
from app.schemas.common import PaginatedParams, IDResponse
from app.routers.auth import get_current_active_user
from app.utils.response import success_response, paginated_response

router = APIRouter(prefix="/api/messages", tags=["消息"])


# ==================== 私信相关 ====================

@router.post("/send")
async def send_message(
    receiver_id: UUID = Form(...),
    house_id: Optional[UUID] = Form(default=None),
    content: str = Form(...),
    message_type: MessageType = Form(default=MessageType.TEXT),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """发送私信"""
    # 检查接收者是否存在
    result = await session.execute(select(User).where(User.id == receiver_id))
    receiver = result.scalar_one_or_none()

    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="接收者不存在",
        )

    # 不能给自己发消息
    if receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能给自己发送消息",
        )

    # 检查房源是否存在（如果指定了）
    if house_id:
        result = await session.execute(select(House).where(House.id == house_id))
        house = result.scalar_one_or_none()
        if not house:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="房源不存在",
            )

    # 创建消息
    new_message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        house_id=house_id,
        content=content,
        message_type=message_type,
    )

    session.add(new_message)
    await session.commit()
    await session.refresh(new_message)

    # 创建通知
    notification = Notification(
        user_id=receiver_id,
        title="新消息",
        content=f"{current_user.nickname or current_user.username} 给您发送了一条消息",
        notification_type=NotificationType.MESSAGE,
        target_id=new_message.id,
    )
    session.add(notification)
    await session.commit()

    return IDResponse(id=new_message.id, message="消息发送成功")


@router.get("/conversations")
async def get_conversations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """获取会话列表"""
    # 查询所有与当前用户相关的消息的对方用户
    result = await session.execute(
        select(distinct(Message.sender_id)).where(Message.receiver_id == current_user.id)
    )
    sender_ids = [row[0] for row in result.fetchall()]

    result = await session.execute(
        select(distinct(Message.receiver_id)).where(Message.sender_id == current_user.id)
    )
    receiver_ids = [row[0] for row in result.fetchall()]

    # 合并所有对话用户
    all_user_ids = list(set(sender_ids + receiver_ids))

    conversations = []
    for user_id in all_user_ids:
        # 获取用户信息
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            continue

        # 获取最后一条消息
        result = await session.execute(
            select(Message)
            .where(
                or_(
                    and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                    and_(Message.sender_id == user_id, Message.receiver_id == current_user.id),
                )
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = result.scalar_one_or_none()

        # 获取未读消息数
        count_result = await session.execute(
            select(func.count(Message.id)).where(
                Message.sender_id == user_id,
                Message.receiver_id == current_user.id,
                Message.is_read == False,
            )
        )
        unread_count = count_result.scalar() or 0

        conversations.append(
            {
                "user_id": str(user_id),
                "nickname": user.nickname or user.username,
                "avatar": user.avatar,
                "last_message": {
                    "content": last_message.content if last_message else None,
                    "created_at": last_message.created_at.isoformat() if last_message else None,
                    "is_sender": last_message.sender_id == current_user.id if last_message else None,
                } if last_message else None,
                "unread_count": unread_count,
            }
        )

    # 按最后消息时间排序
    conversations.sort(
        key=lambda x: (
            x["last_message"]["created_at"] if x["last_message"] and x["last_message"]["created_at"] else "0"
        ),
        reverse=True,
    )

    return success_response(data=conversations)


@router.get("/conversation/{user_id}")
async def get_conversation_with(
    user_id: UUID,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """获取与指定用户的对话记录"""
    # 查询总数
    count_result = await session.execute(
        select(func.count(Message.id)).where(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user.id),
            )
        )
    )
    total = count_result.scalar() or 0

    # 查询消息列表（按时间倒序，最新的在前面）
    result = await session.execute(
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user.id),
            )
        )
        .order_by(Message.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    messages = result.scalars().all()

    # 将未读消息标记为已读
    await session.execute(
        select(Message).where(
            Message.sender_id == user_id,
            Message.receiver_id == current_user.id,
            Message.is_read == False,
        )
    )
    unread_messages = result.scalars().all()
    for msg in unread_messages:
        msg.is_read = True
        msg.read_at = datetime.utcnow()

    await session.commit()

    # 转换为响应格式（反转顺序，最新的在下面）
    message_list = []
    for msg in reversed(list(messages)):
        message_list.append(
            {
                "id": str(msg.id),
                "content": msg.content,
                "message_type": msg.message_type.value if msg.message_type else None,
                "house_id": str(msg.house_id) if msg.house_id else None,
                "is_sender": msg.sender_id == current_user.id,
                "is_read": msg.is_read,
                "created_at": msg.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=message_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """获取未读消息数"""
    # 未读私信数
    message_count_result = await session.execute(
        select(func.count(Message.id)).where(
            Message.receiver_id == current_user.id,
            Message.is_read == False,
        )
    )
    message_count = message_count_result.scalar() or 0

    # 未读通知数
    notification_count_result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    notification_count = notification_count_result.scalar() or 0

    return success_response(
        data={
            "message_count": message_count,
            "notification_count": notification_count,
            "total": message_count + notification_count,
        }
    )


# ==================== 通知相关 ====================

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """获取通知列表"""
    # 构建查询条件
    query = select(Notification).where(Notification.user_id == current_user.id)
    count_query = select(func.count(Notification.id)).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)
        count_query = count_query.where(Notification.is_read == False)

    # 查询总数
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # 查询通知列表
    query = query.order_by(Notification.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(query)
    notifications = result.scalars().all()

    notification_list = []
    for notification in notifications:
        notification_list.append(
            {
                "id": str(notification.id),
                "title": notification.title,
                "content": notification.content,
                "notification_type": notification.notification_type.value if notification.notification_type else None,
                "target_id": str(notification.target_id) if notification.target_id else None,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }
        )

    return paginated_response(
        data=notification_list,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """标记通知为已读"""
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在",
        )

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await session.commit()

    return success_response(message="已标记为已读")


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """标记所有通知为已读"""
    from sqlalchemy import update

    await session.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await session.commit()

    return success_response(message="所有通知已标记为已读")
