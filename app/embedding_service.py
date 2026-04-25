import os
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


class EmbeddingService:
    def __init__(self):
        print(f"\n{'='*60}")
        print("[DEBUG EmbeddingService.__init__] 初始化 EmbeddingService")
        print(f"{'='*60}")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please set it in .env file or environment variable.")
        
        base_url = os.getenv("OPENAI_BASE_URL")
        
        print(f"[DEBUG EmbeddingService.__init__] API Key: {api_key[:5] if api_key else None}...{api_key[-5:] if api_key and len(api_key) > 10 else ''}")
        print(f"[DEBUG EmbeddingService.__init__] Base URL: {base_url}")
        
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        
        print(f"[DEBUG EmbeddingService.__init__] Model: {self.model}")
        print(f"[DEBUG EmbeddingService.__init__] Dimensions: {self.dimensions}")
        print(f"{'='*60}\n")
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        print(f"\n{'='*60}")
        print("[DEBUG EmbeddingService.embed_text] 开始文本嵌入")
        print(f"{'='*60}")
        
        if not text or not text.strip():
            print("[DEBUG EmbeddingService.embed_text] ❌ 文本为空，返回 None")
            return None
        
        print(f"[DEBUG EmbeddingService.embed_text] 输入文本: '{text.strip()}'")
        print(f"[DEBUG EmbeddingService.embed_text] 文本长度: {len(text.strip())} 字符")
        
        try:
            print(f"[DEBUG EmbeddingService.embed_text] 调用 OpenAI API...")
            print(f"[DEBUG EmbeddingService.embed_text]   - Model: {self.model}")
            
            response = self.client.embeddings.create(
                input=text.strip(),
                model=self.model,
            )
            
            print(f"[DEBUG EmbeddingService.embed_text] ✅ API 调用成功")
            
            embedding = response.data[0].embedding
            print(f"[DEBUG EmbeddingService.embed_text] 嵌入向量维度: {len(embedding)}")
            print(f"[DEBUG EmbeddingService.embed_text] 嵌入向量前5个值: {embedding[:5]}")
            print(f"[DEBUG EmbeddingService.embed_text] 嵌入向量后5个值: {embedding[-5:]}")
            
            if len(embedding) > 0:
                import numpy as np
                arr = np.array(embedding)
                print(f"[DEBUG EmbeddingService.embed_text] 嵌入向量统计:")
                print(f"  - min: {arr.min():.6f}")
                print(f"  - max: {arr.max():.6f}")
                print(f"  - mean: {arr.mean():.6f}")
                print(f"  - std: {arr.std():.6f}")
                print(f"  - L2 norm: {np.linalg.norm(arr):.6f}")
            
            print(f"{'='*60}\n")
            return embedding
            
        except Exception as e:
            print(f"[DEBUG EmbeddingService.embed_text] ❌ 生成嵌入向量时出错: {e}")
            import traceback
            traceback.print_exc()
            print(f"{'='*60}\n")
            return None
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        print(f"\n{'='*60}")
        print(f"[DEBUG EmbeddingService.embed_texts] 批量嵌入 {len(texts)} 个文本")
        print(f"{'='*60}")
        
        results = []
        for i, text in enumerate(texts):
            print(f"\n[DEBUG EmbeddingService.embed_texts] 处理第 {i+1}/{len(texts)} 个文本")
            result = self.embed_text(text)
            results.append(result)
        
        print(f"\n[DEBUG EmbeddingService.embed_texts] 批量嵌入完成，成功 {len([r for r in results if r is not None])}/{len(texts)} 个")
        print(f"{'='*60}\n")
        return results
    
    def embed_description(self, description: str, tags: str = "") -> Optional[List[float]]:
        print(f"\n{'='*60}")
        print("[DEBUG EmbeddingService.embed_description] 嵌入描述和标签")
        print(f"{'='*60}")
        
        print(f"[DEBUG EmbeddingService.embed_description] 原始描述: '{description}'")
        print(f"[DEBUG EmbeddingService.embed_description] 原始标签: '{tags}'")
        
        combined_text = description
        if tags:
            combined_text = f"{description} Tags: {tags}"
        
        print(f"[DEBUG EmbeddingService.embed_description] 组合后文本: '{combined_text}'")
        
        result = self.embed_text(combined_text)
        
        if result:
            print(f"[DEBUG EmbeddingService.embed_description] ✅ 成功生成嵌入向量")
        else:
            print(f"[DEBUG EmbeddingService.embed_description] ❌ 嵌入向量生成失败")
        
        return result
    
    def get_embedding_dimensions(self) -> int:
        return self.dimensions


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
