"""房源表迁移脚本 - 添加新字段"""

import asyncio
from sqlalchemy import text
from app.config.database import async_session_maker, engine


MIGRATIONS = [
    # SQLite 不支持同时添加多列，需要分开执行
    """ALTER TABLE houses ADD COLUMN property_type VARCHAR(50)""",
    """ALTER TABLE houses ADD COLUMN bedrooms INTEGER""",
    """ALTER TABLE houses ADD COLUMN livingrooms INTEGER""",
    """ALTER TABLE houses ADD COLUMN bathrooms INTEGER""",
    """ALTER TABLE houses ADD COLUMN contact_name VARCHAR(50)""",
    """ALTER TABLE houses ADD COLUMN contact_phone VARCHAR(20)""",
]


async def run_migration():
    """运行迁移"""
    print("开始执行房源表迁移...")
    
    async with async_session_maker() as session:
        try:
            for migration in MIGRATIONS:
                try:
                    await session.execute(text(migration))
                    await session.commit()
                    print(f"✓ 执行成功: {migration[:80]}...")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "duplicate column" in error_msg or "already exists" in error_msg:
                        print(f"- 列已存在，跳过: {migration[:50]}...")
                        await session.rollback()
                    else:
                        print(f"✗ 执行失败: {e}")
                        await session.rollback()
                        raise
            
            print("\n迁移完成！")
            print("\n新增字段:")
            print("  - property_type: 房屋类型（公寓/住宅/别墅等）")
            print("  - bedrooms: 卧室数量")
            print("  - livingrooms: 客厅数量")
            print("  - bathrooms: 卫生间数量")
            print("  - contact_name: 联系人姓名")
            print("  - contact_phone: 联系电话")
            
        except Exception as e:
            print(f"\n迁移过程中出错: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
