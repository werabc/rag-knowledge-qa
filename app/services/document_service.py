"""
文档处理服务
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

import PyPDF2
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.models.schemas import DocumentCreate, DocumentResponse, DocumentStats
from app.services.vector_store import vector_store

class DocumentService:
    """文档处理服务类"""
    
    def __init__(self):
        """初始化文档服务"""
        self.documents_db: Dict[str, DocumentResponse] = {}
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )
    
    async def upload_document(self, file_path: str, filename: str, file_size: int) -> DocumentResponse:
        """
        上传并处理文档
        
        Args:
            file_path: 文件路径
            filename: 文件名
            file_size: 文件大小
            
        Returns:
            DocumentResponse: 文档信息
        """
        # 生成文档ID
        doc_id = str(uuid.uuid4())
        
        # 获取文件类型
        file_type = Path(filename).suffix.lower()
        
        # 提取文档内容
        content = await self._extract_content(file_path, file_type)
        
        # 分块处理
        chunks = self.text_splitter.split_text(content)

        # 写入向量库（embedding 由 chromadb 完成）
        indexed = await vector_store.add_documents(
            doc_id, chunks,
            metadata={"filename": filename, "file_type": file_type},
        )

        # 创建文档记录
        document = DocumentResponse(
            id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            status="processed" if indexed else "index_failed",
            chunk_count=len(chunks)
        )
        
        # 存储文档信息
        self.documents_db[doc_id] = document
        
        # 保存分块内容到文件（简化实现）
        chunks_dir = os.path.join(settings.DOCUMENT_STORAGE_PATH, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        chunks_file = os.path.join(chunks_dir, f"{doc_id}.txt")
        with open(chunks_file, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks):
                f.write(f"--- Chunk {i+1} ---\n")
                f.write(chunk)
                f.write("\n\n")
        
        return document
    
    async def _extract_content(self, file_path: str, file_type: str) -> str:
        """
        提取文档内容
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            str: 提取的文本内容
        """
        content = ""
        
        try:
            if file_type == ".pdf":
                content = await self._extract_pdf(file_path)
            elif file_type == ".docx":
                content = await self._extract_docx(file_path)
            elif file_type == ".txt":
                content = await self._extract_txt(file_path)
            else:
                # 尝试作为文本文件读取
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
        except Exception as e:
            print(f"文档内容提取失败: {e}")
            content = f"文档内容提取失败: {str(e)}"
        
        return content
    
    async def _extract_pdf(self, file_path: str) -> str:
        """提取PDF文档内容"""
        text = ""
        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            text = f"PDF读取失败: {str(e)}"
        return text
    
    async def _extract_docx(self, file_path: str) -> str:
        """提取Word文档内容"""
        text = ""
        try:
            doc = DocxDocument(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            text = f"Word文档读取失败: {str(e)}"
        return text
    
    async def _extract_txt(self, file_path: str) -> str:
        """提取文本文件内容"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"文本文件读取失败: {str(e)}"
    
    async def get_documents(self) -> List[DocumentResponse]:
        """获取所有文档列表"""
        return list(self.documents_db.values())
    
    async def get_document(self, doc_id: str) -> Optional[DocumentResponse]:
        """获取指定文档信息"""
        return self.documents_db.get(doc_id)
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id in self.documents_db:
            del self.documents_db[doc_id]
            # 删除分块文件
            chunks_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "chunks", f"{doc_id}.txt")
            if os.path.exists(chunks_file):
                os.remove(chunks_file)
            return True
        return False
    
    async def get_document_stats(self) -> DocumentStats:
        """获取文档统计信息"""
        documents = list(self.documents_db.values())
        
        total_chunks = sum(doc.chunk_count for doc in documents)
        total_size = sum(doc.file_size for doc in documents)
        
        file_types = {}
        for doc in documents:
            file_type = doc.file_type
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return DocumentStats(
            total_documents=len(documents),
            total_chunks=total_chunks,
            total_size=total_size,
            file_types=file_types
        )
    
    async def get_document_chunks(self, doc_id: str) -> List[str]:
        """获取文档分块内容"""
        chunks_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "chunks", f"{doc_id}.txt")
        
        if not os.path.exists(chunks_file):
            return []
        
        try:
            with open(chunks_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 简单分块解析
            chunks = []
            current_chunk = ""
            for line in content.split("\n"):
                if line.startswith("--- Chunk") and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                else:
                    current_chunk += line + "\n"
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            return chunks
        except Exception as e:
            print(f"读取文档分块失败: {e}")
            return []

# 创建全局文档服务实例
document_service = DocumentService()