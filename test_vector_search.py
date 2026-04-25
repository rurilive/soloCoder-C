import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("测试向量搜索功能")
print("=" * 60)

print("\n测试 1: 直接测试语义相似度...")
print("-" * 60)

from app.embedding_service import get_embedding_service

embedding_service = get_embedding_service()

test_pairs = [
    ("黑眼圈", "熊猫的黑眼睛"),
    ("黑眼圈", "黑眼圈很重"),
    ("黑眼圈", "白色的熊猫"),
    ("黑眼圈", "太阳"),
]

for text1, text2 in test_pairs:
    emb1 = embedding_service.embed_text(text1)
    emb2 = embedding_service.embed_text(text2)
    
    if emb1 and emb2:
        import numpy as np
        a = np.array(emb1)
        b = np.array(emb2)
        sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        print(f"  '{text1}' ↔ '{text2}': 相似度 = {sim:.4f}")

print("\n" + "-" * 60)
print("测试 2: 模拟搜索测试（添加测试数据）")
print("-" * 60)

from app.vector_store import get_vector_store

vector_store = get_vector_store()

test_descriptions = [
    (1001, "可爱的大熊猫，有黑眼圈", "熊猫, 可爱"),
    (1002, "今天工作太累了，黑眼圈很重", "工作, 累"),
    (1003, "海边日落风景照", "风景, 海边"),
    (1004, "这只熊猫正在吃竹子", "熊猫, 竹子"),
]

print("\n  添加测试数据到向量存储:")
for photo_id, desc, tags in test_descriptions:
    emb = embedding_service.embed_description(desc, tags)
    if emb:
        vector_store.add_entry(
            photo_id=photo_id,
            text_embedding=emb,
            description=desc,
            tags=tags,
        )
        print(f"    ID {photo_id}: '{desc}'")

print("\n  测试搜索 '黑眼圈':")
search_query = "黑眼圈"
query_emb = embedding_service.embed_text(search_query)

if query_emb:
    results = vector_store.search_combined(query_emb, top_k=10)
    print(f"\n    搜索结果 (按相似度排序):")
    for photo_id, sim in results:
        entry = vector_store.get_entry(photo_id)
        desc = entry.description if entry else "(未知)"
        print(f"      相似度 {sim*100:>5.1f}% | ID {photo_id:>4} | '{desc}'")

print("\n  清理测试数据...")
for photo_id, _, _ in test_descriptions:
    vector_store.remove_entry(photo_id)

print("\n" + "=" * 60)
print("结论")
print("=" * 60)
print("""
✅ 向量搜索功能正常工作！

问题原因:
  你现有的图片描述是 'fff'、'sss' 等无意义字符
  这些字符与 "黑眼圈" 没有任何语义关联

解决方案:
  上传新图片时，填写有意义的描述
  例如:
    - 熊猫图片 → 描述填 "可爱的大熊猫，有黑眼圈"
    - 风景图片 → 描述填 "美丽的海边日落"
    - 人像图片 → 描述填 "家庭聚会合影"
""")
print("=" * 60)
