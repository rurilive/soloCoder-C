"""数据模型模块"""

import enum
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import String, Text, Boolean, DateTime, Date, Integer, Numeric, Enum, ForeignKey, Table, Column, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.config.database import Base


# 枚举类型定义
class UserRole(str, enum.Enum):
    """用户角色"""
    USER = "user"
    LANDLORD = "landlord"
    AGENT = "agent"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


class HouseStatus(str, enum.Enum):
    """房源状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    LEASED = "leased"
    OFF_SHELF = "off_shelf"


class HouseType(str, enum.Enum):
    """房屋类型"""
    ENTIRE = "entire"
    SHARED = "shared"


class Orientation(str, enum.Enum):
    """朝向"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"


class Decoration(str, enum.Enum):
    """装修程度"""
    BARE = "bare"
    SIMPLE = "simple"
    FINE = "fine"
    LUXURY = "luxury"


class ImageType(str, enum.Enum):
    """图片类型"""
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    FLOOR_PLAN = "floor_plan"


class CommentStatus(str, enum.Enum):
    """评论状态"""
    ACTIVE = "active"
    HIDDEN = "hidden"
    DELETED = "deleted"


class QuestionStatus(str, enum.Enum):
    """问题状态"""
    OPEN = "open"
    CLOSED = "closed"


class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    SYSTEM = "system"


class AppointmentStatus(str, enum.Enum):
    """预约状态"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReportStatus(str, enum.Enum):
    """举报状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class TargetType(str, enum.Enum):
    """目标类型"""
    HOUSE = "house"
    COMMENT = "comment"
    QUESTION = "question"


class NotificationType(str, enum.Enum):
    """通知类型"""
    SYSTEM = "system"
    COMMENT = "comment"
    QUESTION = "question"
    MESSAGE = "message"
    APPOINTMENT = "appointment"
    PRICE_CHANGE = "price_change"


