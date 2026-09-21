"""
多样性重排序
"""

import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseReranker

class DiversityReranker(BaseReranker):
    """基于多样性的重排序器"""
    
    def __init__(self, lambda_param: float = 0.7, 
                 diversity_metric: str = "mmr",
                 embedding_model=None):
        """
        初始化多样性重排序器
        
        Args:
            lambda_param: MMR参数，控制相关性和多样性的平衡
            diversity_metric: 多样性度量方法
            embedding_model: 嵌入模型
        """
        self.lambda_param = lambda_param
        self.diversity_metric = diversity_metric
        self.embedding_model = embedding_model
    
    async def rerank(self, query: str, candidates: List[Dict], 
                    top_k: int = None, **kwargs) -> List[Dict]:
        """
        多样性重排序
        
        Args:
            query: 查询文本
            candidates: 候选结果列表
            top_k: 返回结果数量
            **kwargs: 额外参数
            
        Returns:
            List[Dict]: 重排序后的结果列表
        """
        if not candidates:
            return []
        
        if top_k is None:
            top_k = len(candidates)
        
        if len(candidates) <= top_k:
            return candidates
        
        # 归一化分数
        candidates = self._normalize_scores(candidates)
        
        # 计算文档嵌入（如果需要）
        doc_embeddings = await self._compute_document_embeddings(candidates)
        
        if self.diversity_metric == "mmr":
            return await self._mmr_rerank(candidates, doc_embeddings, top_k)
        elif self.diversity_metric == "dpp":
            return await self._dpp_rerank(candidates, doc_embeddings, top_k)
        else:
            # 默认使用MMR
            return await self._mmr_rerank(candidates, doc_embeddings, top_k)
    
    async def _compute_document_embeddings(self, candidates: List[Dict]) -> List[List[float]]:
        """计算文档嵌入"""
        if not self.embedding_model:
            return []
        
        embeddings = []
        for candidate in candidates:
            content = candidate.get("content", "")
            try:
                embedding = await self.embedding_model.embed(content)
                embeddings.append(embedding)
            except Exception as e:
                print(f"计算文档嵌入失败: {e}")
                # 使用零向量作为后备
                embeddings.append([0.0] * 384)  # 假设嵌入维度为384
        
        return embeddings
    
    async def _mmr_rerank(self, candidates: List[Dict], 
                         doc_embeddings: List[List[float]],
                         top_k: int) -> List[Dict]:
        """最大边际相关性重排序"""
        if not doc_embeddings:
            # 没有嵌入，直接返回按分数排序的结果
            return candidates[:top_k]
        
        selected = []
        remaining = list(range(len(candidates)))
        
        # 选择第一个文档（最高分数）
        first_idx = np.argmax([c.get("normalized_score", 0) for c in candidates])
        selected.append(first_idx)
        remaining.remove(first_idx)
        
        # 迭代选择剩余文档
        while len(selected) < top_k and remaining:
            best_score = -float('inf')
            best_idx = -1
            
            for idx in remaining:
                # 相关性分数
                relevance = candidates[idx].get("normalized_score", 0)
                
                # 与已选文档的最大相似度
                max_similarity = 0
                for selected_idx in selected:
                    similarity = self._compute_similarity(
                        doc_embeddings[idx], 
                        doc_embeddings[selected_idx]
                    )
                    max_similarity = max(max_similarity, similarity)
                
                # MMR分数
                mmr_score = self.lambda_param * relevance - (1 - self.lambda_param) * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx != -1:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        # 构建结果
        result = []
        for idx in selected:
            candidate = candidates[idx].copy()
            candidate["diversity_score"] = candidates[idx].get("normalized_score", 0)
            candidate["diversity_method"] = "mmr"
            result.append(candidate)
        
        return result
    
    async def _dpp_rerank(self, candidates: List[Dict],
                         doc_embeddings: List[List[float]],
                         top_k: int) -> List[Dict]:
        """行列式点过程重排序"""
        if not doc_embeddings:
            return candidates[:top_k]
        
        n = len(candidates)
        
        # 构建相似度矩阵
        similarity_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    similarity_matrix[i][j] = self._compute_similarity(
                        doc_embeddings[i], doc_embeddings[j]
                    )
        
        # 构建质量向量（基于分数）
        quality = np.array([c.get("normalized_score", 0) for c in candidates])
        
        # 贪心DPP算法
        selected = self._greedy_dpp(similarity_matrix, quality, top_k)
        
        # 构建结果
        result = []
        for idx in selected:
            candidate = candidates[idx].copy()
            candidate["diversity_score"] = quality[idx]
            candidate["diversity_method"] = "dpp"
            result.append(candidate)
        
        return result
    
    def _greedy_dpp(self, similarity_matrix: np.ndarray, 
                   quality: np.ndarray, k: int) -> List[int]:
        """贪心DPP算法"""
        n = len(quality)
        selected = []
        
        # 初始化未选集合
        remaining = set(range(n))
        
        for _ in range(k):
            if not remaining:
                break
            
            best_score = -float('inf')
            best_idx = -1
            
            for idx in remaining:
                # 计算DPP分数
                # 简化版本：质量 * (1 - 与已选文档的相似度)
                if not selected:
                    score = quality[idx]
                else:
                    # 计算与已选文档的平均相似度
                    avg_similarity = np.mean([
                        similarity_matrix[idx][s] for s in selected
                    ])
                    score = quality[idx] * (1 - avg_similarity)
                
                if score > best_score:
                    best_score = score
                    best_idx = idx
            
            if best_idx != -1:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        return selected
    
    def _compute_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """计算余弦相似度"""
        if not emb1 or not emb2:
            return 0.0
        
        emb1 = np.array(emb1)
        emb2 = np.array(emb2)
        
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)