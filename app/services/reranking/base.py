"""
重排序基础类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseReranker(ABC):
    """重排序基类"""
    
    @abstractmethod
    async def rerank(self, query: str, candidates: List[Dict], 
                    top_k: int = None, **kwargs) -> List[Dict]:
        """
        重排序候选结果
        
        Args:
            query: 查询文本
            candidates: 候选结果列表
            top_k: 返回结果数量
            **kwargs: 额外参数
            
        Returns:
            List[Dict]: 重排序后的结果列表
        """
        pass
    
    def _normalize_scores(self, results: List[Dict]) -> List[Dict]:
        """归一化分数到[0,1]区间"""
        if not results:
            return results
        
        scores = [r.get("score", 0) for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score - min_score == 0:
            # 所有分数相同
            for result in results:
                result["normalized_score"] = 1.0
        else:
            for result in results:
                score = result.get("score", 0)
                result["normalized_score"] = (score - min_score) / (max_score - min_score)
        
        return results