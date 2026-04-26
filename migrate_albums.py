import os
import shutil
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config import config
from app.logger import get_logger

logger = get_logger()

DB_PATH = "./photo_album.db"
BACKUP_PATH = "./photo_album.db.backup.alb"


def backup_database():
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        logger.info(f"数据库已备份到: {BACKUP_PATH}")
        return True
    return False


def check_album_tables():
    if not os.path.exists(DB_PATH):
        return "empty"
    
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if "albums" not in tables:
        return "needs_migration"
    
    if "photos" in tables:
        columns = [c["name"] for c in inspector.get_columns("photos")]
        if "album_id" not in columns:
            return "needs_migration"
    
    if "album_members" not in tables:
        return "needs_migration"
    
    return "up_to_date"


def create_album_tables():
    logger.info("开始创建相册相关表...")
    
    backup_database()
    
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "albums" not in tables:
            logger.info("创建 albums 表...")
            conn.execute(text("""
                CREATE TABLE albums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT '',
                    is_public BOOLEAN DEFAULT 0,
                    owner_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users (id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_albums_owner_id ON albums (owner_id)"))
            conn.commit()
        
        if "album_members" not in tables:
            logger.info("创建 album_members 表...")
            conn.execute(text("""
                CREATE TABLE album_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    album_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role VARCHAR(50) DEFAULT 'viewer',
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    invited_by INTEGER,
                    FOREIGN KEY (album_id) REFERENCES albums (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (invited_by) REFERENCES users (id)
                )
            """))
            conn.execute(text("CREATE INDEX ix_album_members_album_id ON album_members (album_id)"))
            conn.execute(text("CREATE INDEX ix_album_members_user_id ON album_members (user_id)"))
            conn.commit()
        
        columns = [c["name"] for c in inspector.get_columns("photos")]
        if "album_id" not in columns:
            logger.info("添加 album_id 列到 photos 表...")
            conn.execute(text("ALTER TABLE photos ADD COLUMN album_id INTEGER"))
            conn.execute(text("CREATE INDEX ix_photos_album_id ON photos (album_id)"))
            conn.commit()
        
        users = conn.execute(text("SELECT id FROM users")).fetchall()
        for (user_id,) in users:
            existing_album = conn.execute(
                text("SELECT id FROM albums WHERE owner_id = :owner_id AND name = '默认相册'"),
                {"owner_id": user_id}
            ).fetchone()
            
            if not existing_album:
                logger.info(f"为用户 {user_id} 创建默认相册...")
                result = conn.execute(
                    text("INSERT INTO albums (name, description, owner_id, is_public) VALUES (:name, :description, :owner_id, :is_public)"),
                    {"name": "默认相册", "description": "系统自动创建的默认相册", "owner_id": user_id, "is_public": 0}
                )
                album_id = result.lastrowid
                conn.commit()
                
                logger.info(f"将用户 {user_id} 的现有照片迁移到默认相册 (album_id={album_id})...")
                conn.execute(
                    text("UPDATE photos SET album_id = :album_id WHERE user_id = :user_id AND album_id IS NULL"),
                    {"album_id": album_id, "user_id": user_id}
                )
                conn.commit()
        
        logger.info("相册表创建和数据迁移完成!")


if __name__ == "__main__":
    status = check_album_tables()
    
    if status == "empty":
        logger.info("检测到空数据库，相册表将在应用启动时自动创建。")
    elif status == "needs_migration":
        logger.info("检测到需要添加相册表和字段...")
        create_album_tables()
    else:
        logger.info("相册相关表已是最新状态，无需迁移。")
