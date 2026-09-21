"""
BM25召回策略
"""

import math
import numpy as np
from typing import List, Dict, Any, Optional
from collections import Counter
from .base import BaseRetriever, RetrievalResult

class BM25Retriever(BaseRetriever):
    """基于BM25算法的召回器"""
    
    def __init__(self, documents: List[str], top_k: int = 10,
                 k1: float = 1.5, b: float = 0.75):
        """
        初始化BM25召回器
        
        Args:
            documents: 文档列表
            top_k: 返回结果数量
            k1: 词频饱和参数
            b: 文档长度归一化参数
        """
        super().__init__(top_k)
        self.k1 = k1
        self.b = b
        self.documents = documents
        
        # 构建索引
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.doc_freqs = []
        self.idf = {}
        self.tf = []
        
        self._build_index()
    
    def _build_index(self):
        """构建BM25索引"""
        # 1. 分词和计算词频
        tokenized_docs = [self._tokenize(doc) for doc in self.documents]
        
        # 2. 计算文档长度
        self.doc_lengths = [len(doc) for doc in tokenized_docs]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0
        
        # 3. 计算文档频率
        self.doc_freqs = []
        for doc in tokenized_docs:
            freq = Counter(doc)
            self.doc_freqs.append(freq)
        
        # 4. 计算IDF
        self._compute_idf()
        
        # 5. 计算TF
        self._compute_tf(tokenized_docs)
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        import jieba
        # 使用jieba分词
        tokens = list(jieba.cut(text))
        
        # 过滤停用词和标点
        filtered_tokens = []
        for token in tokens:
            token = token.strip()
            if token and len(token) > 1 and not self._is_stopword(token):
                filtered_tokens.append(token)
        
        return filtered_tokens
    
    def _is_stopword(self, word: str) -> bool:
        """检查是否为停用词"""
        # 简单的停用词列表
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '他', '她',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
            'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'
        }
        
        return word.lower() in stop_words
    
    def _compute_idf(self):
        """计算IDF"""
        num_docs = len(self.documents)
        
        # 统计每个词出现在多少文档中
        word_doc_freq = {}
        for doc_freq in self.doc_freqs:
            for word in doc_freq.keys():
                if word not in word_doc_freq:
                    word_doc_freq[word] = 0
                word_doc_freq[word] += 1
        
        # 计算IDF
        for word, freq in word_doc_freq.items():
            # IDF = log((N - n + 0.5) / (n + 0.5))
            self.idf[word] = math.log((num_docs - freq + 0.5) / (freq + 0.5))
    
    def _compute_tf(self, tokenized_docs: List[List[str]]):
        """计算TF"""
        self.tf = []
        for doc in tokenized_docs:
            tf = {}
            for word in doc:
                if word not in tf:
                    tf[word] = 0
                tf[word] += 1
            self.tf.append(tf)
    
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        """
        BM25检索
        
        Args:
            query: 查询文本
            **kwargs: 额外参数
            
        Returns:
            List[RetrievalResult]: 召回结果列表
        """
        # 分词查询
        query_tokens = self._tokenize(query)
        
        # 计算BM25分数
        scores = []
        for i, doc_tf in enumerate(self.tf):
            score = 0.0
            doc_length = self.doc_lengths[i]
            
            for token in query_tokens:
                if token in doc_tf:
                    tf = doc_tf[token]
                    idf = self.idf.get(token, 0)
                    
                    # BM25公式
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                    
                    score += idf * numerator / denominator
            
            scores.append(score)
        
        # 获取top-k结果
        top_indices = np.argsort(scores)[-self.top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 只返回正分数结果
                result = RetrievalResult(
                    content=self.documents[idx],
                    score=scores[idx],
                    metadata={"doc_index": idx},
                    retrieval_method="bm25"
                )
                results.append(result)
        
        return results