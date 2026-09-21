"""
结构化召回策略
"""

import re
from typing import List, Dict, Any, Optional
from .base import BaseRetriever, RetrievalResult

class StructuralRetriever(BaseRetriever):
    """基于文档结构的召回器"""
    
    def __init__(self, document_parser, top_k: int = 10):
        """
        初始化结构化召回器
        
        Args:
            document_parser: 文档解析器
            top_k: 返回结果数量
        """
        super().__init__(top_k)
        self.parser = document_parser
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """
        基于文档结构的检索
        
        Args:
            query: 查询文本
            **kwargs: 额外参数（document_id等）
            
        Returns:
            List[RetrievalResult]: 召回结果列表
        """
        document_id = kwargs.get("document_id")
        if not document_id:
            return []
        
        try:
            # 1. 解析文档结构
            structure = await self.parser.parse_structure(document_id)
            
            # 2. 基于标题的检索
            title_matches = self._search_by_title(query, structure.get("titles", []))
            
            # 3. 基于章节的检索
            section_matches = self._search_by_section(query, structure.get("sections", []))
            
            # 4. 基于关键词的检索
            keyword_matches = self._search_by_keywords(query, structure.get("keywords", []))
            
            # 5. 合并结果
            all_results = title_matches + section_matches + keyword_matches
            
            # 6. 去重和排序
            unique_results = self._deduplicate_and_rank(all_results)
            
            return unique_results[:self.top_k]
            
        except Exception as e:
            print(f"结构化检索失败: {e}")
            return []
    
    def _search_by_title(self, query: str, titles: List[Dict]) -> List[RetrievalResult]:
        """标题匹配检索"""
        results = []
        
        for title_info in titles:
            title_text = title_info.get("text", "")
            title_content = title_info.get("content", "")
            
            # 计算标题与查询的相似度
            similarity = self._compute_text_similarity(query, title_text)
            
            if similarity > 0.3:  # 标题匹配阈值
                result = RetrievalResult(
                    content=title_content,
                    score=similarity * 1.5,  # 标题加权
                    metadata={
                        "match_type": "title",
                        "title": title_text,
                        "level": title_info.get("level", 0)
                    },
                    retrieval_method="structural_title"
                )
                results.append(result)
        
        return results
    
    def _search_by_section(self, query: str, sections: List[Dict]) -> List[RetrievalResult]:
        """章节检索"""
        results = []
        
        for section in sections:
            section_title = section.get("title", "")
            section_content = section.get("content", "")
            
            # 计算章节内容与查询的相似度
            similarity = self._compute_text_similarity(query, section_content)
            
            if similarity > 0.2:  # 章节匹配阈值
                result = RetrievalResult(
                    content=section_content,
                    score=similarity,
                    metadata={
                        "match_type": "section",
                        "section_title": section_title,
                        "section_level": section.get("level", 0)
                    },
                    retrieval_method="structural_section"
                )
                results.append(result)
        
        return results
    
    def _search_by_keywords(self, query: str, keywords: List[Dict]) -> List[RetrievalResult]:
        """关键词检索"""
        results = []
        
        for keyword_info in keywords:
            keyword = keyword_info.get("keyword", "")
            keyword_context = keyword_info.get("context", "")
            
            # 计算关键词与查询的相关性
            relevance = self._compute_keyword_relevance(query, keyword)
            
            if relevance > 0.4:  # 关键词匹配阈值
                result = RetrievalResult(
                    content=keyword_context,
                    score=relevance,
                    metadata={
                        "match_type": "keyword",
                        "keyword": keyword,
                        "importance": keyword_info.get("importance", 0)
                    },
                    retrieval_method="structural_keyword"
                )
                results.append(result)
        
        return results
    
    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 使用Jaccard相似度
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _compute_keyword_relevance(self, query: str, keyword: str) -> float:
        """计算关键词相关性"""
        # 简单实现：检查关键词是否在查询中
        if keyword in query:
            return 1.0
        
        # 检查查询中的词是否包含关键词的子词
        query_words = set(query.split())
        keyword_parts = set(keyword.split())
        
        if not keyword_parts:
            return 0.0
        
        overlap = len(query_words.intersection(keyword_parts))
        return overlap / len(keyword_parts)
    
    def _deduplicate_and_rank(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """去重和排序"""
        # 基于内容去重
        unique_contents = set()
        unique_results = []
        
        for result in results:
            # 内容指纹（取前200字符）
            content_fingerprint = result.content[:200]
            
            if content_fingerprint not in unique_contents:
                unique_contents.add(content_fingerprint)
                unique_results.append(result)
        
        # 按分数排序
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results