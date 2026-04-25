import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("测试 Embedding API 连接")
print("=" * 60)

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("OPENAI_EMBEDDING_MODEL")

print(f"\n配置信息:")
print(f"  API Key: {api_key[:10] if api_key else '(未设置)'}...")
print(f"  Base URL: {base_url}")
print(f"  Model: {model}")

if not api_key:
    print("\n❌ 错误: 未设置 OPENAI_API_KEY")
    exit(1)

from openai import OpenAI

try:
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    
    client = OpenAI(**client_kwargs)
    
    print(f"\n正在调用 API...")
    print(f"  测试文本: '黑眼圈'")
    
    response = client.embeddings.create(
        input="黑眼圈",
        model=model,
    )
    
    embedding = response.data[0].embedding
    print(f"\n✅ API 调用成功!")
    print(f"  向量维度: {len(embedding)}")
    print(f"  前5个值: {embedding[:5]}")
    
    print(f"\n正在测试另一个文本...")
    response2 = client.embeddings.create(
        input="熊猫的黑眼睛",
        model=model,
    )
    embedding2 = response2.data[0].embedding
    
    import numpy as np
    a = np.array(embedding)
    b = np.array(embedding2)
    sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    print(f"  '黑眼圈' 和 '熊猫的黑眼睛' 的相似度: {sim:.4f}")
    
    if sim > 0.7:
        print(f"  这两个词语义相似度较高，向量搜索应该能工作")
    
except Exception as e:
    print(f"\n❌ API 调用失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
