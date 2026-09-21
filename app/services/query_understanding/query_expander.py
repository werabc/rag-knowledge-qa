"""
查询扩展
"""

import re
from typing import List, Dict, Any, Optional

class QueryExpander:
    """查询扩展器"""
    
    def __init__(self, llm=None, expansion_factor: int = 3):
        """
        初始化查询扩展器
        
        Args:
            llm: 语言模型（可选）
            expansion_factor: 扩展因子
        """
        self.llm = llm
        self.expansion_factor = expansion_factor
        
        # 同义词词典（简化版）
        self.synonym_dict = {
            "机器学习": ["ML", "统计学习", "数据挖掘"],
            "深度学习": ["DL", "神经网络", "深度神经网络"],
            "人工智能": ["AI", "智能计算", "机器智能"],
            "自然语言处理": ["NLP", "文本处理", "语言理解"],
            "计算机视觉": ["CV", "图像处理", "视觉计算"],
            "算法": ["方法", "策略", "技术"],
            "系统": ["平台", "框架", "架构"],
            "数据": ["信息", "资料", "内容"],
            "模型": ["网络", "算法", "结构"],
            "训练": ["学习", "优化", "调整"],
            "测试": ["验证", "评估", "检验"],
            "部署": ["发布", "上线", "运行"],
        }
    
    async def expand_query(self, query: str) -> List[str]:
        """
        扩展查询
        
        Args:
            query: 原始查询
            
        Returns:
            List[str]: 扩展后的查询列表
        """
        expanded_queries = [query]  # 包含原始查询
        
        # 1. 同义词扩展
        synonym_expansions = await self._expand_with_synonyms(query)
        expanded_queries.extend(synonym_expansions)
        
        # 2. 上下位词扩展
        hierarchy_expansions = await self._expand_with_hierarchy(query)
        expanded_queries.extend(hierarchy_expansions)
        
        # 3. 查询重写（如果LLM可用）
        if self.llm:
            rewrite_expansions = await self._expand_with_rewrite(query)
            expanded_queries.extend(rewrite_expansions)
        
        # 去重和限制数量
        unique_queries = list(dict.fromkeys(expanded_queries))  # 保持顺序去重
        return unique_queries[:self.expansion_factor + 1]  # 包含原始查询
    
    async def _expand_with_synonyms(self, query: str) -> List[str]:
        """基于同义词的扩展"""
        expansions = []
        
        # 分词
        tokens = self._tokenize(query)
        
        # 为每个词查找同义词
        expanded_tokens = []
        for token in tokens:
            synonyms = self._get_synonyms(token)
            expanded_tokens.extend(synonyms[:2])  # 每个词最多2个同义词
        
        # 组合扩展查询
        if expanded_tokens:
            # 生成组合查询
            for i in range(min(2, len(expanded_tokens))):
                expanded_query = query + " " + expanded_tokens[i]
                expansions.append(expanded_query)
        
        return expansions
    
    async def _expand_with_hierarchy(self, query: str) -> List[str]:
        """基于上下位词的扩展"""
        expansions = []
        
        # 简化实现：添加更一般或更具体的术语
        keywords = self._extract_keywords(query)
        
        for keyword in keywords[:2]:  # 只处理前2个关键词
            # 添加上位词（更一般的词）
            hypernyms = self._get_hypernyms(keyword)
            for hypernym in hypernyms[:1]:
                expanded_query = query + " " + hypernym
                expansions.append(expanded_query)
            
            # 添加下位词（更具体的词）
            hyponyms = self._get_hyponyms(keyword)
            for hyponym in hyponyms[:1]:
                expanded_query = query + " " + hyponym
                expansions.append(expanded_query)
        
        return expansions
    
    async def _expand_with_rewrite(self, query: str) -> List[str]:
        """基于LLM的查询重写"""
        if not self.llm:
            return []
        
        try:
            prompt = f"""基于以下原始查询，生成{self.expansion_factor}个语义相似但表述不同的查询：

原始查询：{query}

请提供{self.expansion_factor}个扩展查询，每行一个："""
            
            response = await self.llm.generate(prompt)
            expanded = response.strip().split('\n')
            
            # 过滤空行和过长的查询
            filtered_expansions = []
            for exp in expanded:
                exp = exp.strip()
                if exp and len(exp) < 200 and exp != query:
                    filtered_expansions.append(exp)
            
            return filtered_expansions[:self.expansion_factor]
            
        except Exception as e:
            print(f"LLM查询重写失败: {e}")
            return []
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单的分词：按空格和标点分割
        tokens = re.split(r'[，。！？、；：""''（）\[\]{}，\.\!\?\,\;\:\'\"\(\)\[\]\{\}\s]+', text)
        return [t for t in tokens if t.strip()]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取较长的词
        tokens = self._tokenize(text)
        keywords = [t for t in tokens if len(t) >= 2]
        return keywords[:5]  # 返回前5个关键词
    
    def _get_synonyms(self, word: str) -> List[str]:
        """获取同义词"""
        return self.synonym_dict.get(word, [])
    
    def _get_hypernyms(self, word: str) -> List[str]:
        """获取上位词（简化实现）"""
        # 这里可以集成WordNet或自定义词典
        hypernym_dict = {
            "机器学习": ["人工智能", "数据挖掘"],
            "深度学习": ["机器学习", "神经网络"],
            "自然语言处理": ["人工智能", "文本处理"],
            "计算机视觉": ["人工智能", "图像处理"],
            "算法": ["方法", "技术"],
            "模型": ["网络", "结构"],
        }
        
        return hypernym_dict.get(word, [])
    
    def _get_hyponyms(self, word: str) -> List[str]:
        """获取下位词（简化实现）"""
        # 这里可以集成WordNet或自定义词典
        hyponym_dict = {
            "人工智能": ["机器学习", "深度学习", "自然语言处理", "计算机视觉"],
            "机器学习": ["监督学习", "无监督学习", "强化学习"],
            "深度学习": ["卷积神经网络", "循环神经网络", "Transformer"],
            "算法": ["排序算法", "搜索算法", "图算法"],
            "模型": ["线性模型", "非线性模型", "集成模型"],
        }
        
        return hyponym_dict.get(word, [])