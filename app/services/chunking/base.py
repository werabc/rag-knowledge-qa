"""
分块策略基础类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

@dataclass
class Chunk:
    """分块数据类"""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        """后处理：自动生成ID"""
        if not self.id:
            content_hash = hashlib.md5(self.text.encode()).hexdigest()[:8]
            self.id = f"chunk_{content_hash}"

class BaseChunker(ABC):
    """分块策略基类"""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100):
        """
        初始化分块器
        
        Args:
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    @abstractmethod
    async def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        分块文本
        
        Args:
            text: 输入文本
            metadata: 元数据
            
        Returns:
            List[Chunk]: 分块列表
        """
        pass
    
    def _create_chunk(self, text: str, metadata: Dict[str, Any] = None, **kwargs) -> Chunk:
        """创建分块对象"""
        chunk_metadata = metadata or {}
        chunk_metadata.update(kwargs)
        
        return Chunk(
            id="",
            text=text,
            metadata=chunk_metadata
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量"""
        # 简单估算：中文1字1token，英文1词1token
        import re
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return chinese_chars + english_words