"""评论和问答路由"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from uuid import UUID

from app.config.database import get_async_session
from app.models import (
    User, House, Comment, Question, Answer,
    CommentStatus, QuestionStatus, TargetType, Like,
)
from app.schemas.common import PaginatedParams, IDResponse, MessageResponse
from app.routers.auth import get_current_active_user, get_current_landlord
from app.utils.response import success_response, error_response, paginated_response

router = APIRouter(prefix="/api/comments", tags=["评论"])


# ==================== 评论相关 ====================

@router.post("/house/{house_id}")
async def create_comment(
    house_id: UUID,
    content: str = Form(...),
    rating: Optional[int] = Form(default=None),
    parent_id: Optional[UUID] = Form(default=None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """发布评论或回复"""
    # 检查房源是否存在
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 检查父评论是否存在
    if parent_id:
        result = await session.execute(select(Comment).where(Comment.id == parent_id))
        parent_comment = result.scalar_one_or_none()
        if not parent_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="父评论不存在",
            )

    # 验证评分
    if rating is not None and (rating < 1 or rating > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="评分必须在1-5之间",
        )

    # 创建评论
    new_comment = Comment(
        user_id=current_user.id,
        house_id=house_id,
        parent_id=parent_id,
        content=content,
        rating=rating,
        status=CommentStatus.ACTIVE,
    )

    session.add(new_comment)
    await session.commit()
    await session.refresh(new_comment)

    return IDResponse(id=new_comment.id, message="评论发布成功")


@router.get("/house/{house_id}")
async def get_house_comments(
    house_id: UUID,
    pagination: PaginatedParams = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    """获取房源评论列表"""
    from sqlalchemy.orm import selectinload

    # 查询总数
    count_result = await session.execute(
        select(func.count(Comment.id))
        .where(
            Comment.house_id == house_id,
            Comment.parent_id.is_(None),
            Comment.status == CommentStatus.ACTIVE,
        )
    )
    total = count_result.scalar() or 0

    # 查询评论（只查一级评论，不包含回复）
    result = await session.execute(
        select(Comment, User)
        .join(User, Comment.user_id == User.id)
        .where(
            Comment.house_id == house_id,
            Comment.parent_id.is_(None),
            Comment.status == CommentStatus.ACTIVE,
        )
        .order_by(Comment.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.fetchall()

    comments = []
    for comment, user in rows:
        # 查询回复
        reply_result = await session.execute(
            select(Comment, User)
            .join(User, Comment.user_id == User.id)
            .where(
                Comment.parent_id == comment.id,
                Comment.status == CommentStatus.ACTIVE,
            )
            .order_by(Comment.created_at.asc())
        )
        reply_rows = reply_result.fetchall()

        replies = []
        for reply, reply_user in reply_rows:
            replies.append(
                {
                    "id": str(reply.id),
                    "content": reply.content,
                    "like_count": reply.like_count,
                    "created_at": reply.created_at.isoformat(),
                    "user": {
                        "id": str(reply_user.id),
                        "nickname": reply_user.nickname or reply_user.username,
                        "avatar": reply_user.avatar,
                    },
                }
            )

        comments.append(
            {
                "id": str(comment.id),
                "content": comment.content,
                "rating": comment.rating,
                "like_count": comment.like_count,
                "created_at": comment.created_at.isoformat(),
                "user": {
                    "id": str(user.id),
                    "nickname": user.nickname or user.username,
                    "avatar": user.avatar,
                },
                "replies": replies,
            }
        )

    return paginated_response(
        data=comments,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """删除评论（软删除）"""
    result = await session.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    # 权限检查：只有评论者或管理员可以删除
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除该评论",
        )

    comment.status = CommentStatus.DELETED
    await session.commit()

    return success_response(message="评论已删除")


@router.post("/{comment_id}/like")
async def toggle_comment_like(
    comment_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """点赞/取消点赞评论"""
    result = await session.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    # 检查是否已点赞
    result = await session.execute(
        select(Like).where(
            Like.user_id == current_user.id,
            Like.target_id == comment_id,
            Like.target_type == TargetType.COMMENT,
        )
    )
    existing_like = result.scalar_one_or_none()

    if existing_like:
        # 取消点赞
        await session.delete(existing_like)
        if comment.like_count > 0:
            comment.like_count -= 1
        is_liked = False
    else:
        # 添加点赞
        new_like = Like(
            user_id=current_user.id,
            target_id=comment_id,
            target_type=TargetType.COMMENT,
        )
        session.add(new_like)
        comment.like_count += 1
        is_liked = True

    await session.commit()

    return success_response(
        data={"is_liked": is_liked, "like_count": comment.like_count},
        message="已取消点赞" if not is_liked else "点赞成功",
    )


# ==================== 问答相关 ====================

@router.post("/questions/house/{house_id}")
async def create_question(
    house_id: UUID,
    content: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """发布问题"""
    # 检查房源是否存在
    result = await session.execute(select(House).where(House.id == house_id))
    house = result.scalar_one_or_none()

    if not house:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="房源不存在",
        )

    # 创建问题
    new_question = Question(
        user_id=current_user.id,
        house_id=house_id,
        content=content,
        status=QuestionStatus.OPEN,
    )

    session.add(new_question)
    await session.commit()
    await session.refresh(new_question)

    return IDResponse(id=new_question.id, message="问题发布成功")


@router.get("/questions/house/{house_id}")
async def get_house_questions(
    house_id: UUID,
    pagination: PaginatedParams = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    """获取房源问题列表"""
    # 查询总数
    count_result = await session.execute(
        select(func.count(Question.id)).where(Question.house_id == house_id)
    )
    total = count_result.scalar() or 0

    # 查询问题列表
    result = await session.execute(
        select(Question, User)
        .join(User, Question.user_id == User.id)
        .where(Question.house_id == house_id)
        .order_by(Question.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.fetchall()

    questions = []
    for question, user in rows:
        # 查询回答
        answer_result = await session.execute(
            select(Answer, User)
            .join(User, Answer.user_id == User.id)
            .where(Answer.question_id == question.id)
            .order_by(Answer.created_at.asc())
        )
        answer_rows = answer_result.fetchall()

        answers = []
        for answer, answer_user in answer_rows:
            answers.append(
                {
                    "id": str(answer.id),
                    "content": answer.content,
                    "is_best": answer.is_best,
                    "like_count": answer.like_count,
                    "created_at": answer.created_at.isoformat(),
                    "user": {
                        "id": str(answer_user.id),
                        "nickname": answer_user.nickname or answer_user.username,
                        "avatar": answer_user.avatar,
                    },
                }
            )

        questions.append(
            {
                "id": str(question.id),
                "content": question.content,
                "like_count": question.like_count,
                "view_count": question.view_count,
                "status": question.status.value if question.status else None,
                "created_at": question.created_at.isoformat(),
                "user": {
                    "id": str(user.id),
                    "nickname": user.nickname or user.username,
                    "avatar": user.avatar,
                },
                "answers": answers,
            }
        )

    return paginated_response(
        data=questions,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/questions/{question_id}/answers")
async def create_answer(
    question_id: UUID,
    content: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """回答问题"""
    # 检查问题是否存在
    result = await session.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问题不存在",
        )

    # 创建回答
    new_answer = Answer(
        question_id=question_id,
        user_id=current_user.id,
        content=content,
    )

    session.add(new_answer)
    await session.commit()
    await session.refresh(new_answer)

    return IDResponse(id=new_answer.id, message="回答发布成功")


@router.get("/questions/my")
async def get_my_questions(
    pagination: PaginatedParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """获取我的问题"""
    # 查询总数
    count_result = await session.execute(
        select(func.count(Question.id)).where(Question.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # 查询问题列表
    result = await session.execute(
        select(Question, House)
        .join(House, Question.house_id == House.id)
        .where(Question.user_id == current_user.id)
        .order_by(Question.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.fetchall()

    questions = []
    for question, house in rows:
        questions.append(
            {
                "id": str(question.id),
                "content": question.content,
                "like_count": question.like_count,
                "view_count": question.view_count,
                "status": question.status.value if question.status else None,
                "created_at": question.created_at.isoformat(),
                "house": {
                    "id": str(house.id),
                    "title": house.title,
                    "main_image": house.main_image,
                    "price": float(house.price),
                },
            }
        )

    return paginated_response(
        data=questions,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/questions/{question_id}/like")
async def toggle_question_like(
    question_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: AsyncSession = Depends(get_async_session),
):
    """点赞/取消点赞问题"""
    result = await session.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问题不存在",
        )

    # 检查是否已点赞
    result = await session.execute(
        select(Like).where(
            Like.user_id == current_user.id,
            Like.target_id == question_id,
            Like.target_type == TargetType.QUESTION,
        )
    )
    existing_like = result.scalar_one_or_none()

    if existing_like:
        await session.delete(existing_like)
        if question.like_count > 0:
            question.like_count -= 1
        is_liked = False
    else:
        new_like = Like(
            user_id=current_user.id,
            target_id=question_id,
            target_type=TargetType.QUESTION,
        )
        session.add(new_like)
        question.like_count += 1
        is_liked = True

    await session.commit()

    return success_response(
        data={"is_liked": is_liked, "like_count": question.like_count},
        message="已取消点赞" if not is_liked else "点赞成功",
    )
