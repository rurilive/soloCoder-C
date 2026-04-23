"""租房管理系统主应用入口"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.config.settings import get_settings
from app.config.database import init_db, close_db
from app.routers import (
    auth_router,
    user_router,
    house_router,
    comment_router,
    message_router,
    admin_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 创建上传目录
    upload_dirs = [
        settings.upload_dir,
        settings.upload_image_dir,
        settings.upload_video_dir,
        settings.upload_avatar_dir,
    ]
    for directory in upload_dirs:
        os.makedirs(directory, exist_ok=True)

    # 初始化数据库
    await init_db()

    # 创建默认管理员账户
    async def create_default_admin():
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.config.database import async_session_maker
        from app.models import User, UserRole, UserStatus
        from app.utils.security import get_password_hash

        async with async_session_maker() as session:
            from sqlalchemy import select

            # 检查管理员是否已存在
            result = await session.execute(
                select(User).where(User.role == UserRole.ADMIN)
            )
            existing_admin = result.scalar_one_or_none()

            if not existing_admin:
                admin = User(
                    username=settings.admin_username,
                    email=settings.admin_email,
                    password_hash=get_password_hash(settings.admin_password),
                    nickname="管理员",
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                )
                session.add(admin)
                await session.commit()
                print(f"默认管理员账户已创建: {settings.admin_username} / {settings.admin_password}")

    await create_default_admin()

    yield

    # 关闭数据库连接
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="租房管理系统 - 基于FastAPI + Jinja2的完整租房平台",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts if not settings.debug else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录
BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

# 确保目录存在
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 模板引擎
templates = Jinja2Templates(directory=str(templates_dir))


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    if settings.debug:
        raise exc

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """数据库完整性错误处理"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": "数据操作失败，请检查输入数据",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """请求验证错误处理"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "请求参数验证失败",
            "errors": exc.errors(),
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        },
    )


# 注册路由
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(house_router)
app.include_router(comment_router)
app.include_router(message_router)
app.include_router(admin_router)


# 首页路由
@app.get("/")
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
        },
    )


@app.get("/login")
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse(request, "user/login.html")


@app.get("/register")
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse(request, "user/register.html")


@app.get("/houses")
async def houses_list_page(request: Request):
    """房源列表页面"""
    return templates.TemplateResponse(request, "house/list.html")


@app.get("/houses/{house_id}")
async def house_detail_page(request: Request, house_id: str):
    """房源详情页面"""
    return templates.TemplateResponse(
        request,
        "house/detail.html",
        {"house_id": house_id},
    )


@app.get("/publish")
async def publish_house_page(request: Request):
    """发布房源页面"""
    return templates.TemplateResponse(request, "house/publish.html")


@app.get("/user/profile")
async def user_profile_page(request: Request):
    """用户个人资料页面"""
    return templates.TemplateResponse(request, "user/profile.html")


@app.get("/user/favorites")
async def user_favorites_page(request: Request):
    """用户收藏页面"""
    return templates.TemplateResponse(request, "user/favorites.html")


@app.get("/messages")
async def messages_page(request: Request):
    """消息中心页面"""
    return templates.TemplateResponse(request, "message/index.html")


@app.get("/admin")
async def admin_page(request: Request):
    """管理后台页面"""
    return templates.TemplateResponse(request, "admin/index.html")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": settings.app_version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
