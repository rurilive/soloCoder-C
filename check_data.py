import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./photo_album.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.database import Photo, Base

print("=" * 60)
print("数据库检查")
print("=" * 60)

db = SessionLocal()
photos = db.query(Photo).all()

print(f"\n数据库中共有 {len(photos)} 张图片\n")

for i, photo in enumerate(photos, 1):
    print(f"--- 图片 {i} ---")
    print(f"  ID: {photo.id}")
    print(f"  描述: '{photo.description}'")
    print(f"  标签: '{photo.tags}'")
    print(f"  创建时间: {photo.created_at}")
    print()

db.close()

print("\n" + "=" * 60)
print("环境变量检查")
print("=" * 60)
print(f"OPENAI_API_KEY 已配置: {'是' if os.getenv('OPENAI_API_KEY') else '否'}")
print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', '(未设置)')}")
print(f"OPENAI_EMBEDDING_MODEL: {os.getenv('OPENAI_EMBEDDING_MODEL', '(默认)')}")

print("\n" + "=" * 60)
print("向量存储检查")
print("=" * 60)

vector_store_path = "./vector_store"
if os.path.exists(vector_store_path):
    print(f"向量存储目录存在: {vector_store_path}")
    files = os.listdir(vector_store_path)
    for f in files:
        fpath = os.path.join(vector_store_path, f)
        size = os.path.getsize(fpath)
        print(f"  - {f} ({size} bytes)")
else:
    print("向量存储目录不存在")

print("\n" + "=" * 60)
print("搜索测试")
print("=" * 60)

search_term = "黑眼圈"
print(f"测试搜索词: '{search_term}'\n")

db = SessionLocal()

like_results = db.query(Photo).filter(Photo.description.like(f"%{search_term}%")).all()
print(f"SQL LIKE 模糊匹配结果: {len(like_results)} 条")

for photo in like_results:
    print(f"  - ID: {photo.id}, 描述: '{photo.description}'")

if not like_results:
    print("  没有匹配的图片")
    print(f"  原因: 描述字段中没有包含 '{search_term}' 的图片")

db.close()

print("\n" + "=" * 60)
print("问题分析")
print("=" * 60)

if len(photos) == 0:
    print("❌ 数据库中没有图片，请先上传图片")
elif not like_results:
    print(f"❌ 描述中没有包含 '{search_term}' 的图片")
    print("  普通搜索使用 SQL LIKE 模糊匹配，需要描述中包含搜索词")
    print(f"  例如: 如果描述是'熊猫有黑眼圈'，搜索'黑眼圈'可以匹配到")
else:
    print("✅ 普通搜索应该可以工作")

if not os.getenv('OPENAI_API_KEY'):
    print("\n❌ 向量搜索未启用: 缺少 OPENAI_API_KEY")
    print("  请在 .env 文件中配置 OPENAI_API_KEY")
else:
    print("\n✅ OPENAI_API_KEY 已配置")
    if not os.path.exists(vector_store_path) or not os.listdir(vector_store_path):
        print("❌ 向量存储为空")
        print("  原因: 上传图片时需要填写描述，描述才会被转为向量")
        print("  请重新上传图片并填写描述字段")
    else:
        print("✅ 向量存储存在数据")

print("\n" + "=" * 60)
