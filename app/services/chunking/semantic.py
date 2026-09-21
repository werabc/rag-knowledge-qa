"""
语义分块策略
"""

import re
import numpy as np
from typing import List, Dict, Any, Optional
from .base import BaseChunker, Chunk

class SemanticChunker(BaseChunker):
    """基于语义的智能分块器"""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100,
                 similarity_threshold: float = 0.7, min_sentences: int = 2):
        """
        初始化语义分块器
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠大小
            similarity_threshold: 相似度阈值，低于此值则分割
            min_sentences: 最小句子数
        """
        super().__init__(chunk_size, chunk_overlap)
        self.similarity_threshold = similarity_threshold
        self.min_sentences = min_sentences
        self.embedding_model = None  # 稍后初始化
    
    def _split_sentences(self, text: str) -> List[str]:
        """智能句子分割"""
        # 中英文句子分割正则
        sentence_endings = re.compile(r'(?<=[。！？.!?])\s*')
        sentences = sentence_endings.split(text)
        
        # 过滤空句子和过短句子
        filtered_sentences = []
        for s in sentences:
            s = s.strip()
            if s and len(s) > 5:  # 至少5个字符
                filtered_sentences.append(s)
        
        return filtered_sentences
    
    async def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        基于语义的智能分块
        
        Args:
            text: 输入文本
            metadata: 元数据
            
        Returns:
            List[Chunk]: 分块列表
        """
        if not text or not text.strip():
            return []
        
        # 1. 句子分割
        sentences = self._split_sentences(text)
        
        if len(sentences) <= self.min_sentences:
            # 句子太少，直接作为一个分块
            chunk = self._create_chunk(
                text=text,
                metadata=metadata,
                chunk_type="semantic",
                sentence_count=len(sentences)
            )
            return [chunk]
        
        # 2. 计算句子嵌入（如果模型可用）
        if self.embedding_model:
            embeddings = await self._compute_sentence_embeddings(sentences)
            similarities = self._compute_similarities(embeddings)
        else:
            # 如果没有嵌入模型，使用简单的启发式方法
            similarities = self._compute_heuristic_similarities(sentences)
        
        # 3. 基于相似度分割
        chunks = self._split_by_similarity(sentences, similarities, metadata)
        
        return chunks
    
    async def _compute_sentence_embeddings(self, sentences: List[str]) -> List[List[float]]:
        """计算句子嵌入"""
        if not self.embedding_model:
            return []
        
        embeddings = []
        batch_size = 32
        
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i+batch_size]
            batch_embeddings = await self.embedding_model.embed_batch(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _compute_similarities(self, embeddings: List[List[float]]) -> List[float]:
        """计算相邻句子余弦相似度"""
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i+1])
            similarities.append(sim)
        return similarities
    
    def _compute_heuristic_similarities(self, sentences: List[str]) -> List[float]:
        """使用启发式方法计算相似度"""
        similarities = []
        for i in range(len(sentences) - 1):
            # 基于词汇重叠的相似度
            words1 = set(sentences[i].split())
            words2 = set(sentences[i+1].split())
            
            if not words1 or not words2:
                similarity = 0.0
            else:
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))
                similarity = intersection / union if union > 0 else 0.0
            
            similarities.append(similarity)
        
        return similarities
    
    def _split_by_similarity(self, sentences: List[str], similarities: List[float],
                            metadata: Dict[str, Any] = None) -> List[Chunk]:
        """基于相似度阈值分割"""
        chunks = []
        current_chunk_sentences = [sentences[0]]
        
        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                # 相似度低于阈值，分割
                chunk_text = " ".join(current_chunk_sentences)
                
                # 检查是否需要分割（基于大小）
                if len(chunk_text) > self.chunk_size:
                    # 大分块进一步分割
                    sub_chunks = self._split_large_chunk(chunk_text, metadata)
                    chunks.extend(sub_chunks)
                else:
                    chunk = self._create_chunk(
                        text=chunk_text,
                        metadata=metadata,
                        chunk_type="semantic",
                        sentence_count=len(current_chunk_sentences),
                        similarity_threshold=self.similarity_threshold
                    )
                    chunks.append(chunk)
                
                current_chunk_sentences = [sentences[i+1]]
            else:
                current_chunk_sentences.append(sentences[i+1])
        
        # 添加最后一个分块
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            if len(chunk_text) > self.chunk_size:
                sub_chunks = self._split_large_chunk(chunk_text, metadata)
                chunks.extend(sub_chunks)
            else:
                chunk = self._create_chunk(
                    text=chunk_text,
                    metadata=metadata,
                    chunk_type="semantic",
                    sentence_count=len(current_chunk_sentences),
                    similarity_threshold=self.similarity_threshold
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_large_chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """分割过大的语义分块"""
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = current_pos + self.chunk_size
            
            if end_pos < len(text):
                # 尝试在句子边界处分割
                split_pos = self._find_sentence_boundary(text, current_pos, end_pos)
                if split_pos > current_pos:
                    end_pos = split_pos
            
            chunk_text = text[current_pos:end_pos].strip()
            
            if chunk_text:
                chunk = self._create_chunk(
                    text=chunk_text,
                    metadata=metadata,
                    chunk_type="semantic_large",
                    start_pos=current_pos,
                    end_pos=end_pos
                )
                chunks.append(chunk)
            
            current_pos = end_pos - self.chunk_overlap
            if current_pos >= end_pos:
                current_pos = end_pos
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """查找句子边界"""
        # 中英文句子结束符
        sentence_endings = ['。', '！', '？', '.', '!', '?']
        
        for i in range(end - 1, start, -1):
            if text[i] in sentence_endings:
                return i + 1
        
        return end
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)