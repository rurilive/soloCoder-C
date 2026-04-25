import os
import shutil
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker
import datetime
import uuid

DB_PATH = "./photo_album.db"
BACKUP_PATH = "./photo_album.db.backup"
INITIAL_TOKEN = "aaaa"


def backup_database():
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"数据库已备份到: {BACKUP_PATH}")
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


def migrate_database():
    print("开始数据库迁移...")
    
    backup_database()
    
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "users" not in tables:
            print("创建 users 表...")
            conn.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        
        initial_user = conn.execute(text("SELECT * FROM users WHERE token = :token"), {"token": INITIAL_TOKEN}).fetchone()
        if not initial_user:
            print("创建初始用户 (token: aaaa)...")
            conn.execute(
                text("INSERT INTO users (token, username) VALUES (:token, :username)"),
                {"token": INITIAL_TOKEN, "username": "admin"}
            )
            conn.commit()
        
        columns = [c["name"] for c in inspector.get_columns("photos")]
        if "user_id" not in columns:
            print("添加 user_id 列到 photos 表...")
            
            initial_user = conn.execute(text("SELECT * FROM users WHERE token = :token"), {"token": INITIAL_TOKEN}).fetchone()
            user_id = initial_user[0]
            
            conn.execute(text("ALTER TABLE photos ADD COLUMN user_id INTEGER"))
            conn.execute(text("UPDATE photos SET user_id = :user_id"), {"user_id": user_id})
            conn.execute(text("CREATE INDEX ix_photos_user_id ON photos (user_id)"))
            conn.commit()
            print(f"所有现有照片已分配给用户 ID: {user_id} (admin)")
        
        print("数据库迁移完成!")


def init_new_database():
    print("初始化新数据库...")
    
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
            {"token": INITIAL_TOKEN, "username": "admin"}
        )
        
        conn.commit()
    
    print("新数据库初始化完成!")
    print(f"初始用户 token: {INITIAL_TOKEN} (username: admin)")


if __name__ == "__main__":
    status = check_database_structure()
    
    if status == "empty":
        print("检测到空数据库，创建新数据库...")
        init_new_database()
    elif status == "needs_migration":
        print("检测到旧数据库结构，需要迁移...")
        migrate_database()
    else:
        print("数据库已是最新状态，无需迁移。")
