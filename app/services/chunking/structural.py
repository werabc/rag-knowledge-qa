"""
结构感知分块策略
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .base import BaseChunker, Chunk

@dataclass
class DocumentElement:
    """文档元素"""
    type: str  # heading, paragraph, list, table, etc.
    level: int  # 标题层级
    text: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class StructureAwareChunker(BaseChunker):
    """基于文档结构的智能分块器"""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 100,
                 preserve_structure: bool = True):
        """
        初始化结构感知分块器
        
        Args:
            chunk_size: 分块大小（字符数）
            chunk_overlap: 分块重叠大小
            preserve_structure: 是否保持文档结构
        """
        super().__init__(chunk_size, chunk_overlap)
        self.preserve_structure = preserve_structure
    
    async def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        基于文档结构的智能分块
        
        Args:
            text: 输入文本
            metadata: 元数据
            
        Returns:
            List[Chunk]: 分块列表
        """
        if not text or not text.strip():
            return []
        
        # 1. 解析文档结构
        elements = self._parse_document_structure(text)
        
        # 2. 按章节分块
        chunks = self._chunk_by_sections(elements, metadata)
        
        # 3. 处理跨章节分块
        chunks = self._handle_cross_section_chunks(chunks, metadata)
        
        return chunks
    
    def _parse_document_structure(self, text: str) -> List[DocumentElement]:
        """解析文档结构"""
        elements = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测标题
            heading_level = self._detect_heading_level(line)
            if heading_level > 0:
                elements.append(DocumentElement(
                    type="heading",
                    level=heading_level,
                    text=line,
                    metadata={"is_heading": True}
                ))
            else:
                # 检测列表项
                if self._is_list_item(line):
                    elements.append(DocumentElement(
                        type="list",
                        level=0,
                        text=line,
                        metadata={"is_list": True}
                    ))
                else:
                    # 普通段落
                    elements.append(DocumentElement(
                        type="paragraph",
                        level=0,
                        text=line,
                        metadata={"is_paragraph": True}
                    ))
        
        return elements
    
    def _detect_heading_level(self, line: str) -> int:
        """检测标题层级"""
        # Markdown风格标题
        if line.startswith('#'):
            return len(line) - len(line.lstrip('#'))
        
        # 数字编号标题
        match = re.match(r'^(\d+)\.\s', line)
        if match:
            return min(len(match.group(1)), 3)  # 最多3级
        
        # 中文标题模式
        if re.match(r'^[一二三四五六七八九十]+、', line):
            return 1
        if re.match(r'^[（(][一二三四五六七八九十]+[）)]', line):
            return 2
        
        return 0
    
    def _is_list_item(self, line: str) -> bool:
        """检查是否为列表项"""
        # 无序列表
        if re.match(r'^[-*+]\s', line):
            return True
        
        # 有序列表
        if re.match(r'^\d+\.\s', line):
            return True
        
        # 中文列表
        if re.match(r'^[（(]\d+[）)]', line):
            return True
        
        return False
    
    def _chunk_by_sections(self, elements: List[DocumentElement], 
                          metadata: Dict[str, Any] = None) -> List[Chunk]:
        """按章节分块"""
        chunks = []
        current_section = None
        current_content = []
        
        for element in elements:
            if element.type == "heading":
                # 遇到新标题，保存当前章节
                if current_content:
                    section_text = "\n".join([e.text for e in current_content])
                    if section_text.strip():
                        chunk = self._create_section_chunk(
                            section_text, current_section, metadata
                        )
                        chunks.append(chunk)
                
                # 开始新章节
                current_section = element
                current_content = [element]
            else:
                current_content.append(element)
        
        # 保存最后一个章节
        if current_content:
            section_text = "\n".join([e.text for e in current_content])
            if section_text.strip():
                chunk = self._create_section_chunk(
                    section_text, current_section, metadata
                )
                chunks.append(chunk)
        
        return chunks
    
    def _create_section_chunk(self, text: str, section: DocumentElement,
                             metadata: Dict[str, Any] = None) -> Chunk:
        """创建章节分块"""
        chunk_metadata = metadata or {}
        chunk_metadata.update({
            "chunk_type": "structural",
            "section_title": section.text if section else "",
            "section_level": section.level if section else 0,
            "element_count": len(text.split('\n')),
            "is_structural": True
        })
        
        return self._create_chunk(
            text=text,
            metadata=chunk_metadata
        )
    
    def _handle_cross_section_chunks(self, chunks: List[Chunk],
                                    metadata: Dict[str, Any] = None) -> List[Chunk]:
        """处理跨章节分块"""
        if not self.preserve_structure:
            return chunks
        
        processed_chunks = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # 如果当前分块太小，尝试与下一个合并
            if (len(current_chunk.text) < self.chunk_size // 2 and 
                i + 1 < len(chunks)):
                
                next_chunk = chunks[i + 1]
                combined_text = current_chunk.text + "\n\n" + next_chunk.text
                
                if len(combined_text) <= self.chunk_size:
                    # 合并分块
                    combined_metadata = current_chunk.metadata.copy()
                    combined_metadata.update({
                        "merged_from": [current_chunk.id, next_chunk.id],
                        "original_sections": [
                            current_chunk.metadata.get("section_title", ""),
                            next_chunk.metadata.get("section_title", "")
                        ]
                    })
                    
                    merged_chunk = self._create_chunk(
                        text=combined_text,
                        metadata=combined_metadata
                    )
                    processed_chunks.append(merged_chunk)
                    i += 2
                    continue
            
            # 保持原样
            processed_chunks.append(current_chunk)
            i += 1
        
        return processed_chunks