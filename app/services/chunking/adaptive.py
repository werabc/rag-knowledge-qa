"""
自适应分块策略
"""

import re
import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseChunker, Chunk

class AdaptiveChunker(BaseChunker):
    """基于内容重要性的自适应分块器"""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100,
                 min_size: int = 200, max_size: int = 2000):
        """
        初始化自适应分块器
        
        Args:
            chunk_size: 默认分块大小
            chunk_overlap: 分块重叠大小
            min_size: 最小分块大小
            max_size: 最大分块大小
        """
        super().__init__(chunk_size, chunk_overlap)
        self.min_size = min_size
        self.max_size = max_size
        self.importance_scorer = None  # 稍后初始化
    
    async def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        基于内容重要性的自适应分块
        
        Args:
            text: 输入文本
            metadata: 元数据
            
        Returns:
            List[Chunk]: 分块列表
        """
        if not text or not text.strip():
            return []
        
        # 1. 计算内容重要性分数
        importance_scores = await self._compute_importance_scores(text, metadata)
        
        # 2. 基于重要性分数进行自适应分块
        chunks = self._adaptive_chunking(text, importance_scores, metadata)
        
        # 3. 后处理：合并过小的分块
        chunks = self._merge_small_chunks(chunks, metadata)
        
        return chunks
    
    async def _compute_importance_scores(self, text: str, metadata: Dict[str, Any] = None) -> List[float]:
        """计算内容重要性分数"""
        # 分句处理
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return [1.0]  # 默认重要性
        
        scores = []
        for sentence in sentences:
            score = await self._compute_sentence_importance(sentence, metadata)
            scores.append(score)
        
        return scores
    
    async def _compute_sentence_importance(self, sentence: str, metadata: Dict[str, Any] = None) -> float:
        """计算单个句子的重要性"""
        importance_factors = []
        
        # 1. 基于关键词的重要性
        keyword_score = self._keyword_importance(sentence)
        importance_factors.append(keyword_score)
        
        # 2. 基于位置的重要性
        position_score = self._position_importance(sentence)
        importance_factors.append(position_score)
        
        # 3. 基于句子长度的重要性
        length_score = self._length_importance(sentence)
        importance_factors.append(length_score)
        
        # 4. 基于标点符号的重要性
        punctuation_score = self._punctuation_importance(sentence)
        importance_factors.append(punctuation_score)
        
        # 5. 基于数字和特殊内容的重要性
        special_score = self._special_content_importance(sentence)
        importance_factors.append(special_score)
        
        # 加权平均
        weights = [0.3, 0.2, 0.2, 0.15, 0.15]
        final_score = np.average(importance_factors, weights=weights)
        
        return final_score
    
    def _keyword_importance(self, sentence: str) -> float:
        """基于关键词的重要性"""
        # 重要关键词列表（可以根据领域调整）
        important_keywords = [
            "重要", "关键", "核心", "主要", "基本", "定义", "原理",
            "方法", "步骤", "注意", "警告", "示例", "总结", "结论",
            "important", "key", "core", "main", "basic", "definition",
            "method", "step", "note", "warning", "example", "summary"
        ]
        
        sentence_lower = sentence.lower()
        keyword_count = sum(1 for keyword in important_keywords 
                          if keyword in sentence_lower)
        
        # 归一化到[0,1]
        return min(keyword_count / 3, 1.0)
    
    def _position_importance(self, sentence: str) -> float:
        """基于位置的重要性"""
        # 段落开头和结尾通常更重要
        if sentence.startswith(('因此', '所以', '总之', '综上所述', '因此', '故')):
            return 0.8
        if sentence.startswith(('首先', '其次', '最后', '第一', '第二', '第三')):
            return 0.7
        if sentence.endswith(('。', '！', '？')):
            return 0.6
        return 0.5
    
    def _length_importance(self, sentence: str) -> float:
        """基于句子长度的重要性"""
        # 中等长度的句子通常更重要
        length = len(sentence)
        if 20 <= length <= 100:
            return 0.8
        elif 10 <= length <= 150:
            return 0.6
        else:
            return 0.4
    
    def _punctuation_importance(self, sentence: str) -> float:
        """基于标点符号的重要性"""
        # 包含问号、感叹号、冒号的句子可能更重要
        punctuation_chars = ['？', '！', '：', '?', '!', ':', '；', ';']
        punctuation_count = sum(1 for char in punctuation_chars 
                              if char in sentence)
        
        return min(punctuation_count / 2, 1.0)
    
    def _special_content_importance(self, sentence: str) -> float:
        """基于特殊内容的重要性"""
        # 包含数字、公式、代码的内容
        has_numbers = bool(re.search(r'\d+', sentence))
        has_formulas = bool(re.search(r'[=+\-*/^]', sentence))
        has_code = bool(re.search(r'[{}\[\]()<>]', sentence))
        
        score = 0.4
        if has_numbers:
            score += 0.2
        if has_formulas:
            score += 0.2
        if has_code:
            score += 0.2
        
        return min(score, 1.0)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 中英文句子分割
        sentence_endings = re.compile(r'(?<=[。！？.!?])\s*')
        sentences = sentence_endings.split(text)
        
        # 过滤空句子
        return [s.strip() for s in sentences if s.strip()]
    
    def _adaptive_chunking(self, text: str, importance_scores: List[float],
                          metadata: Dict[str, Any] = None) -> List[Chunk]:
        """基于重要性进行自适应分块"""
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # 计算当前位置的重要性
            local_importance = self._get_local_importance(importance_scores, current_pos)
            
            # 根据重要性决定分块大小
            chunk_size = self._compute_adaptive_size(local_importance)
            
            # 确保不超出文本范围
            end_pos = min(current_pos + chunk_size, len(text))
            
            # 尝试在句子边界处分割
            if end_pos < len(text):
                end_pos = self._find_sentence_boundary(text, current_pos, end_pos)
            
            # 提取分块
            chunk_text = text[current_pos:end_pos].strip()
            
            if chunk_text:
                # 计算分块的重要性分数
                chunk_importance = self._compute_chunk_importance(
                    importance_scores, current_pos, end_pos
                )
                
                # 创建分块
                chunk = self._create_chunk(
                    text=chunk_text,
                    metadata=metadata,
                    chunk_type="adaptive",
                    importance_score=chunk_importance,
                    adaptive_size=chunk_size,
                    start_pos=current_pos,
                    end_pos=end_pos
                )
                chunks.append(chunk)
            
            # 移动到下一个位置
            current_pos = end_pos - self.chunk_overlap
            if current_pos >= end_pos:
                current_pos = end_pos
        
        return chunks
    
    def _get_local_importance(self, importance_scores: List[float], position: int) -> float:
        """获取局部重要性"""
        if not importance_scores:
            return 0.5
        
        # 简化处理：使用平均重要性
        return np.mean(importance_scores)
    
    def _compute_adaptive_size(self, importance_score: float) -> int:
        """根据重要性计算自适应分块大小"""
        # 重要性越高，分块越小（更精细）
        # 重要性越低，分块越大（更粗略）
        
        if importance_score > 0.8:
            # 高重要性：小分块
            return self.min_size
        elif importance_score < 0.3:
            # 低重要性：大分块
            return self.max_size
        else:
            # 中等重要性：线性插值
            ratio = (importance_score - 0.3) / (0.8 - 0.3)
            size = self.max_size - ratio * (self.max_size - self.min_size)
            return int(size)
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """查找句子边界"""
        # 中英文句子结束符
        sentence_endings = ['。', '！', '？', '.', '!', '?', '；', ';']
        
        for i in range(end - 1, start, -1):
            if text[i] in sentence_endings:
                return i + 1
        
        return end
    
    def _compute_chunk_importance(self, importance_scores: List[float],
                                 start_pos: int, end_pos: int) -> float:
        """计算分块的重要性分数"""
        if not importance_scores:
            return 0.5
        
        # 简化处理：使用平均重要性
        return np.mean(importance_scores)
    
    def _merge_small_chunks(self, chunks: List[Chunk], 
                           metadata: Dict[str, Any] = None) -> List[Chunk]:
        """合并过小的分块"""
        if len(chunks) <= 1:
            return chunks
        
        merged_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # 如果当前分块太小，尝试与下一个合并
            if (len(current_chunk.text) < self.min_size and 
                i + 1 < len(chunks)):
                
                next_chunk = chunks[i + 1]
                combined_text = current_chunk.text + "\n\n" + next_chunk.text
                
                if len(combined_text) <= self.max_size:
                    # 合并分块
                    combined_metadata = current_chunk.metadata.copy()
                    combined_metadata.update({
                        "merged_from": [current_chunk.id, next_chunk.id],
                        "original_importance": [
                            current_chunk.metadata.get("importance_score", 0.5),
                            next_chunk.metadata.get("importance_score", 0.5)
                        ]
                    })
                    
                    merged_chunk = self._create_chunk(
                        text=combined_text,
                        metadata=combined_metadata
                    )
                    merged_chunks.append(merged_chunk)
                    i += 2
                    continue
            
            # 保持原样
            merged_chunks.append(current_chunk)
            i += 1
        
        return merged_chunks