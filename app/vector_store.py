import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from app.logger import get_logger
from app.config import config

logger = get_logger()


def filter_results_by_threshold(
    results: List[Tuple[int, float, str]],
    threshold: float,
) -> Tuple[List[Tuple[int, float, str]], int]:
    logger.debug(f"\n[filter_results_by_threshold] 开始阈值过滤")
    logger.debug(f"  - 输入结果数: {len(results)}")
    logger.debug(f"  - 阈值: {threshold}")
    
    filtered = []
    filtered_count = 0
    
    for pid, sim, source in results:
        if sim >= threshold:
            logger.debug(f"    ✅ [保留] photo_id={pid}, similarity={sim:.6f} (>= {threshold}), source={source}")
            filtered.append((pid, sim, source))
        else:
            logger.debug(f"    ❌ [过滤] photo_id={pid}, similarity={sim:.6f} (< {threshold}), source={source}")
            filtered_count += 1
    
    logger.debug(f"[filter_results_by_threshold] 过滤完成:")
    logger.debug(f"  - 保留: {len(filtered)}")
    logger.debug(f"  - 过滤: {filtered_count}")
    
    return filtered, filtered_count


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
        logger.info(f"  - 相似度阈值: {config.VECTOR_SEARCH_SIMILARITY_THRESHOLD}")
        logger.info(f"  - 最大结果数: {config.VECTOR_SEARCH_TOP_K}")
        
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
        
        logger.debug(f"        [cosine_similarity] 向量信息:")
        logger.debug(f"          - 查询向量 L2 范数: {norm_a:.6f}")
        logger.debug(f"          - 候选向量 L2 范数: {norm_b:.6f}")
        
        if norm_a == 0 or norm_b == 0:
            logger.warning(f"        [cosine_similarity] ⚠️ 向量范数为0，相似度返回0.0")
            logger.warning(f"          - 查询向量统计: min={a.min():.6f}, max={a.max():.6f}, mean={a.mean():.6f}")
            logger.warning(f"          - 候选向量统计: min={b.min():.6f}, max={b.max():.6f}, mean={b.mean():.6f}")
            return 0.0
        
        dot_product = np.dot(a, b)
        similarity = float(dot_product / (norm_a * norm_b))
        
        logger.debug(f"          - 点积 (dot_product): {dot_product:.6f}")
        logger.debug(f"          - 相似度 = {dot_product:.6f} / ({norm_a:.6f} * {norm_b:.6f})")
        logger.debug(f"          - 相似度 = {similarity:.6f} ({similarity*100:.2f}%)")
        
        if similarity < 0:
            logger.warning(f"        [cosine_similarity] ⚠️ 相似度为负值: {similarity:.6f}")
            logger.warning(f"          - 这可能表示向量方向相反，通常是异常情况")
        
        return similarity
    
    def search_by_text(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
    ) -> List[Tuple[int, float]]:
        logger.debug(f"\n{'='*60}")
        logger.debug(f"[VectorStore.search_by_text] 文本向量搜索")
        logger.debug(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        logger.debug(f"  - 查询向量维度: {len(query)}")
        logger.debug(f"  - 查询向量统计:")
        logger.debug(f"    - min: {query.min():.6f}")
        logger.debug(f"    - max: {query.max():.6f}")
        logger.debug(f"    - mean: {query.mean():.6f}")
        logger.debug(f"    - L2 norm: {np.linalg.norm(query):.6f}")
        logger.debug(f"  - 候选文本嵌入数: {len(self._text_embeddings)}")
        
        if threshold is None:
            threshold = config.VECTOR_SEARCH_SIMILARITY_THRESHOLD
        
        logger.debug(f"  - 相似度阈值: {threshold}")
        
        if len(self._text_embeddings) == 0:
            logger.warning(f"[VectorStore.search_by_text] ⚠️ 没有任何文本嵌入！")
            logger.warning(f"  可能的原因:")
            logger.warning(f"  1. 上传照片时没有添加描述/标签")
            logger.warning(f"  2. 上传照片时 OpenAI API 调用失败")
            logger.warning(f"  3. 向量存储文件损坏或未正确保存")
            return []
        
        logger.debug(f"\n[VectorStore.search_by_text] 开始文本相似度比较:")
        results = []
        all_scores = []
        
        for photo_id, emb in self._text_embeddings.items():
            logger.debug(f"\n    --- 比较 photo_id={photo_id} ---")
            entry = self._entries.get(photo_id)
            if entry:
                logger.debug(f"      description: '{entry.description}'")
                logger.debug(f"      tags: '{entry.tags}'")
            
            logger.debug(f"      候选向量统计:")
            logger.debug(f"        - 维度: {len(emb)}")
            logger.debug(f"        - min: {emb.min():.6f}")
            logger.debug(f"        - max: {emb.max():.6f}")
            logger.debug(f"        - mean: {emb.mean():.6f}")
            logger.debug(f"        - L2 norm: {np.linalg.norm(emb):.6f}")
            
            sim = self.cosine_similarity(query, emb)
            all_scores.append((photo_id, sim))
            
            if sim >= threshold:
                desc = entry.description if entry else ""
                logger.debug(f"      ✅ [保留] similarity={sim:.6f} (>= {threshold})")
                results.append((photo_id, sim))
            else:
                logger.debug(f"      ❌ [过滤] similarity={sim:.6f} (< {threshold})")
        
        logger.debug(f"\n[VectorStore.search_by_text] 比较完成，开始排序...")
        logger.debug(f"  - 总比较数: {len(all_scores)}")
        logger.debug(f"  - 通过阈值: {len(results)}")
        logger.debug(f"  - 被过滤: {len(all_scores) - len(results)}")
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"\n[VectorStore.search_by_text] 最终结果 (top {min(top_k, len(results))}):")
        logger.debug(f"{'='*60}")
        for i, (pid, sim) in enumerate(results[:top_k]):
            entry = self._entries.get(pid)
            desc = entry.description if entry else ""
            tags = entry.tags if entry else ""
            logger.debug(f"  {i+1}. photo_id={pid}")
            logger.debug(f"     相似度: {sim:.6f} ({sim*100:.2f}%)")
            logger.debug(f"     描述: '{desc}'")
            logger.debug(f"     标签: '{tags}'")
        
        if len(results) == 0 and len(all_scores) > 0:
            logger.warning(f"\n[VectorStore.search_by_text] ⚠️ 所有结果都被阈值过滤了！")
            logger.warning(f"  所有比较的相似度:")
            for pid, sim in all_scores:
                logger.warning(f"    photo_id={pid}, similarity={sim:.6f}")
            logger.warning(f"\n  建议降低 VECTOR_SEARCH_SIMILARITY_THRESHOLD (当前值: {threshold})")
        
        logger.debug(f"{'='*60}\n")
        return results[:top_k]
    
    def search_by_image(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
    ) -> List[Tuple[int, float]]:
        logger.debug(f"\n{'='*60}")
        logger.debug(f"[VectorStore.search_by_image] 图像向量搜索")
        logger.debug(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        logger.debug(f"  - 查询向量维度: {len(query)}")
        logger.debug(f"  - 查询向量统计:")
        logger.debug(f"    - min: {query.min():.6f}")
        logger.debug(f"    - max: {query.max():.6f}")
        logger.debug(f"    - mean: {query.mean():.6f}")
        logger.debug(f"    - L2 norm: {np.linalg.norm(query):.6f}")
        logger.debug(f"  - 候选图像嵌入数: {len(self._image_embeddings)}")
        
        if threshold is None:
            threshold = config.VECTOR_SEARCH_SIMILARITY_THRESHOLD
        
        logger.debug(f"  - 相似度阈值: {threshold}")
        
        if len(self._image_embeddings) == 0:
            logger.warning(f"[VectorStore.search_by_image] ⚠️ 没有任何图像嵌入！")
            logger.warning(f"  注意: 当前系统只支持文本嵌入，图像嵌入功能可能未实现")
            return []
        
        logger.debug(f"\n[VectorStore.search_by_image] 开始图像相似度比较:")
        results = []
        all_scores = []
        
        for photo_id, emb in self._image_embeddings.items():
            logger.debug(f"\n    --- 比较 photo_id={photo_id} ---")
            entry = self._entries.get(photo_id)
            if entry:
                logger.debug(f"      description: '{entry.description}'")
                logger.debug(f"      tags: '{entry.tags}'")
            
            logger.debug(f"      候选向量统计:")
            logger.debug(f"        - 维度: {len(emb)}")
            logger.debug(f"        - min: {emb.min():.6f}")
            logger.debug(f"        - max: {emb.max():.6f}")
            logger.debug(f"        - mean: {emb.mean():.6f}")
            logger.debug(f"        - L2 norm: {np.linalg.norm(emb):.6f}")
            
            sim = self.cosine_similarity(query, emb)
            all_scores.append((photo_id, sim))
            
            if sim >= threshold:
                logger.debug(f"      ✅ [保留] similarity={sim:.6f} (>= {threshold})")
                results.append((photo_id, sim))
            else:
                logger.debug(f"      ❌ [过滤] similarity={sim:.6f} (< {threshold})")
        
        logger.debug(f"\n[VectorStore.search_by_image] 比较完成，开始排序...")
        logger.debug(f"  - 总比较数: {len(all_scores)}")
        logger.debug(f"  - 通过阈值: {len(results)}")
        logger.debug(f"  - 被过滤: {len(all_scores) - len(results)}")
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"\n[VectorStore.search_by_image] 最终结果 (top {min(top_k, len(results))}):")
        logger.debug(f"{'='*60}")
        for i, (pid, sim) in enumerate(results[:top_k]):
            entry = self._entries.get(pid)
            desc = entry.description if entry else ""
            tags = entry.tags if entry else ""
            logger.debug(f"  {i+1}. photo_id={pid}")
            logger.debug(f"     相似度: {sim:.6f} ({sim*100:.2f}%)")
            logger.debug(f"     描述: '{desc}'")
            logger.debug(f"     标签: '{tags}'")
        
        if len(results) == 0 and len(all_scores) > 0:
            logger.warning(f"\n[VectorStore.search_by_image] ⚠️ 所有结果都被阈值过滤了！")
            logger.warning(f"  所有比较的相似度:")
            for pid, sim in all_scores:
                logger.warning(f"    photo_id={pid}, similarity={sim:.6f}")
            logger.warning(f"\n  建议降低 VECTOR_SEARCH_SIMILARITY_THRESHOLD (当前值: {threshold})")
        
        logger.debug(f"{'='*60}\n")
        return results[:top_k]
    
    def search_combined(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: Optional[float] = None,
    ) -> List[Tuple[int, float]]:
        logger.debug(f"\n{'='*60}")
        logger.debug(f"[VectorStore.search_combined] 组合向量搜索")
        logger.debug(f"{'='*60}")
        
        query = np.array(query_embedding, dtype=np.float32)
        logger.debug(f"  - 查询向量维度: {len(query)}")
        logger.debug(f"  - 查询向量统计:")
        logger.debug(f"    - min: {query.min():.6f}")
        logger.debug(f"    - max: {query.max():.6f}")
        logger.debug(f"    - mean: {query.mean():.6f}")
        logger.debug(f"    - L2 norm: {np.linalg.norm(query):.6f}")
        logger.debug(f"  - 总条目数: {len(self._entries)}")
        logger.debug(f"  - 文本嵌入数: {len(self._text_embeddings)}")
        logger.debug(f"  - 图像嵌入数: {len(self._image_embeddings)}")
        
        if threshold is None:
            threshold = config.VECTOR_SEARCH_SIMILARITY_THRESHOLD
        
        logger.debug(f"  - 配置的相似度阈值: {threshold}")
        
        if len(self._entries) == 0:
            logger.warning(f"[VectorStore.search_combined] ⚠️ 向量存储中没有任何条目！")
            logger.warning(f"  可能的原因:")
            logger.warning(f"  1. 上传照片时没有添加描述/标签")
            logger.warning(f"  2. 上传照片时 OpenAI API 调用失败")
            logger.warning(f"  3. 向量存储文件损坏或未正确保存")
        
        logger.debug(f"\n[VectorStore.search_combined] 开始逐一比较:")
        results_with_source = []
        total_count = 0
        
        for photo_id in self._entries:
            entry = self._entries[photo_id]
            max_sim = 0.0
            best_source = "无"
            
            logger.debug(f"\n  --- photo_id={photo_id} ---")
            logger.debug(f"      description: '{entry.description}'")
            logger.debug(f"      tags: '{entry.tags}'")
            
            if photo_id in self._text_embeddings:
                emb = self._text_embeddings[photo_id]
                text_sim = self.cosine_similarity(query, emb)
                logger.debug(f"      文本相似度: {text_sim:.6f} (嵌入维度: {len(emb)})")
                
                if text_sim > max_sim:
                    max_sim = text_sim
                    best_source = "文本"
            
            if photo_id in self._image_embeddings:
                emb = self._image_embeddings[photo_id]
                image_sim = self.cosine_similarity(query, emb)
                logger.debug(f"      图像相似度: {image_sim:.6f} (嵌入维度: {len(emb)})")
                
                if image_sim > max_sim:
                    max_sim = image_sim
                    best_source = "图像"
            
            logger.debug(f"      最大相似度: {max_sim:.6f} (来源: {best_source})")
            
            total_count += 1
            if max_sim >= threshold:
                logger.debug(f"      ✅ 满足阈值条件 (>= {threshold})，加入结果")
                results_with_source.append((photo_id, max_sim, best_source))
            else:
                logger.debug(f"      ❌ 不满足阈值条件 (< {threshold})，被过滤")
        
        results_with_source.sort(key=lambda x: x[1], reverse=True)
        results = [(r[0], r[1]) for r in results_with_source]
        
        filtered_count = total_count - len(results)
        
        logger.info(f"\n[VectorStore.search_combined] 搜索完成:")
        logger.info(f"  - 总比较数: {total_count}")
        logger.info(f"  - 通过阈值: {len(results)} (阈值: {threshold})")
        logger.info(f"  - 被过滤: {filtered_count}")
        
        if len(results) > 0:
            logger.debug(f"\n  Top {min(top_k, len(results))} 结果:")
            for i, (pid, sim, source) in enumerate(results_with_source[:top_k]):
                entry = self._entries.get(pid)
                desc = entry.description if entry else ""
                tags = entry.tags if entry else ""
                logger.debug(f"  {i+1}. photo_id={pid}")
                logger.debug(f"     相似度: {sim:.6f} ({sim*100:.2f}%)")
                logger.debug(f"     来源: {source}")
                logger.debug(f"     描述: '{desc}'")
                logger.debug(f"     标签: '{tags}'")
        else:
            logger.warning(f"  ⚠️ 没有找到任何匹配的结果")
            if filtered_count > 0:
                logger.warning(f"     所有 {filtered_count} 个候选都被阈值过滤掉了")
                logger.warning(f"     建议降低 VECTOR_SEARCH_SIMILARITY_THRESHOLD")
        
        logger.debug(f"{'='*60}\n")
        
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
