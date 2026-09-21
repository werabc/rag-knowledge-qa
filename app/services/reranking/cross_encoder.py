"""
Cross-Encoder重排序
"""

import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseReranker

class CrossEncoderReranker(BaseReranker):
    """基于Cross-Encoder的重排序器"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 batch_size: int = 32):
        """
        初始化Cross-Encoder重排序器
        
        Args:
            model_name: 模型名称
            batch_size: 批处理大小
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = None  # 延迟加载
    
    def _load_model(self):
        """加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(self.model_name)
                print(f"✅ Cross-Encoder模型加载成功: {self.model_name}")
            except Exception as e:
                print(f"❌ Cross-Encoder模型加载失败: {e}")
                self.model = None
    
    async def rerank(self, query: str, candidates: List[Dict], 
                    top_k: int = None, **kwargs) -> List[Dict]:
        """
        Cross-Encoder重排序
        
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
        
        # 加载模型
        self._load_model()
        
        if self.model is None:
            # 模型加载失败，返回原始排序
            print("⚠️  Cross-Encoder模型未加载，返回原始排序")
            return candidates[:top_k] if top_k else candidates
        
        try:
            # 1. 准备输入对
            query_doc_pairs = []
            for candidate in candidates:
                content = candidate.get("content", "")
                # 截断过长的文本
                if len(content) > 512:
                    content = content[:512] + "..."
                query_doc_pairs.append((query, content))
            
            # 2. 批量预测相关性分数
            scores = []
            for i in range(0, len(query_doc_pairs), self.batch_size):
                batch = query_doc_pairs[i:i + self.batch_size]
                batch_scores = self.model.predict(batch)
                scores.extend(batch_scores.tolist() if hasattr(batch_scores, 'tolist') else batch_scores)
            
            # 3. 添加重排序分数
            reranked_results = []
            for i, (candidate, score) in enumerate(zip(candidates, scores)):
                reranked = candidate.copy()
                reranked["rerank_score"] = float(score)
                reranked["original_rank"] = i
                reranked["rerank_method"] = "cross_encoder"
                reranked_results.append(reranked)
            
            # 4. 按重排序分数排序
            reranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            # 5. 返回top-k结果
            if top_k:
                reranked_results = reranked_results[:top_k]
            
            return reranked_results
            
        except Exception as e:
            print(f"❌ Cross-Encoder重排序失败: {e}")
            return candidates[:top_k] if top_k else candidates
    
    async def batch_rerank(self, queries: List[str], 
                          candidates_list: List[List[Dict]],
                          top_k: int = None) -> List[List[Dict]]:
        """
        批量重排序
        
        Args:
            queries: 查询列表
            candidates_list: 每个查询的候选结果列表
            top_k: 每个查询返回的结果数量
            
        Returns:
            List[List[Dict]]: 每个查询重排序后的结果
        """
        results = []
        for query, candidates in zip(queries, candidates_list):
            reranked = await self.rerank(query, candidates, top_k)
            results.append(reranked)
        
        return results