"""数据模型测试

测试 app/models/__init__.py 中的数据模型和枚举类型。
"""

import pytest
from uuid import uuid4


class TestEnumTypes:
    """测试枚举类型"""

    def test_user_role_enum(self):
        """测试用户角色枚举"""
        from app.models import UserRole

        assert UserRole.USER.value == "user"
        assert UserRole.LANDLORD.value == "landlord"
        assert UserRole.AGENT.value == "agent"
        assert UserRole.ADMIN.value == "admin"

        assert UserRole("user") == UserRole.USER
        assert UserRole("landlord") == UserRole.LANDLORD

    def test_user_status_enum(self):
        """测试用户状态枚举"""
        from app.models import UserStatus

        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.BANNED.value == "banned"

    def test_house_status_enum(self):
        """测试房源状态枚举"""
        from app.models import HouseStatus

        assert HouseStatus.DRAFT.value == "draft"
        assert HouseStatus.PUBLISHED.value == "published"
        assert HouseStatus.LEASED.value == "leased"
        assert HouseStatus.OFF_SHELF.value == "off_shelf"

    def test_house_type_enum(self):
        """测试房源类型枚举"""
        from app.models import HouseType

        assert HouseType.ENTIRE.value == "entire"
        assert HouseType.SHARED.value == "shared"

    def test_orientation_enum(self):
        """测试朝向枚举"""
        from app.models import Orientation

        assert Orientation.NORTH.value == "north"
        assert Orientation.SOUTH.value == "south"
        assert Orientation.EAST.value == "east"
        assert Orientation.WEST.value == "west"
        assert Orientation.SOUTHEAST.value == "southeast"
        assert Orientation.SOUTHWEST.value == "southwest"
        assert Orientation.NORTHEAST.value == "northeast"
        assert Orientation.NORTHWEST.value == "northwest"

    def test_decoration_enum(self):
        """测试装修程度枚举"""
        from app.models import Decoration

        assert Decoration.BARE.value == "bare"
        assert Decoration.SIMPLE.value == "simple"
        assert Decoration.FINE.value == "fine"
        assert Decoration.LUXURY.value == "luxury"

    def test_image_type_enum(self):
        """测试图片类型枚举"""
        from app.models import ImageType

        assert ImageType.INTERIOR.value == "interior"
        assert ImageType.EXTERIOR.value == "exterior"
        assert ImageType.FLOOR_PLAN.value == "floor_plan"

    def test_comment_status_enum(self):
        """测试评论状态枚举"""
        from app.models import CommentStatus

        assert CommentStatus.ACTIVE.value == "active"
        assert CommentStatus.HIDDEN.value == "hidden"
        assert CommentStatus.DELETED.value == "deleted"

    def test_question_status_enum(self):
        """测试问题状态枚举"""
        from app.models import QuestionStatus

        assert QuestionStatus.OPEN.value == "open"
        assert QuestionStatus.CLOSED.value == "closed"

    def test_message_type_enum(self):
        """测试消息类型枚举"""
        from app.models import MessageType

        assert MessageType.TEXT.value == "text"
        assert MessageType.IMAGE.value == "image"
        assert MessageType.SYSTEM.value == "system"

    def test_appointment_status_enum(self):
        """测试预约状态枚举"""
        from app.models import AppointmentStatus

        assert AppointmentStatus.PENDING.value == "pending"
        assert AppointmentStatus.CONFIRMED.value == "confirmed"
        assert AppointmentStatus.COMPLETED.value == "completed"
        assert AppointmentStatus.CANCELLED.value == "cancelled"

    def test_report_status_enum(self):
        """测试举报状态枚举"""
        from app.models import ReportStatus

        assert ReportStatus.PENDING.value == "pending"
        assert ReportStatus.PROCESSING.value == "processing"
        assert ReportStatus.RESOLVED.value == "resolved"
        assert ReportStatus.DISMISSED.value == "dismissed"

    def test_target_type_enum(self):
        """测试目标类型枚举"""
        from app.models import TargetType

        assert TargetType.HOUSE.value == "house"
        assert TargetType.COMMENT.value == "comment"
        assert TargetType.QUESTION.value == "question"

    def test_notification_type_enum(self):
        """测试通知类型枚举"""
        from app.models import NotificationType

        assert NotificationType.SYSTEM.value == "system"
        assert NotificationType.COMMENT.value == "comment"
        assert NotificationType.QUESTION.value == "question"
        assert NotificationType.MESSAGE.value == "message"
        assert NotificationType.APPOINTMENT.value == "appointment"
        assert NotificationType.PRICE_CHANGE.value == "price_change"


class TestModelImports:
    """测试模型类可导入性"""

    def test_import_all_models(self):
        """测试所有模型类可以导入"""
        from app.models import (
            User, House, HouseImage, Comment, Question, Answer,
            Favorite, FavoriteFolder, Like, Message, Notification,
            ViewingAppointment, Report, FAQ,
        )

        assert User is not None
        assert House is not None
        assert HouseImage is not None
        assert Comment is not None
        assert Question is not None
        assert Answer is not None
        assert Favorite is not None
        assert FavoriteFolder is not None
        assert Like is not None
        assert Message is not None
        assert Notification is not None
        assert ViewingAppointment is not None
        assert Report is not None
        assert FAQ is not None

    def test_model_class_attributes(self):
        """测试模型类具有必要的属性"""
        from app.models import User, House

        assert hasattr(User, '__tablename__')
        assert User.__tablename__ == "users"

        assert hasattr(House, '__tablename__')
        assert House.__tablename__ == "houses"

    def test_all_enums_in_all(self):
        """测试所有枚举都在 __all__ 中"""
        from app.models import __all__

        expected_enums = [
            'UserRole', 'UserStatus', 'HouseStatus', 'HouseType',
            'Orientation', 'Decoration', 'ImageType', 'CommentStatus',
            'QuestionStatus', 'MessageType', 'AppointmentStatus',
            'ReportStatus', 'TargetType', 'NotificationType',
        ]

        for enum_name in expected_enums:
            assert enum_name in __all__, f"Enum {enum_name} should be in __all__"


class TestEnumValidation:
    """测试枚举值验证"""

    def test_orientation_from_string(self):
        """测试朝向枚举从字符串解析"""
        from app.models import Orientation

        test_cases = [
            ("north", Orientation.NORTH),
            ("south", Orientation.SOUTH),
            ("east", Orientation.EAST),
            ("west", Orientation.WEST),
            ("southeast", Orientation.SOUTHEAST),
            ("southwest", Orientation.SOUTHWEST),
            ("northeast", Orientation.NORTHEAST),
            ("northwest", Orientation.NORTHWEST),
        ]

        for value, expected in test_cases:
            assert Orientation(value) == expected

    def test_decoration_from_string(self):
        """测试装修枚举从字符串解析"""
        from app.models import Decoration

        test_cases = [
            ("bare", Decoration.BARE),
            ("simple", Decoration.SIMPLE),
            ("fine", Decoration.FINE),
            ("luxury", Decoration.LUXURY),
        ]

        for value, expected in test_cases:
            assert Decoration(value) == expected

    def test_invalid_enum_value_raises(self):
        """测试无效的枚举值抛出异常"""
        from app.models import Orientation, Decoration

        with pytest.raises(ValueError):
            Orientation("invalid")

        with pytest.raises(ValueError):
            Decoration("unknown")
