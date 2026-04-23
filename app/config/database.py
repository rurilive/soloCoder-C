"""数据库配置"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """基础模型类"""

    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话依赖"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库表"""
    async with engine.begin() as conn:
        # 导入所有模型以确保Base.metadata包含它们
        from app.models import User, House, HouseImage, Comment, Question, Answer
        from app.models import Favorite, FavoriteFolder, Like, Message, Notification
        from app.models import ViewingAppointment, Report

        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()
