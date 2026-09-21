"""
固定大小分块策略
"""

import re
from typing import List, Dict, Any
from .base import BaseChunker, Chunk

class FixedSizeChunker(BaseChunker):
    """固定大小分块器"""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100, 
                 separators: List[str] = None):
        """
        初始化固定大小分块器
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠大小
            separators: 分隔符列表
        """
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]
    
    async def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        固定大小分块
        
        Args:
            text: 输入文本
            metadata: 元数据
            
        Returns:
            List[Chunk]: 分块列表
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # 计算结束位置
            end_pos = current_pos + self.chunk_size
            
            # 如果不是最后一块，尝试在分隔符处分割
            if end_pos < len(text):
                split_pos = self._find_split_position(text, current_pos, end_pos)
                if split_pos > current_pos:
                    end_pos = split_pos
            
            # 提取分块
            chunk_text = text[current_pos:end_pos].strip()
            
            if chunk_text:
                # 创建分块
                chunk = self._create_chunk(
                    text=chunk_text,
                    metadata=metadata,
                    chunk_type="fixed_size",
                    start_pos=current_pos,
                    end_pos=end_pos,
                    chunk_index=len(chunks)
                )
                chunks.append(chunk)
            
            # 移动到下一个位置（考虑重叠）
            current_pos = end_pos - self.chunk_overlap
            if current_pos >= end_pos:
                current_pos = end_pos
        
        return chunks
    
    def _find_split_position(self, text: str, start: int, end: int) -> int:
        """查找最佳分割位置"""
        # 从后向前查找分隔符
        for separator in self.separators:
            pos = text.rfind(separator, start, end)
            if pos > start:
                return pos + len(separator)
        
        # 如果没找到分隔符，在空格处分割
        pos = text.rfind(' ', start, end)
        if pos > start:
            return pos + 1
        
        # 返回结束位置
        return end