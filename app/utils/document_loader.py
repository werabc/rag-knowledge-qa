"""
文档加载器工具
"""

import os
from typing import List, Dict, Any
from pathlib import Path

from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.config import settings

class DocumentLoader:
    """文档加载器类"""
    
    def __init__(self):
        """初始化文档加载器"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        加载文档并分块
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Document]: 文档分块列表
        """
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == ".pdf":
                return self._load_pdf(file_path)
            elif file_ext == ".docx":
                return self._load_docx(file_path)
            elif file_ext == ".txt":
                return self._load_txt(file_path)
            else:
                # 尝试作为文本文件加载
                return self._load_txt(file_path)
        except Exception as e:
            print(f"加载文档失败 {file_path}: {e}")
            return []
    
    def _load_pdf(self, file_path: str) -> List[Document]:
        """加载PDF文档"""
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            print(f"PDF加载失败: {e}")
            return []
    
    def _load_docx(self, file_path: str) -> List[Document]:
        """加载Word文档"""
        try:
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            print(f"Word文档加载失败: {e}")
            return []
    
    def _load_txt(self, file_path: str) -> List[Document]:
        """加载文本文件"""
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
            return self.text_splitter.split_documents(documents)
        except Exception as e:
            print(f"文本文件加载失败: {e}")
            return []
    
    def load_directory(self, directory: str) -> List[Document]:
        """
        加载目录中的所有文档
        
        Args:
            directory: 目录路径
            
        Returns:
            List[Document]: 所有文档分块列表
        """
        all_chunks = []
        
        for file_path in Path(directory).glob("*"):
            if file_path.is_file():
                chunks = self.load_document(str(file_path))
                all_chunks.extend(chunks)
        
        return all_chunks
    
    def get_document_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文档基本信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 文档信息
        """
        file_path_obj = Path(file_path)
        
        return {
            "filename": file_path_obj.name,
            "file_type": file_path_obj.suffix.lower(),
            "file_size": os.path.getsize(file_path),
            "modified_time": os.path.getmtime(file_path),
            "created_time": os.path.getctime(file_path)
        }

# 创建全局文档加载器实例
document_loader = DocumentLoader()