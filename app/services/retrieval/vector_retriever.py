"""
向量召回策略
"""

import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseRetriever, RetrievalResult

class VectorRetriever(BaseRetriever):
    """基于向量相似度的召回器"""
    
    def __init__(self, embedding_model, vector_db, top_k: int = 10,
                 similarity_threshold: float = 0.5):
        """
        初始化向量召回器
        
        Args:
            embedding_model: 嵌入模型
            vector_db: 向量数据库
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
        """
        super().__init__(top_k)
        self.embedding_model = embedding_model
        self.vector_db = vector_db
        self.similarity_threshold = similarity_threshold
        
        # 检索参数
        self.search_params = {
            "ef_search": 128,
            "metric_type": "cosine"
        }
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """
        向量检索
        
        Args:
            query: 查询文本
            **kwargs: 额外参数
            
        Returns:
            List[RetrievalResult]: 召回结果列表
        """
        try:
            # 1. 查询向量化
            query_embedding = await self.embedding_model.embed(query)
            
            # 2. 向量检索
            search_results = await self.vector_db.search(
                vector=query_embedding,
                top_k=self.top_k,
                params=self.search_params
            )
            
            # 3. 过滤低相似度结果
            filtered_results = []
            for result in search_results:
                if result.score >= self.similarity_threshold:
                    retrieval_result = RetrievalResult(
                        content=result.content,
                        score=result.score,
                        metadata=result.metadata,
                        retrieval_method="vector",
                        doc_id=result.metadata.get("doc_id"),
                        chunk_id=result.metadata.get("chunk_id")
                    )
                    filtered_results.append(retrieval_result)
            
            return filtered_results
            
        except Exception as e:
            print(f"向量检索失败: {e}")
            return []
    
    async def batch_retrieve(self, queries: List[str], **kwargs) -> List[List[RetrievalResult]]:
        """
        批量向量检索
        
        Args:
            queries: 查询列表
            **kwargs: 额外参数
            
        Returns:
            List[List[RetrievalResult]]: 每个查询的召回结果
        """
        results = []
        for query in queries:
            query_results = await self.retrieve(query, **kwargs)
            results.append(query_results)
        
        return results