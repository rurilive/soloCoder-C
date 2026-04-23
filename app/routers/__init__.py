"""路由模块"""

from app.routers.auth import router as auth_router
from app.routers.user import router as user_router
from app.routers.house import router as house_router
from app.routers.comment import router as comment_router
from app.routers.message import router as message_router
from app.routers.admin import router as admin_router

__all__ = [
    "auth_router",
    "user_router",
    "house_router",
    "comment_router",
    "message_router",
    "admin_router",
]
