import os
import numpy as np
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
from app.logger import get_logger

logger = get_logger()

load_dotenv()


class EmbeddingService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please set it in .env file or environment variable.")
        
        base_url = os.getenv("OPENAI_BASE_URL")
        
        logger.info(f"[EmbeddingService] 初始化...")
        logger.info(f"  - API Key: {api_key[:5] if api_key else None}...{api_key[-5:] if api_key and len(api_key) > 10 else ''}")
        logger.info(f"  - Base URL: {base_url}")
        
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        
        logger.info(f"  - Model: {self.model}")
        logger.info(f"  - Dimensions: {self.dimensions}")
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        if not text or not text.strip():
            logger.warning(f"[EmbeddingService.embed_text] 文本为空，返回 None")
            return None
        
        logger.debug(f"[EmbeddingService.embed_text] 输入文本: '{text.strip()}'")
        
        try:
            logger.debug(f"[EmbeddingService.embed_text] 调用 OpenAI API, Model: {self.model}")
            
            response = self.client.embeddings.create(
                input=text.strip(),
                model=self.model,
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"[EmbeddingService.embed_text] 嵌入向量维度: {len(embedding)}")
            
            if len(embedding) > 0:
                arr = np.array(embedding)
                logger.debug(f"[EmbeddingService.embed_text] 向量统计: min={arr.min():.4f}, max={arr.max():.4f}, mean={arr.mean():.4f}, norm={np.linalg.norm(arr):.4f}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"[EmbeddingService.embed_text] 生成嵌入向量时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        logger.debug(f"[EmbeddingService.embed_texts] 批量嵌入 {len(texts)} 个文本")
        
        results = []
        for i, text in enumerate(texts):
            result = self.embed_text(text)
            results.append(result)
        
        success_count = len([r for r in results if r is not None])
        logger.debug(f"[EmbeddingService.embed_texts] 完成: {success_count}/{len(texts)} 成功")
        return results
    
    def embed_description(self, description: str, tags: str = "") -> Optional[List[float]]:
        logger.debug(f"[EmbeddingService.embed_description] description='{description}', tags='{tags}'")
        
        combined_text = description
        if tags:
            combined_text = f"{description} Tags: {tags}"
        
        logger.debug(f"[EmbeddingService.embed_description] 组合后文本: '{combined_text}'")
        
        return self.embed_text(combined_text)
    
    def get_embedding_dimensions(self) -> int:
        return self.dimensions


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