# 模型定义
class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    houses: Mapped[List["House"]] = relationship("House", back_populates="owner", cascade="all, delete-orphan")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="user", cascade="all, delete-orphan")
    answers: Mapped[List["Answer"]] = relationship("Answer", back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[List["Favorite"]] = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    favorite_folders: Mapped[List["FavoriteFolder"]] = relationship("FavoriteFolder", back_populates="user", cascade="all, delete-orphan")
    likes: Mapped[List["Like"]] = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    sent_messages: Mapped[List["Message"]] = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender", cascade="all, delete-orphan")
    received_messages: Mapped[List["Message"]] = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    appointments: Mapped[List["ViewingAppointment"]] = relationship("ViewingAppointment", foreign_keys="ViewingAppointment.user_id", back_populates="user", cascade="all, delete-orphan")
    landlord_appointments: Mapped[List["ViewingAppointment"]] = relationship("ViewingAppointment", foreign_keys="ViewingAppointment.landlord_id", back_populates="landlord", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship("Report", foreign_keys="Report.reporter_id", back_populates="reporter", cascade="all, delete-orphan")


class House(Base):
    """房源模型"""

    __tablename__ = "houses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    community: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    province: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, index=True)
    deposit_type: Mapped[str] = mapped_column(String(50), default="押一付三", nullable=False)
    house_type: Mapped[HouseType] = mapped_column(Enum(HouseType), default=HouseType.ENTIRE, nullable=False, index=True)
    room_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    area: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    orientation: Mapped[Optional[Orientation]] = mapped_column(Enum(Orientation), nullable=True)
    decoration: Mapped[Optional[Decoration]] = mapped_column(Enum(Decoration), nullable=True)
    facilities: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    surrounding: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    main_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[HouseStatus] = mapped_column(Enum(HouseStatus), default=HouseStatus.DRAFT, nullable=False, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    rent_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    min_rent_months: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    owner: Mapped["User"] = relationship("User", back_populates="houses")
    images: Mapped[List["HouseImage"]] = relationship("HouseImage", back_populates="house", cascade="all, delete-orphan")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="house", cascade="all, delete-orphan")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="house", cascade="all, delete-orphan")
    favorites: Mapped[List["Favorite"]] = relationship("Favorite", back_populates="house", cascade="all, delete-orphan")
    appointments: Mapped[List["ViewingAppointment"]] = relationship("ViewingAppointment", back_populates="house", cascade="all, delete-orphan")


class HouseImage(Base):
    """房源图片模型"""

    __tablename__ = "house_images"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    house_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("houses.id"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    image_type: Mapped[ImageType] = mapped_column(Enum(ImageType), default=ImageType.INTERIOR, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    house: Mapped["House"] = relationship("House", back_populates="images")


class Comment(Base):
    """评论模型"""

    __tablename__ = "comments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    house_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("houses.id"), nullable=False, index=True)
    parent_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("comments.id"), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[CommentStatus] = mapped_column(Enum(CommentStatus), default=CommentStatus.ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="comments")
    house: Mapped["House"] = relationship("House", back_populates="comments")
    parent: Mapped[Optional["Comment"]] = relationship("Comment", remote_side=[id], backref="replies")


class Question(Base):
    """问题模型"""

    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    house_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("houses.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(Enum(QuestionStatus), default=QuestionStatus.OPEN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="questions")
    house: Mapped["House"] = relationship("House", back_populates="questions")
    answers: Mapped[List["Answer"]] = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    """回答模型"""

    __tablename__ = "answers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("questions.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_best: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
    user: Mapped["User"] = relationship("User", back_populates="answers")


class FavoriteFolder(Base):
    """收藏夹模型"""

    __tablename__ = "favorite_folders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="favorite_folders")
    favorites: Mapped[List["Favorite"]] = relationship("Favorite", back_populates="folder")


class Favorite(Base):
    """收藏模型"""

    __tablename__ = "favorites"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    house_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("houses.id"), nullable=False, index=True)
    folder_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("favorite_folders.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="favorites")
    house: Mapped["House"] = relationship("House", back_populates="favorites")
    folder: Mapped[Optional["FavoriteFolder"]] = relationship("FavoriteFolder", back_populates="favorites")


class Like(Base):
    """点赞模型"""

    __tablename__ = "likes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    target_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="likes")


class Message(Base):
    """消息模型"""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    sender_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    house_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("houses.id"), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.TEXT, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver: Mapped["User"] = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


class Notification(Base):
    """通知模型"""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    target_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    target_type: Mapped[Optional[TargetType]] = mapped_column(Enum(TargetType), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="notifications")


class ViewingAppointment(Base):
    """预约看房模型"""

    __tablename__ = "viewing_appointments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    house_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("houses.id"), nullable=False, index=True)
    landlord_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    viewing_date: Mapped[date] = mapped_column(Date, nullable=False)
    viewing_time: Mapped[str] = mapped_column(String(20), nullable=False)
    visitor_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING, nullable=False, index=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="appointments")
    house: Mapped["House"] = relationship("House", back_populates="appointments")
    landlord: Mapped["User"] = relationship("User", foreign_keys=[landlord_id], back_populates="landlord_appointments")


class Report(Base):
    """举报模型"""

    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    reporter_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    target_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType), nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False, index=True)
    handler_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    handle_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id], back_populates="reports")


class FAQ(Base):
    """常见问题模型"""

    __tablename__ = "faqs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


__all__ = [
    "User", "House", "HouseImage", "Comment", "Question", "Answer",
    "Favorite", "FavoriteFolder", "Like", "Message", "Notification",
    "ViewingAppointment", "Report", "FAQ",
    "UserRole", "UserStatus", "HouseStatus", "HouseType", "Orientation",
    "Decoration", "ImageType", "CommentStatus", "QuestionStatus",
    "MessageType", "AppointmentStatus", "ReportStatus", "TargetType",
    "NotificationType",
]
