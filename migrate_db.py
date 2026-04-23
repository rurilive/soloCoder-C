"""独立的数据库迁移脚本 - 为房源表添加新字段"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./rental.db")

MIGRATIONS = [
    """ALTER TABLE houses ADD COLUMN property_type VARCHAR(50)""",
    """ALTER TABLE houses ADD COLUMN bedrooms INTEGER""",
    """ALTER TABLE houses ADD COLUMN livingrooms INTEGER""",
    """ALTER TABLE houses ADD COLUMN bathrooms INTEGER""",
    """ALTER TABLE houses ADD COLUMN contact_name VARCHAR(50)""",
    """ALTER TABLE houses ADD COLUMN contact_phone VARCHAR(20)""",
]


async def run_migration():
    """运行迁移"""
    print("=" * 60)
    print("房源表迁移脚本")
    print("=" * 60)
    print(f"数据库: {DATABASE_URL}")
    print()
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for migration in MIGRATIONS:
            try:
                await session.execute(text(migration))
                await session.commit()
                print(f"✓ 成功: {migration}")
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    print(f"- 跳过: {migration} (列已存在)")
                    await session.rollback()
                else:
                    print(f"✗ 失败: {migration}")
                    print(f"  错误: {e}")
                    await session.rollback()
    
    await engine.dispose()
    
    print()
    print("=" * 60)
    print("迁移完成!")
    print("=" * 60)
    print()
    print("新增字段说明:")
    print("  - property_type: 房屋类型（公寓/住宅/别墅等）")
    print("  - bedrooms: 卧室数量")
    print("  - livingrooms: 客厅数量")
    print("  - bathrooms: 卫生间数量")
    print("  - contact_name: 联系人姓名")
    print("  - contact_phone: 联系电话")


if __name__ == "__main__":
    asyncio.run(run_migration())
