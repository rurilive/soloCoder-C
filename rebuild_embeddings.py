import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("重新生成所有图片的 Embedding")
print("=" * 60)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./photo_album.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.database import Photo
from app.embedding_service import get_embedding_service
from app.vector_store import get_vector_store

print("\n步骤 1: 检查数据库中的图片...")
db = SessionLocal()
photos = db.query(Photo).all()
print(f"  数据库中共有 {len(photos)} 张图片")

if len(photos) == 0:
    print("\n❌ 数据库中没有图片，请先上传图片")
    db.close()
    exit(1)

print("\n步骤 2: 清理现有向量数据...")
vector_store = get_vector_store()

for photo in photos:
    vector_store.remove_entry(photo.id)

print(f"  已清理 {len(photos)} 条记录")

print("\n步骤 3: 为所有图片生成新的 Embedding...")
embedding_service = get_embedding_service()

success_count = 0
fail_count = 0

for i, photo in enumerate(photos, 1):
    print(f"\n  [{i}/{len(photos)}] 图片 ID: {photo.id}")
    print(f"      描述: '{photo.description}'")
    print(f"      标签: '{photo.tags}'")
    
    try:
        text_embedding = embedding_service.embed_description(
            photo.description, 
            photo.tags
        )
        
        if text_embedding:
            vector_store.add_entry(
                photo_id=photo.id,
                text_embedding=text_embedding,
                description=photo.description,
                tags=photo.tags,
            )
            print(f"      ✅ 生成成功，维度: {len(text_embedding)}")
            success_count += 1
        else:
            print(f"      ⚠️  无法生成 embedding（可能是描述为空）")
            fail_count += 1
            
    except Exception as e:
        print(f"      ❌ 错误: {e}")
        fail_count += 1

db.close()

print("\n" + "=" * 60)
print("完成总结")
print("=" * 60)
print(f"  成功: {success_count} 张")
print(f"  失败: {fail_count} 张")

if success_count > 0:
    print(f"\n✅ 向量数据已更新！")
    print(f"\n提示：")
    print(f"  1. 现有图片的描述: 'fff', 'fff', 'sss' 都是无意义的字符")
    print(f"  2. 要测试向量搜索，建议上传带有有意义描述的图片")
    print(f"  3. 例如：上传熊猫图片，描述填'可爱的大熊猫，有黑眼圈'")
else:
    print(f"\n❌ 没有成功生成任何 embedding")

print("\n" + "=" * 60)
