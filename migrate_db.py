import os
import shutil
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config import config
from app.logger import get_logger

logger = get_logger()

DB_PATH = "./photo_album.db"
BACKUP_PATH = "./photo_album.db.backup"
BASE_UPLOAD_DIR = "./uploads"


def backup_database():
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        logger.info(f"数据库已备份到: {BACKUP_PATH}")
        return True
    return False


def check_database_structure():
    if not os.path.exists(DB_PATH):
        return "empty"
    
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if "users" not in tables:
        return "needs_migration"
    
    if "photos" in tables:
        columns = [c["name"] for c in inspector.get_columns("photos")]
        if "user_id" not in columns:
            return "needs_migration"
    
    return "up_to_date"


def migrate_photo_files(user_id: int):
    logger.info(f"\n开始迁移照片文件到用户目录 (user_id={user_id})...")
    
    user_dir = os.path.join(BASE_UPLOAD_DIR, str(user_id))
    user_thumbnails_dir = os.path.join(user_dir, "thumbnails")
    old_thumbnails_dir = os.path.join(BASE_UPLOAD_DIR, "thumbnails")
    
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(user_thumbnails_dir, exist_ok=True)
    
    migrated_count = 0
    skipped_count = 0
    
    if os.path.exists(old_thumbnails_dir):
        for filename in os.listdir(old_thumbnails_dir):
            old_path = os.path.join(old_thumbnails_dir, filename)
            if os.path.isfile(old_path):
                new_path = os.path.join(user_thumbnails_dir, filename)
                if not os.path.exists(new_path):
                    shutil.copy2(old_path, new_path)
                    logger.info(f"  复制缩略图: {filename}")
                    migrated_count += 1
                else:
                    skipped_count += 1
    
    for filename in os.listdir(BASE_UPLOAD_DIR):
        old_path = os.path.join(BASE_UPLOAD_DIR, filename)
        if os.path.isfile(old_path) and not filename.startswith('.'):
            new_path = os.path.join(user_dir, filename)
            if not os.path.exists(new_path):
                shutil.copy2(old_path, new_path)
                logger.info(f"  复制照片: {filename}")
                migrated_count += 1
            else:
                skipped_count += 1
    
    logger.info(f"照片文件迁移完成: 复制了 {migrated_count} 个文件，跳过了 {skipped_count} 个已存在的文件")


def migrate_database():
    logger.info("开始数据库迁移...")
    
    backup_database()
    
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "users" not in tables:
            logger.info("创建 users 表...")
            conn.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        
        initial_user = conn.execute(text("SELECT * FROM users WHERE token = :token"), {"token": config.INITIAL_TOKEN}).fetchone()
        if not initial_user:
            logger.info(f"创建初始用户 (token: {config.INITIAL_TOKEN})...")
            conn.execute(
                text("INSERT INTO users (token, username) VALUES (:token, :username)"),
                {"token": config.INITIAL_TOKEN, "username": "admin"}
            )
            conn.commit()
        
        columns = [c["name"] for c in inspector.get_columns("photos")]
        if "user_id" not in columns:
            logger.info("添加 user_id 列到 photos 表...")
            
            initial_user = conn.execute(text("SELECT * FROM users WHERE token = :token"), {"token": config.INITIAL_TOKEN}).fetchone()
            user_id = initial_user[0]
            
            conn.execute(text("ALTER TABLE photos ADD COLUMN user_id INTEGER"))
            conn.execute(text("UPDATE photos SET user_id = :user_id"), {"user_id": user_id})
            conn.execute(text("CREATE INDEX ix_photos_user_id ON photos (user_id)"))
            conn.commit()
            logger.info(f"所有现有照片已分配给用户 ID: {user_id} (admin)")
            
            migrate_photo_files(user_id)
        
        logger.info("数据库迁移完成!")


def init_new_database():
    logger.info("初始化新数据库...")
    
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename VARCHAR(255) NOT NULL,
                thumbnail_filename VARCHAR(255),
                tags VARCHAR(500) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT DEFAULT '',
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """))
        
        conn.execute(text("CREATE INDEX ix_photos_user_id ON photos (user_id)"))
        conn.execute(text("CREATE INDEX ix_photos_filename ON photos (filename)"))
        
        conn.execute(
            text("INSERT INTO users (token, username) VALUES (:token, :username)"),
            {"token": config.INITIAL_TOKEN, "username": "admin"}
        )
        
        conn.commit()
    
    logger.info("新数据库初始化完成!")
    logger.info(f"初始用户 token: {config.INITIAL_TOKEN} (username: admin)")


if __name__ == "__main__":
    status = check_database_structure()
    
    if status == "empty":
        logger.info("检测到空数据库，创建新数据库...")
        init_new_database()
    elif status == "needs_migration":
        logger.info("检测到旧数据库结构，需要迁移...")
        migrate_database()
    else:
        logger.info("数据库已是最新状态，无需迁移。")
