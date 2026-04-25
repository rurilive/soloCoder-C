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
        print(f"\n{'='*60}")
        print("[DEBUG VectorStore.__init__] 初始化 VectorStore")
        print(f"{'='*60}")
        
        self.store_path = store_path
        self.vectors_file = os.path.join(store_path, "vectors.npz")
        self.metadata_file = os.path.join(store_path, "metadata.json")
        
        print(f"[DEBUG VectorStore.__init__] 存储路径: {self.store_path}")
        print(f"[DEBUG VectorStore.__init__] 元数据文件: {self.metadata_file}")
        print(f"[DEBUG VectorStore.__init__] 向量文件: {self.vectors_file}")
        
        os.makedirs(store_path, exist_ok=True)
        
        self._entries: Dict[int, VectorEntry] = {}
        self._text_embeddings: Dict[int, np.ndarray] = {}
        self._image_embeddings: Dict[int, np.ndarray] = {}
        
        self._load()
        
        print(f"[DEBUG VectorStore.__init__] 加载完成:")
        print(f"  - 条目总数: {len(self._entries)}")
        print(f"  - 文本嵌入数: {len(self._text_embeddings)}")
        print(f"  - 图像嵌入数: {len(self._image_embeddings)}")
        print(f"{'='*60}\n")
    
    def _load(self):
        print(f"\n[DEBUG VectorStore._load] 开始加载向量存储数据...")
        
        if os.path.exists(self.metadata_file):
            print(f"[DEBUG VectorStore._load] 从 {self.metadata_file} 加载元数据")
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                entries = metadata.get("entries", [])
                print(f"[DEBUG VectorStore._load] 元数据中有 {len(entries)} 个条目")
                
                for i, entry_data in enumerate(entries):
                    entry = VectorEntry.from_dict(entry_data)
                    self._entries[entry.photo_id] = entry
                    print(f"  [{i+1}] photo_id={entry.photo_id}, description='{entry.description}', tags='{entry.tags}'")
        else:
            print(f"[DEBUG VectorStore._load] 元数据文件不存在: {self.metadata_file}")
        
        if os.path.exists(self.vectors_file):
            print(f"[DEBUG VectorStore._load] 从 {self.vectors_file} 加载向量")
            data = np.load(self.vectors_file, allow_pickle=True)
            
            text_count = 0
            image_count = 0
            
            for key in data.files:
                if key.startswith("text_"):
                    photo_id = int(key.replace("text_", ""))
                    self._text_embeddings[photo_id] = data[key]
                    text_count += 1
                    print(f"  [文本] photo_id={photo_id}, 维度={len(data[key])}")
                elif key.startswith("image_"):
                    photo_id = int(key.replace("image_", ""))
                    self._image_embeddings[photo_id] = data[key]
                    image_count += 1
                    print(f"  [图像] photo_id={photo_id}, 维度={len(data[key])}")
            
            print(f"[DEBUG VectorStore._load] 向量加载完成: 文本={text_count}, 图像={image_count}")
        else:
            print(f"[DEBUG VectorStore._load] 向量文件不存在: {self.vectors_file}")
    
    def _save(self):
        print(f"\n[DEBUG VectorStore._save] 开始保存向量存储数据...")
        
        metadata = {
            "entries": [entry.to_dict() for entry in self._entries.values()]
        }
        
        print(f"[DEBUG VectorStore._save] 保存元数据到 {self.metadata_file}")
        print(f"  - 条目数: {len(metadata['entries'])}")
        
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        vectors_to_save = {}
        for photo_id, emb in self._text_embeddings.items():
            vectors_to_save[f"text_{photo_id}"] = emb
        for photo_id, emb in self._image_embeddings.items():
            vectors_to_save[f"image_{photo_id}"] = emb
        
        if vectors_to_save:
            print(f"[DEBUG VectorStore._save] 保存向量到 {self.vectors_file}")
            print(f"  - 向量数: {len(vectors_to_save)}")
            np.savez(self.vectors_file, **vectors_to_save)
        else:
            print(f"[DEBUG VectorStore._save] 没有向量需要保存")
            if os.path.exists(self.vectors_file):
                os.remove(self.vectors_file)
                print(f"[DEBUG VectorStore._save] 已删除空的向量文件")
    
    def add_entry(
        self,
        photo_id: int,
        text_embedding: Optional[List[float]] = None,
        image_embedding: Optional[List[float]] = None,
        description: str = "",
        tags: str = "",
    ):
        print(f"\n{'='*60}")
        print(f"[DEBUG VectorStore.add_entry] 添加向量条目")
        print(f"{'='*60}")
        print(f"  - photo_id: {photo_id}")
        print(f"  - description: '{description}'")
        print(f"  - tags: '{tags}'")
        print(f"  - 文本嵌入: {'有' if text_embedding else '无'}")
        print(f"  - 图像嵌入: {'有' if image_embedding else '无'}")
        
        entry = VectorEntry(
            photo_id=photo_id,
            description=description,
            tags=tags,
        )
        self._entries[photo_id] = entry
        
        if text_embedding is not None:
            print(f"[DEBUG VectorStore.add_entry] 保存文本嵌入，维度: {len(text_embedding)}")
            self._text_embeddings[photo_id] = np.array(text_embedding, dtype=np.float32)
        
        if image_embedding is not None:
            print(f"[DEBUG VectorStore.add_entry] 保存图像嵌入，维度: {len(image_embedding)}")
            self._image_embeddings[photo_id] = np.array(image_embedding, dtype=np.float32)
        
        self._save()
        print(f"{'='*60}\n")
    
    def remove_entry(self, photo_id: int):
        print(f"\n[DEBUG VectorStore.remove_entry] 删除向量条目 photo_id={photo_id}")
        
        removed = False
        if photo_id in self._entries:
            del self._entries[photo_id]
            print(f"  - 已删除元数据")
            removed = True
        if photo_id in self._text_embeddings:
            del self._text_embeddings[photo_id]
            print(f"  - 已删除文本嵌入")
            removed = True
        if photo_id in self._image_embeddings:
            del self._image_embeddings[photo_id]
            print(f"  - 已删除图像嵌入")
            removed = True
        
        if removed:
            self._save()
        else:
            print(f"  - 未找到该条目")
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        dot_product = np.dot(a, b)
        similarity = float(dot_product / (norm_a * norm_b))
        
        return similarity
    
    def search_by_text(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        print(f"\n{'='*60}")
        print("[DEBUG VectorStore.search_by_text] 文本向量搜索")
        print(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        print(f"  - 查询向量维度: {len(query)}")
        print(f"  - 查询向量前5值: {query[:5]}")
        print(f"  - 候选条目数: {len(self._text_embeddings)}")
        
        results = []
        
        for photo_id, emb in self._text_embeddings.items():
            sim = self.cosine_similarity(query, emb)
            
            entry = self._entries.get(photo_id)
            desc = entry.description if entry else ""
            tags = entry.tags if entry else ""
            
            print(f"  [比较] photo_id={photo_id}, similarity={sim:.6f}, desc='{desc[:30] if desc else '空'}...'")
            
            results.append((photo_id, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n[DEBUG VectorStore.search_by_text] 搜索结果 (top {min(top_k, len(results))}):")
        for i, (pid, sim) in enumerate(results[:top_k]):
            entry = self._entries.get(pid)
            desc = entry.description if entry else ""
            print(f"  {i+1}. photo_id={pid}, similarity={sim:.6f}, desc='{desc[:50] if desc else '空'}'")
        
        print(f"{'='*60}\n")
        return results[:top_k]
    
    def search_by_image(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        print(f"\n{'='*60}")
        print("[DEBUG VectorStore.search_by_image] 图像向量搜索")
        print(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        print(f"  - 查询向量维度: {len(query)}")
        print(f"  - 候选条目数: {len(self._image_embeddings)}")
        
        results = []
        
        for photo_id, emb in self._image_embeddings.items():
            sim = self.cosine_similarity(query, emb)
            
            entry = self._entries.get(photo_id)
            desc = entry.description if entry else ""
            
            print(f"  [比较] photo_id={photo_id}, similarity={sim:.6f}")
            results.append((photo_id, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n[DEBUG VectorStore.search_by_image] 搜索结果 (top {min(top_k, len(results))}):")
        for i, (pid, sim) in enumerate(results[:top_k]):
            print(f"  {i+1}. photo_id={pid}, similarity={sim:.6f}")
        
        print(f"{'='*60}\n")
        return results[:top_k]
    
    def search_combined(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        print(f"\n{'='*60}")
        print("[DEBUG VectorStore.search_combined] 组合向量搜索")
        print(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        print(f"  - 查询向量维度: {len(query)}")
        print(f"  - 查询向量统计:")
        print(f"    - min: {query.min():.6f}")
        print(f"    - max: {query.max():.6f}")
        print(f"    - mean: {query.mean():.6f}")
        print(f"    - L2 norm: {np.linalg.norm(query):.6f}")
        print(f"  - 总条目数: {len(self._entries)}")
        print(f"  - 文本嵌入数: {len(self._text_embeddings)}")
        print(f"  - 图像嵌入数: {len(self._image_embeddings)}")
        
        results = []
        
        print(f"\n[DEBUG VectorStore.search_combined] 开始逐一比较:")
        for photo_id in self._entries:
            entry = self._entries[photo_id]
            max_sim = 0.0
            best_source = "无"
            
            print(f"\n  --- photo_id={photo_id} ---")
            print(f"      description: '{entry.description}'")
            print(f"      tags: '{entry.tags}'")
            
            if photo_id in self._text_embeddings:
                emb = self._text_embeddings[photo_id]
                text_sim = self.cosine_similarity(query, emb)
                print(f"      文本相似度: {text_sim:.6f} (嵌入维度: {len(emb)})")
                
                if text_sim > max_sim:
                    max_sim = text_sim
                    best_source = "文本"
            
            if photo_id in self._image_embeddings:
                emb = self._image_embeddings[photo_id]
                image_sim = self.cosine_similarity(query, emb)
                print(f"      图像相似度: {image_sim:.6f} (嵌入维度: {len(emb)})")
                
                if image_sim > max_sim:
                    max_sim = image_sim
                    best_source = "图像"
            
            print(f"      最大相似度: {max_sim:.6f} (来源: {best_source})")
            
            if max_sim > 0:
                results.append((photo_id, max_sim, best_source))
        
        results_with_source = results
        results = [(r[0], r[1]) for r in results]
        results.sort(key=lambda x: x[1], reverse=True)
        results_with_source.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n{'='*60}")
        print("[DEBUG VectorStore.search_combined] 最终搜索结果")
        print(f"{'='*60}")
        print(f"  总匹配数: {len(results)}")
        print(f"\n  Top {min(top_k, len(results))} 结果:")
        for i, (pid, sim, source) in enumerate(results_with_source[:top_k]):
            entry = self._entries.get(pid)
            desc = entry.description if entry else ""
            print(f"  {i+1}. photo_id={pid}")
            print(f"     相似度: {sim:.6f} ({sim*100:.2f}%)")
            print(f"     来源: {source}")
            print(f"     描述: '{desc}'")
            print(f"     标签: '{entry.tags if entry else ''}'")
        
        print(f"{'='*60}\n")
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
