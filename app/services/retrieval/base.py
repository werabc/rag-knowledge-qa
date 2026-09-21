"""
召回策略基础类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RetrievalResult:
    """召回结果数据类"""
    content: str
    score: float
    metadata: Dict[str, Any]
    retrieval_method: str
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    
    def __post_init__(self):
        """后处理"""
        if not self.doc_id and "doc_id" in self.metadata:
            self.doc_id = self.metadata["doc_id"]
        if not self.chunk_id and "chunk_id" in self.metadata:
            self.chunk_id = self.metadata["chunk_id"]

class BaseRetriever(ABC):
    """召回策略基类"""
    
    def __init__(self, top_k: int = 10):
        """
        初始化召回器
        
        Args:
            top_k: 返回结果数量
        """
        self.top_k = top_k
    
    @abstractmethod
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """
        召回文档
        
        Args:
            query: 查询文本
            **kwargs: 额外参数
            
        Returns:
            List[RetrievalResult]: 召回结果列表
        """
        pass
    
    async def retrieve_with_filter(self, query: str, 
                                  filter_criteria: Dict[str, Any] = None,
                                  **kwargs) -> List[RetrievalResult]:
        """
        带过滤条件的召回
        
        Args:
            query: 查询文本
            filter_criteria: 过滤条件
            **kwargs: 额外参数
            
        Returns:
            List[RetrievalResult]: 召回结果列表
        """
        results = await self.retrieve(query, **kwargs)
        
        if filter_criteria:
            results = self._apply_filters(results, filter_criteria)
        
        return results
    
    def _apply_filters(self, results: List[RetrievalResult],
                      filter_criteria: Dict[str, Any]) -> List[RetrievalResult]:
        """应用过滤条件"""
        filtered_results = []
        
        for result in results:
            match = True
            for key, value in filter_criteria.items():
                if key in result.metadata:
                    if result.metadata[key] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            
            if match:
                filtered_results.append(result)
        
        return filtered_results