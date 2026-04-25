import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class VectorEntry:
    photo_id: int
    text_embedding: Optional[List[float]] = None
    image_embedding: Optional[List[float]] = None
    description: str = ""
    tags: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VectorEntry":
        return cls(**data)


class VectorStore:
    def __init__(self, store_path: str = "./vector_store"):
        self.store_path = store_path
        self.vectors_file = os.path.join(store_path, "vectors.npz")
        self.metadata_file = os.path.join(store_path, "metadata.json")
        
        os.makedirs(store_path, exist_ok=True)
        
        self._entries: Dict[int, VectorEntry] = {}
        self._text_embeddings: Dict[int, np.ndarray] = {}
        self._image_embeddings: Dict[int, np.ndarray] = {}
        
        self._load()
    
    def _load(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                for entry_data in metadata.get("entries", []):
                    entry = VectorEntry.from_dict(entry_data)
                    self._entries[entry.photo_id] = entry
        
        if os.path.exists(self.vectors_file):
            data = np.load(self.vectors_file, allow_pickle=True)
            for key in data.files:
                if key.startswith("text_"):
                    photo_id = int(key.replace("text_", ""))
                    self._text_embeddings[photo_id] = data[key]
                elif key.startswith("image_"):
                    photo_id = int(key.replace("image_", ""))
                    self._image_embeddings[photo_id] = data[key]
    
    def _save(self):
        metadata = {
            "entries": [entry.to_dict() for entry in self._entries.values()]
        }
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        vectors_to_save = {}
        for photo_id, emb in self._text_embeddings.items():
            vectors_to_save[f"text_{photo_id}"] = emb
        for photo_id, emb in self._image_embeddings.items():
            vectors_to_save[f"image_{photo_id}"] = emb
        
        if vectors_to_save:
            np.savez(self.vectors_file, **vectors_to_save)
        else:
            if os.path.exists(self.vectors_file):
                os.remove(self.vectors_file)
    
    def add_entry(
        self,
        photo_id: int,
        text_embedding: Optional[List[float]] = None,
        image_embedding: Optional[List[float]] = None,
        description: str = "",
        tags: str = "",
    ):
        entry = VectorEntry(
            photo_id=photo_id,
            description=description,
            tags=tags,
        )
        self._entries[photo_id] = entry
        
        if text_embedding is not None:
            self._text_embeddings[photo_id] = np.array(text_embedding, dtype=np.float32)
        
        if image_embedding is not None:
            self._image_embeddings[photo_id] = np.array(image_embedding, dtype=np.float32)
        
        self._save()
    
    def remove_entry(self, photo_id: int):
        if photo_id in self._entries:
            del self._entries[photo_id]
        if photo_id in self._text_embeddings:
            del self._text_embeddings[photo_id]
        if photo_id in self._image_embeddings:
            del self._image_embeddings[photo_id]
        self._save()
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def search_by_text(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        query = np.array(query_embedding, dtype=np.float32)
        results = []
        
        for photo_id, emb in self._text_embeddings.items():
            sim = self.cosine_similarity(query, emb)
            results.append((photo_id, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def search_by_image(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        query = np.array(query_embedding, dtype=np.float32)
        results = []
        
        for photo_id, emb in self._image_embeddings.items():
            sim = self.cosine_similarity(query, emb)
            results.append((photo_id, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def search_combined(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        query = np.array(query_embedding, dtype=np.float32)
        results = []
        
        for photo_id in self._entries:
            max_sim = 0.0
            
            if photo_id in self._text_embeddings:
                text_sim = self.cosine_similarity(query, self._text_embeddings[photo_id])
                max_sim = max(max_sim, text_sim)
            
            if photo_id in self._image_embeddings:
                image_sim = self.cosine_similarity(query, self._image_embeddings[photo_id])
                max_sim = max(max_sim, image_sim)
            
            if max_sim > 0:
                results.append((photo_id, max_sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_entry(self, photo_id: int) -> Optional[VectorEntry]:
        return self._entries.get(photo_id)
    
    def has_text_embedding(self, photo_id: int) -> bool:
        return photo_id in self._text_embeddings
    
    def has_image_embedding(self, photo_id: int) -> bool:
        return photo_id in self._image_embeddings


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
