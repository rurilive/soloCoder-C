import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from app.logger import get_logger

logger = get_logger()


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
        
        logger.info(f"[VectorStore] 初始化...")
        logger.info(f"  - 存储路径: {self.store_path}")
        logger.info(f"  - 元数据文件: {self.metadata_file}")
        logger.info(f"  - 向量文件: {self.vectors_file}")
        
        os.makedirs(store_path, exist_ok=True)
        
        self._entries: Dict[int, VectorEntry] = {}
        self._text_embeddings: Dict[int, np.ndarray] = {}
        self._image_embeddings: Dict[int, np.ndarray] = {}
        
        self._load()
        
        logger.info(f"[VectorStore] 加载完成:")
        logger.info(f"  - 条目总数: {len(self._entries)}")
        logger.info(f"  - 文本嵌入数: {len(self._text_embeddings)}")
        logger.info(f"  - 图像嵌入数: {len(self._image_embeddings)}")
    
    def _load(self):
        logger.debug(f"[VectorStore._load] 开始加载数据...")
        
        if os.path.exists(self.metadata_file):
            logger.debug(f"[VectorStore._load] 从 {self.metadata_file} 加载元数据")
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                entries = metadata.get("entries", [])
                logger.debug(f"[VectorStore._load] 元数据中有 {len(entries)} 个条目")
                
                for i, entry_data in enumerate(entries):
                    entry = VectorEntry.from_dict(entry_data)
                    self._entries[entry.photo_id] = entry
                    logger.debug(f"    [{i+1}] photo_id={entry.photo_id}, description='{entry.description}', tags='{entry.tags}'")
        else:
            logger.debug(f"[VectorStore._load] 元数据文件不存在: {self.metadata_file}")
        
        if os.path.exists(self.vectors_file):
            logger.debug(f"[VectorStore._load] 从 {self.vectors_file} 加载向量")
            data = np.load(self.vectors_file, allow_pickle=True)
            
            text_count = 0
            image_count = 0
            
            for key in data.files:
                if key.startswith("text_"):
                    photo_id = int(key.replace("text_", ""))
                    self._text_embeddings[photo_id] = data[key]
                    text_count += 1
                    logger.debug(f"    [文本] photo_id={photo_id}, 维度={len(data[key])}")
                elif key.startswith("image_"):
                    photo_id = int(key.replace("image_", ""))
                    self._image_embeddings[photo_id] = data[key]
                    image_count += 1
                    logger.debug(f"    [图像] photo_id={photo_id}, 维度={len(data[key])}")
            
            logger.debug(f"[VectorStore._load] 向量加载完成: 文本={text_count}, 图像={image_count}")
        else:
            logger.debug(f"[VectorStore._load] 向量文件不存在: {self.vectors_file}")
    
    def _save(self):
        logger.debug(f"[VectorStore._save] 开始保存数据...")
        
        metadata = {
            "entries": [entry.to_dict() for entry in self._entries.values()]
        }
        
        logger.debug(f"[VectorStore._save] 保存元数据到 {self.metadata_file}")
        logger.debug(f"  - 条目数: {len(metadata['entries'])}")
        
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        vectors_to_save = {}
        for photo_id, emb in self._text_embeddings.items():
            vectors_to_save[f"text_{photo_id}"] = emb
        for photo_id, emb in self._image_embeddings.items():
            vectors_to_save[f"image_{photo_id}"] = emb
        
        if vectors_to_save:
            logger.debug(f"[VectorStore._save] 保存向量到 {self.vectors_file}")
            logger.debug(f"  - 向量数: {len(vectors_to_save)}")
            np.savez(self.vectors_file, **vectors_to_save)
        else:
            logger.debug(f"[VectorStore._save] 没有向量需要保存")
            if os.path.exists(self.vectors_file):
                os.remove(self.vectors_file)
                logger.debug(f"[VectorStore._save] 已删除空的向量文件")
    
    def add_entry(
        self,
        photo_id: int,
        text_embedding: Optional[List[float]] = None,
        image_embedding: Optional[List[float]] = None,
        description: str = "",
        tags: str = "",
    ):
        logger.info(f"[VectorStore.add_entry] 添加向量条目:")
        logger.info(f"  - photo_id: {photo_id}")
        logger.info(f"  - description: '{description}'")
        logger.info(f"  - tags: '{tags}'")
        logger.info(f"  - 文本嵌入: {'有' if text_embedding else '无'}")
        logger.info(f"  - 图像嵌入: {'有' if image_embedding else '无'}")
        
        entry = VectorEntry(
            photo_id=photo_id,
            description=description,
            tags=tags,
        )
        self._entries[photo_id] = entry
        
        if text_embedding is not None:
            logger.debug(f"[VectorStore.add_entry] 保存文本嵌入，维度: {len(text_embedding)}")
            self._text_embeddings[photo_id] = np.array(text_embedding, dtype=np.float32)
        
        if image_embedding is not None:
            logger.debug(f"[VectorStore.add_entry] 保存图像嵌入，维度: {len(image_embedding)}")
            self._image_embeddings[photo_id] = np.array(image_embedding, dtype=np.float32)
        
        self._save()
        logger.info(f"[VectorStore.add_entry] ✅ 已保存到向量存储")
    
    def remove_entry(self, photo_id: int):
        logger.info(f"[VectorStore.remove_entry] 删除向量条目 photo_id={photo_id}")
        
        removed = False
        if photo_id in self._entries:
            del self._entries[photo_id]
            logger.debug(f"  - 已删除元数据")
            removed = True
        if photo_id in self._text_embeddings:
            del self._text_embeddings[photo_id]
            logger.debug(f"  - 已删除文本嵌入")
            removed = True
        if photo_id in self._image_embeddings:
            del self._image_embeddings[photo_id]
            logger.debug(f"  - 已删除图像嵌入")
            removed = True
        
        if removed:
            self._save()
            logger.info(f"[VectorStore.remove_entry] ✅ 已删除")
        else:
            logger.warning(f"[VectorStore.remove_entry] ⚠️ 未找到该条目")
    
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
        logger.debug(f"[VectorStore.search_by_text] 文本向量搜索")
        
        query = np.array(query_embedding, dtype=np.float32)
        logger.debug(f"  - 查询向量维度: {len(query)}")
        logger.debug(f"  - 候选条目数: {len(self._text_embeddings)}")
        
        results = []
        
        for photo_id, emb in self._text_embeddings.items():
            sim = self.cosine_similarity(query, emb)
            
            entry = self._entries.get(photo_id)
            desc = entry.description if entry else ""
            
            logger.debug(f"    [比较] photo_id={photo_id}, similarity={sim:.6f}, desc='{desc[:30] if desc else '空'}...'")
            
            results.append((photo_id, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"[VectorStore.search_by_text] 搜索结果 (top {min(top_k, len(results))}):")
        for i, (pid, sim) in enumerate(results[:top_k]):
            entry = self._entries.get(pid)
            desc = entry.description if entry else ""
            logger.debug(f"    {i+1}. photo_id={pid}, similarity={sim:.6f}, desc='{desc[:50] if desc else '空'}'")
        
        return results[:top_k]
    
    def search_by_image(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        logger.debug(f"[VectorStore.search_by_image] 图像向量搜索")
        
        query = np.array(query_embedding, dtype=np.float32)
        logger.debug(f"  - 查询向量维度: {len(query)}")
        logger.debug(f"  - 候选条目数: {len(self._image_embeddings)}")
        
        results = []
        
        for photo_id, emb in self._image_embeddings.items():
            sim = self.cosine_similarity(query, emb)
            logger.debug(f"    [比较] photo_id={photo_id}, similarity={sim:.6f}")
            results.append((photo_id, sim))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"[VectorStore.search_by_image] 搜索结果 (top {min(top_k, len(results))}):")
        for i, (pid, sim) in enumerate(results[:top_k]):
            logger.debug(f"    {i+1}. photo_id={pid}, similarity={sim:.6f}")
        
        return results[:top_k]
    
    def search_combined(
        self,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        logger.info(f"\n{'='*60}")
        logger.info(f"[VectorStore.search_combined] 组合向量搜索")
        logger.info(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        logger.info(f"  - 查询向量维度: {len(query)}")
        logger.info(f"  - 查询向量统计:")
        logger.info(f"    - min: {query.min():.6f}")
        logger.info(f"    - max: {query.max():.6f}")
        logger.info(f"    - mean: {query.mean():.6f}")
        logger.info(f"    - L2 norm: {np.linalg.norm(query):.6f}")
        logger.info(f"  - 总条目数: {len(self._entries)}")
        logger.info(f"  - 文本嵌入数: {len(self._text_embeddings)}")
        logger.info(f"  - 图像嵌入数: {len(self._image_embeddings)}")
        
        if len(self._entries) == 0:
            logger.warning(f"[VectorStore.search_combined] ⚠️ 向量存储中没有任何条目！")
            logger.warning(f"  可能的原因:")
            logger.warning(f"  1. 上传照片时没有添加描述/标签")
            logger.warning(f"  2. 上传照片时 OpenAI API 调用失败")
            logger.warning(f"  3. 向量存储文件损坏或未正确保存")
        
        logger.info(f"\n[VectorStore.search_combined] 开始逐一比较:")
        results_with_source = []
        
        for photo_id in self._entries:
            entry = self._entries[photo_id]
            max_sim = 0.0
            best_source = "无"
            
            logger.info(f"\n  --- photo_id={photo_id} ---")
            logger.info(f"      description: '{entry.description}'")
            logger.info(f"      tags: '{entry.tags}'")
            
            if photo_id in self._text_embeddings:
                emb = self._text_embeddings[photo_id]
                text_sim = self.cosine_similarity(query, emb)
                logger.info(f"      文本相似度: {text_sim:.6f} (嵌入维度: {len(emb)})")
                
                if text_sim > max_sim:
                    max_sim = text_sim
                    best_source = "文本"
            
            if photo_id in self._image_embeddings:
                emb = self._image_embeddings[photo_id]
                image_sim = self.cosine_similarity(query, emb)
                logger.info(f"      图像相似度: {image_sim:.6f} (嵌入维度: {len(emb)})")
                
                if image_sim > max_sim:
                    max_sim = image_sim
                    best_source = "图像"
            
            logger.info(f"      最大相似度: {max_sim:.6f} (来源: {best_source})")
            
            if max_sim > 0:
                results_with_source.append((photo_id, max_sim, best_source))
        
        results_with_source.sort(key=lambda x: x[1], reverse=True)
        results = [(r[0], r[1]) for r in results_with_source]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[VectorStore.search_combined] 最终搜索结果")
        logger.info(f"{'='*60}")
        logger.info(f"  总匹配数: {len(results)}")
        
        if len(results) > 0:
            logger.info(f"\n  Top {min(top_k, len(results))} 结果:")
            for i, (pid, sim, source) in enumerate(results_with_source[:top_k]):
                entry = self._entries.get(pid)
                desc = entry.description if entry else ""
                tags = entry.tags if entry else ""
                logger.info(f"  {i+1}. photo_id={pid}")
                logger.info(f"     相似度: {sim:.6f} ({sim*100:.2f}%)")
                logger.info(f"     来源: {source}")
                logger.info(f"     描述: '{desc}'")
                logger.info(f"     标签: '{tags}'")
        else:
            logger.warning(f"  ⚠️ 没有找到任何匹配的结果")
            logger.warning(f"     可能的原因:")
            logger.warning(f"     1. 没有任何条目有文本/图像嵌入")
            logger.warning(f"     2. 相似度计算结果都为 0")
        
        logger.info(f"{'='*60}\n")
        
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
