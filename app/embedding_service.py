import os
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


class EmbeddingService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please set it in .env file or environment variable.")
        
        base_url = os.getenv("OPENAI_BASE_URL")
        
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        if not text or not text.strip():
            return None
        
        try:
            response = self.client.embeddings.create(
                input=text.strip(),
                model=self.model,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating text embedding: {e}")
            return None
    
    def embed_texts(self, texts: List[str]) -> List[Optional[List[float]]]:
        results = []
        for text in texts:
            results.append(self.embed_text(text))
        return results
    
    def embed_description(self, description: str, tags: str = "") -> Optional[List[float]]:
        combined_text = description
        if tags:
            combined_text = f"{description} Tags: {tags}"
        
        return self.embed_text(combined_text)
    
    def get_embedding_dimensions(self) -> int:
        return self.dimensions


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
